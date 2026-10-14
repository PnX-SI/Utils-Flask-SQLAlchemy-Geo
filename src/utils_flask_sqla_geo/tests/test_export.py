import csv
import io
import json

import fiona
import pytest
import sqlalchemy as sa

from utils_flask_sqla_geo.export import (
    export_csv,
    export_geojson,
    export_geopackage,
    export_json,
)
from utils_flask_sqla_geo.generic import GenericQueryGeo

from utils_flask_sqla_geo.tests.geo_test_db import SCHEMA, TABLE, db as _db

ROWS = [
    {"id": 1, "name": "point", "value": 10},
    {"id": 2, "name": "line", "value": 20},
    {"id": 3, "name": "polygon", "value": 30},
    {"id": 4, "name": "no geom", "value": 40},
]
WKT = ["POINT (6 10)", "LINESTRING (0 0, 1 1)", "POLYGON ((0 0, 0 1, 1 1, 1 0, 0 0))", None]


@pytest.fixture(scope="module")
def schema_class(app):
    return GenericQueryGeo(_db, TABLE, SCHEMA, geometry_field="geom").get_marshmallow_schema()


def select_all(db, schema_class):
    model = schema_class.Meta.model
    return db.session.scalars(sa.select(model).order_by(model.id))


@pytest.fixture
def query(db, schema_class):
    return select_all(db, schema_class)


def read_csv(fp):
    return list(csv.DictReader(io.StringIO(fp.getvalue()), delimiter=";"))


class TestExportCsv:
    def test_all_columns(self, query, schema_class):
        fp = io.StringIO()
        export_csv(query, schema_class, fp)
        assert read_csv(fp) == [{k: str(v) for k, v in row.items()} for row in ROWS]

    def test_columns(self, query, schema_class):
        fp = io.StringIO()
        export_csv(query, schema_class, fp, columns=["id", "name"], separator=",")
        rows = list(csv.DictReader(io.StringIO(fp.getvalue()), delimiter=","))
        assert rows[0] == {"id": "1", "name": "point"}

    def test_geometry(self, query, schema_class):
        fp = io.StringIO()
        export_csv(query, schema_class, fp, columns=["id"], geometry_field_name="geom")
        assert [row["geom"] for row in read_csv(fp)] == [w or "" for w in WKT]


class TestExportJson:
    def test_all_columns(self, query, schema_class):
        fp = io.StringIO()
        export_json(query, schema_class, fp, chunk_size=2)
        assert json.loads(fp.getvalue()) == ROWS

    def test_geometry(self, query, schema_class):
        fp = io.StringIO()
        export_json(query, schema_class, fp, columns=["id"], geometry_field_name="geom")
        assert json.loads(fp.getvalue()) == [
            {"id": row["id"], "geom": wkt} for row, wkt in zip(ROWS, WKT)
        ]

    def test_default_columns_not_mutated(self, db, schema_class):
        # a result can only be consumed once: use a new one for each export
        export_json(
            select_all(db, schema_class), schema_class, io.StringIO(), geometry_field_name="geom"
        )
        fp = io.StringIO()
        export_json(select_all(db, schema_class), schema_class, fp)
        assert json.loads(fp.getvalue()) == ROWS


class TestExportGeojson:
    def test_feature_collection(self, query, schema_class):
        fp = io.StringIO()
        export_geojson(query, schema_class, fp)
        collection = json.loads(fp.getvalue())
        assert collection["type"] == "FeatureCollection"
        assert [f["properties"] for f in collection["features"]] == ROWS
        assert [f["geometry"] and f["geometry"]["type"] for f in collection["features"]] == [
            "Point",
            "LineString",
            "Polygon",
            None,
        ]

    def test_columns(self, query, schema_class):
        fp = io.StringIO()
        export_geojson(query, schema_class, fp, columns=["name"], geometry_field_name="geom")
        collection = json.loads(fp.getvalue())
        assert collection["features"][0]["properties"] == {"name": "point"}


class TestExportGeopackage:
    def test_all_columns(self, query, schema_class, tmp_path):
        export_geopackage(query, schema_class, str(tmp_path / "out.gpkg"), 4326)
        with fiona.open(tmp_path / "out.gpkg") as f:
            assert f.crs.to_epsg() == 4326
            features = list(f)
        assert [dict(feature["properties"]) for feature in features] == ROWS
        assert features[3]["geometry"] is None

    def test_columns(self, query, schema_class, tmp_path):
        export_geopackage(
            query, schema_class, str(tmp_path / "out.gpkg"), 4326, columns=["id", "name"]
        )
        with fiona.open(tmp_path / "out.gpkg") as f:
            assert list(f.schema["properties"]) == ["id", "name"]
            assert dict(next(iter(f))["properties"]) == {"id": 1, "name": "point"}
