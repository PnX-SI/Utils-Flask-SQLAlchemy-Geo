import json
import zipfile
from types import SimpleNamespace

import fiona
import pytest
import sqlalchemy as sa
from geoalchemy2 import Geometry
from geoalchemy2.shape import from_shape
from shapely.geometry import (
    GeometryCollection,
    LinearRing,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
    mapping,
)

from utils_flask_sqla.errors import UtilsSqlaError
from utils_flask_sqla_geo.utilsgeometry import (
    FionaGpkgService,
    FionaShapeService,
    _nest_properties,
    convert_to_2d,
    create_gpkg_generic,
    create_shapes_generic,
    export_geodata_as_file,
    remove_third_dimension,
)

SQUARE = [(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]
SQUARE_3D = [(x, y, 5) for x, y in SQUARE]
HOLE_3D = [(0.2, 0.2, 5), (0.2, 0.4, 5), (0.4, 0.4, 5), (0.2, 0.2, 5)]


class TestRemoveThirdDimension:
    def test_2d_geometry_unchanged(self):
        point = Point(1, 2)
        assert remove_third_dimension(point) is point

    @pytest.mark.parametrize(
        "geom",
        [
            Point(1, 2, 3),
            LineString([(0, 0, 1), (1, 1, 2)]),
            LinearRing(SQUARE_3D),
            Polygon(SQUARE_3D, [HOLE_3D]),
            MultiPoint([(0, 0, 1), (1, 1, 2)]),
            MultiLineString([[(0, 0, 1), (1, 1, 2)], [(2, 2, 3), (3, 3, 4)]]),
            MultiPolygon([Polygon(SQUARE_3D), Polygon([(x + 2, y, z) for x, y, z in SQUARE_3D])]),
            GeometryCollection([Point(1, 2, 3), LineString([(0, 0, 1), (1, 1, 2)])]),
        ],
        ids=lambda g: g.geom_type,
    )
    def test_3d_geometry_flattened(self, geom):
        result = remove_third_dimension(geom)
        assert not result.has_z
        assert result.geom_type == geom.geom_type
        # x/y coordinates are preserved
        assert result.bounds == geom.bounds

    def test_polygon_keeps_interiors(self):
        result = remove_third_dimension(Polygon(SQUARE_3D, [HOLE_3D]))
        assert len(result.interiors) == 1

    def test_unsupported_geometry(self):
        class FakeGeom:
            has_z = True

        with pytest.raises(RuntimeError, match="not supported"):
            remove_third_dimension(FakeGeom())


class TestConvertTo2d:
    def test_point(self):
        geojson = {"type": "Point", "coordinates": [1, 2, 3]}
        convert_to_2d(geojson)
        assert geojson["coordinates"] == [1, 2]

    def test_linestring(self):
        geojson = {"type": "LineString", "coordinates": [[1, 2, 3], [4, 5, 6]]}
        convert_to_2d(geojson)
        assert geojson["coordinates"] == [[1, 2], [4, 5]]

    def test_polygon(self):
        ring = [(0, 0, 1), (0, 1, 1), (1, 1, 1), (0, 0, 1)]
        geojson = {"type": "Polygon", "coordinates": [ring]}
        convert_to_2d(geojson)
        assert geojson["coordinates"] == [[[0, 0], [0, 1], [1, 1], [0, 0]]]


class TestNestProperties:
    def test_nest(self):
        assert _nest_properties({"a.b": 1, "a.c": 2, "d": 3}) == {"a": {"b": 1, "c": 2}, "d": 3}

    def test_custom_separator(self):
        assert _nest_properties({"a__b": 1, "a.c": 2}, "__") == {"a": {"b": 1}, "a.c": 2}


metadata = sa.MetaData()
geo_table = sa.Table(
    "geo_table",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.Unicode),
    sa.Column("value", sa.Float),
    sa.Column("geom", Geometry("GEOMETRY", 4326)),
)


class FakeView:
    """Minimal stand-in of a GenericTable: only as_dict is used by FionaService"""

    def as_dict(self, data, columns=[]):
        return {col: getattr(data, col) for col in columns}


def make_row(id, geom, as_geojson=False):
    row = SimpleNamespace(id=id, name=f"row {id}", value=id * 1.5)
    if geom is None:
        row.geom = row.geom_json = None
    else:
        row.geom = from_shape(geom, srid=4326)
        row.geom_json = json.dumps(mapping(geom))
    return row


ROWS_GEOMS = [
    Point(6, 10),
    MultiPoint([(1, 1), (2, 2)]),
    LineString([(0, 0), (1, 1)]),
    Polygon(SQUARE),
]


@pytest.fixture
def rows():
    return [make_row(i, g) for i, g in enumerate(ROWS_GEOMS, start=1)]


def read_features(path, **kwargs):
    with fiona.open(path, **kwargs) as f:
        return list(f)


class TestFionaServiceStructure:
    def test_properties_mapping(self, tmp_path):
        FionaGpkgService.create_fiona_struct(geo_table.c, 4326, str(tmp_path), "struct")
        FionaGpkgService.close_files()
        # geometry columns are not exported as attributes
        assert FionaGpkgService.columns == ["id", "name", "value"]
        assert dict(FionaGpkgService.shp_properties) == {
            "id": "int",
            "name": "str",
            "value": "float",
        }

    def test_col_mapping(self, tmp_path):
        col_mapping = {"id": "ID", "name": "NAME", "value": "VALUE", "geom": "GEOM"}
        FionaGpkgService.create_fiona_struct(
            geo_table.c, 4326, str(tmp_path), "mapped", col_mapping=col_mapping
        )
        FionaGpkgService.close_files()
        assert FionaGpkgService.columns == ["ID", "NAME", "VALUE"]


class TestFionaGpkgService:
    def test_export_wkb(self, tmp_path, rows):
        create_gpkg_generic(
            FakeView(), 4326, geo_table.c, rows, str(tmp_path), "out", "geom", None
        )
        features = read_features(tmp_path / "out.gpkg")
        assert len(features) == len(rows)
        assert [f["properties"]["name"] for f in features] == [r.name for r in rows]
        assert [f["geometry"]["type"] for f in features] == [g.geom_type for g in ROWS_GEOMS]

    def test_export_geojson_col(self, tmp_path, rows):
        create_gpkg_generic(
            FakeView(), 4326, geo_table.c, rows, str(tmp_path), "out", "geom", "geom_json"
        )
        assert len(read_features(tmp_path / "out.gpkg")) == len(rows)

    def test_rows_without_geometry_are_skipped(self, tmp_path, rows, caplog):
        rows.append(make_row(99, None))
        create_gpkg_generic(
            FakeView(), 4326, geo_table.c, rows, str(tmp_path), "out", "geom", None
        )
        assert len(read_features(tmp_path / "out.gpkg")) == len(rows) - 1
        assert "Can not build feature for geo column geom" in caplog.text


class TestFionaShapeService:
    def test_export_zip(self, tmp_path, rows):
        create_shapes_generic(
            FakeView(), 4326, geo_table.c, rows, str(tmp_path), "out", "geom", None
        )
        with zipfile.ZipFile(tmp_path / "out.zip") as zp:
            names = set(zp.namelist())
        assert names == {
            f"{kind}_out.{ext}"
            for kind in ("POINT", "POLYGON", "POLYLINE")
            for ext in ("dbf", "shx", "shp", "prj")
        }
        points = read_features(tmp_path / "POINT_out" / "POINT_out.shp")
        # Point is converted to MultiPoint as both can't be mixed in a shapefile
        assert [f["geometry"]["type"] for f in points] == ["MultiPoint", "MultiPoint"]
        assert len(read_features(tmp_path / "POLYLINE_out" / "POLYLINE_out.shp")) == 1
        assert len(read_features(tmp_path / "POLYGON_out" / "POLYGON_out.shp")) == 1

    def test_only_non_empty_shapes_are_zipped(self, tmp_path):
        rows = [make_row(1, LineString([(0, 0), (1, 1)]))]
        create_shapes_generic(
            FakeView(), 4326, geo_table.c, rows, str(tmp_path), "out", "geom", "geom_json"
        )
        with zipfile.ZipFile(tmp_path / "out.zip") as zp:
            assert all(name.startswith("POLYLINE_") for name in zp.namelist())

    def test_only_polygons(self, tmp_path):
        rows = [make_row(1, Polygon(SQUARE))]
        create_shapes_generic(
            FakeView(), 4326, geo_table.c, rows, str(tmp_path), "out", "geom", None
        )
        with zipfile.ZipFile(tmp_path / "out.zip") as zp:
            assert all(name.startswith("POLYGON_") for name in zp.namelist())

    def test_create_feature_invalid_geometry(self, tmp_path):
        FionaShapeService.create_fiona_struct(geo_table.c, 4326, str(tmp_path), "invalid")
        with pytest.raises(UtilsSqlaError):
            FionaShapeService.create_feature({"id": 1}, "not a geometry")


class TestExportGeodataAsFile:
    @pytest.mark.parametrize(
        "export_format,expected_file", [("gpkg", "out.gpkg"), ("shp", "out.zip")]
    )
    def test_formats(self, tmp_path, rows, export_format, expected_file):
        export_geodata_as_file(
            FakeView(),
            4326,
            geo_table.c,
            rows,
            str(tmp_path),
            "out",
            "geom",
            None,
            export_format=export_format,
        )
        assert (tmp_path / expected_file).exists()

    def test_unsupported_format(self, tmp_path, rows):
        export_geodata_as_file(
            FakeView(), 4326, geo_table.c, rows, str(tmp_path), "out", "geom", None, "csv"
        )
        assert list(tmp_path.iterdir()) == []
