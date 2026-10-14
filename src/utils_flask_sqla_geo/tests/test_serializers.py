import re
import zipfile

import fiona
from unittest import TestCase

import pytest
import sqlalchemy as sa
from shapely import wkt
from shapely.geometry import Point, Polygon

from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry
from geoalchemy2.shape import from_shape, to_shape

from utils_flask_sqla.errors import UtilsSqlaError
from utils_flask_sqla.serializers import serializable
from utils_flask_sqla_geo.serializers import (
    geofileserializable,
    geoserializable,
    shapeserializable,
    sqla_query_to_geojson,
    sqla_query_to_text,
    txt_query_as_geojson,
)

from utils_flask_sqla_geo.tests.geo_test_db import SCHEMA

SQUARE = [(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]

db = SQLAlchemy()


class TestSerializers:
    def test_geom(self):
        @geoserializable
        class TestModel1(db.Model):
            pk = db.Column(db.Integer, primary_key=True)
            geom = db.Column(Geometry("GEOMETRY", 4326))

        o = TestModel1(pk=1, geom=wkt.loads("POINT(6 10)"))
        d = o.as_dict()
        TestCase().assertDictEqual(
            {
                "pk": 1,
            },
            d,
        )

    def test_default_params(self):
        @geoserializable(exclude=["excluded"])
        class TestModel2(db.Model):
            pk = db.Column(db.Integer, primary_key=True)
            excluded = db.Column(db.Integer)
            geom = db.Column(Geometry("GEOMETRY", 4326))

        point = wkt.loads("POINT(6 10)")
        o = TestModel2(pk=1, excluded=2, geom=point)
        d = o.as_dict()
        TestCase().assertDictEqual(
            {
                "pk": 1,
            },
            d,
        )

        d = o.as_dict(exclude=[])
        TestCase().assertDictEqual(
            {
                "pk": 1,
                "excluded": 2,
                "geom": point,
            },
            d,
        )

    def test_as_geofeature(self):
        @geoserializable(geoCol="geom", idCol="pk")
        class TestModel3(db.Model):
            pk = db.Column(db.Integer, primary_key=True)
            name = db.Column(db.Unicode)
            geom = db.Column(Geometry("GEOMETRY", 4326))

        o = TestModel3(pk=1, name="o", geom=from_shape(Point(6, 10), srid=4326))
        feature = o.as_geofeature()
        assert feature["id"] == "1"
        assert feature["geometry"] == {"type": "Point", "coordinates": [6.0, 10.0]}
        assert feature["properties"] == {"pk": 1, "name": "o"}
        # columns given at call time override the default ones
        assert o.as_geofeature("geom", "name")["id"] == "o"

    def test_as_geofeature_null_geom(self):
        @geoserializable(geoCol="geom", idCol="pk")
        class TestModel4(db.Model):
            pk = db.Column(db.Integer, primary_key=True)
            geom = db.Column(Geometry("GEOMETRY", 4326))

        feature = TestModel4(pk=1, geom=None).as_geofeature()
        assert feature["geometry"] == {"type": "Point", "coordinates": [0, 0]}

    def test_from_geofeature(self):
        @geoserializable(geoCol="geom", idCol="pk")
        class TestModel5(db.Model):
            pk = db.Column(db.Integer, primary_key=True)
            name = db.Column(db.Unicode)
            geom = db.Column(Geometry("GEOMETRY", 4326))

        o = TestModel5()
        o.from_geofeature(
            {
                "type": "Feature",
                "properties": {"pk": 1, "name": "o"},
                "geometry": {"type": "Point", "coordinates": [6, 10, 1000]},
            }
        )
        assert o.pk == 1
        assert o.name == "o"
        geom = to_shape(o.geom)
        # third dimension is removed
        assert not geom.has_z
        assert geom.equals(Point(6, 10))
        assert o.geom.srid == 4326

    @pytest.mark.parametrize(
        "geojson",
        [
            {"type": "Point", "coordinates": [6, 10]},
            {"type": "Feature", "properties": {"pk": 1}},
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [6, 10]}},
        ],
    )
    def test_from_geofeature_invalid(self, geojson):
        with pytest.raises(UtilsSqlaError, match="Input must be a geofeature"):
            GeofeatureModel().from_geofeature(geojson)


@geoserializable
class GeofeatureModel(db.Model):
    pk = db.Column(db.Integer, primary_key=True)
    geom = db.Column(Geometry("GEOMETRY", 4326))


class FileModelMixin:
    pk = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode)
    geom = db.Column(Geometry("GEOMETRY", 4326))


@shapeserializable
@serializable
class ShapeModel(FileModelMixin, db.Model):
    pass


@geofileserializable
@serializable
class GeofileModel(FileModelMixin, db.Model):
    pass


def file_model_data(model):
    return [
        model(pk=1, name="point", geom=from_shape(Point(6, 10), srid=4326)),
        model(pk=2, name="polygon", geom=from_shape(Polygon(SQUARE), srid=4326)),
        model(pk=3, name="no geom", geom=None),
    ]


def read_features(path):
    with fiona.open(path) as f:
        return [dict(feature["properties"]) for feature in f]


class TestFileSerializers:
    def test_as_shape_without_data(self, tmp_path):
        ShapeModel.as_shape(geom_col="geom", srid=4326, dir_path=str(tmp_path), file_name="out")
        with zipfile.ZipFile(tmp_path / "out.zip") as zp:
            assert zp.namelist() == []
        assert (tmp_path / "POINT_out").exists()

    @pytest.mark.parametrize(
        "export_format,expected_file", [("shp", "out.zip"), ("gpkg", "out.gpkg")]
    )
    def test_as_geofile_without_data(self, tmp_path, export_format, expected_file):
        GeofileModel.as_geofile(
            export_format=export_format,
            geom_col="geom",
            srid=4326,
            dir_path=str(tmp_path),
            file_name="out",
        )
        assert (tmp_path / expected_file).exists()

    def test_as_geofile_default_file_name(self, tmp_path):
        GeofileModel.as_geofile(export_format="gpkg", srid=4326, dir_path=str(tmp_path))
        assert len(list(tmp_path.glob("*.gpkg"))) == 1

    def test_as_shape(self, tmp_path):
        ShapeModel.as_shape(
            geom_col="geom",
            srid=4326,
            data=file_model_data(ShapeModel),
            dir_path=str(tmp_path),
            file_name="out",
        )
        with zipfile.ZipFile(tmp_path / "out.zip") as zp:
            assert {name.split("_")[0] for name in zp.namelist()} == {"POINT", "POLYGON"}
        assert read_features(tmp_path / "POINT_out" / "POINT_out.shp") == [
            {"pk": 1, "name": "point"}
        ]

    def test_as_shape_fields(self, tmp_path):
        with pytest.warns(DeprecationWarning):
            ShapeModel.as_shape(
                geom_col="geom",
                srid=4326,
                data=file_model_data(ShapeModel),
                dir_path=str(tmp_path),
                file_name="out",
                columns=["name"],
            )
        assert read_features(tmp_path / "POLYGON_out" / "POLYGON_out.shp") == [{"name": "polygon"}]

    @pytest.mark.parametrize("fields", [[], ["pk", "geom"]])
    def test_as_geofile_gpkg(self, tmp_path, fields):
        GeofileModel.as_geofile(
            export_format="gpkg",
            geom_col="geom",
            srid=4326,
            data=file_model_data(GeofileModel),
            dir_path=str(tmp_path),
            file_name="out",
            fields=fields,
        )
        expected = [{"pk": 1, "name": "point"}, {"pk": 2, "name": "polygon"}]
        if fields:
            expected = [{"pk": row["pk"]} for row in expected]
        # row without geometry is skipped
        assert read_features(tmp_path / "out.gpkg") == expected

    def test_as_geofile_shp_columns(self, tmp_path):
        with pytest.warns(DeprecationWarning):
            GeofileModel.as_geofile(
                export_format="shp",
                geom_col="geom",
                srid=4326,
                data=file_model_data(GeofileModel),
                dir_path=str(tmp_path),
                file_name="out",
                columns=["name"],
            )
        assert read_features(tmp_path / "POINT_out" / "POINT_out.shp") == [{"name": "point"}]

    def test_as_geofile_unsupported_format(self, tmp_path):
        with pytest.raises(Exception, match="Unsupported format"):
            GeofileModel.as_geofile(export_format="csv", dir_path=str(tmp_path))


metadata = sa.MetaData()
query_table = sa.Table(
    "t_geo",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.Unicode),
    sa.Column("geom", Geometry("GEOMETRY", 4326)),
    schema=SCHEMA,
)


def intersects_square_query():
    square = from_shape(Polygon([(0, 0), (0, 2), (2, 2), (2, 0), (0, 0)]))
    return (
        sa.select(query_table.c.id, query_table.c.name, query_table.c.geom)
        .where(
            sa.func.ST_Intersects(query_table.c.geom, sa.func.ST_GeomFromWKB(square.data, 4326))
        )
        .where(query_table.c.id < 3)
    )


class TestQueryToGeojson:
    def test_sqla_query_to_text(self):
        txt = sqla_query_to_text(intersects_square_query())
        assert "ST_GeomFromWKB" not in txt
        assert "ST_GeomFromText('POLYGON ((0 0, 0 2, 2 2, 2 0, 0 0))', 4326)" in txt
        assert re.search(rf"{SCHEMA}.t_geo.id < 3", txt)

    def test_sqla_query_to_geojson(self, db):
        result = sqla_query_to_geojson(db.session, intersects_square_query(), "id", "geom")
        assert result["type"] == "FeatureCollection"
        # point (6 10) does not intersect the square
        assert [f["id"] for f in result["features"]] == [2]
        feature = result["features"][0]
        assert feature["geometry"] == {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}
        assert feature["properties"] == {"name": "line"}

    def test_txt_query_keep_id_col(self, db):
        query = f"SELECT id, name, geom FROM {SCHEMA}.t_geo WHERE id = 1"
        result = txt_query_as_geojson(db.session, query, "id", "geom", keep_id_col=True)
        assert result["features"][0]["properties"] == {"id": 1, "name": "point"}

    def test_txt_query_other_srid(self, db):
        query = f"SELECT id, ST_Transform(geom, 2154) AS geom FROM {SCHEMA}.t_geo WHERE id = 1"
        result = txt_query_as_geojson(db.session, query, "id", "geom", geom_srid=2154)
        coordinates = result["features"][0]["geometry"]["coordinates"]
        assert coordinates == pytest.approx([6, 10])

    def test_txt_query_is_geojson(self, db):
        query = f"SELECT id, ST_AsGeoJSON(geom) AS geojson FROM {SCHEMA}.t_geo WHERE id = 1"
        result = txt_query_as_geojson(db.session, query, "id", "geojson", is_geojson=True)
        assert result["features"][0]["geometry"] == {"type": "Point", "coordinates": [6, 10]}
        assert result["features"][0]["properties"] == {}
