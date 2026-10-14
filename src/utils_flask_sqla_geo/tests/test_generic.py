import zipfile

import fiona
import sqlalchemy as sa
import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from utils_flask_sqla_geo.generic import GenericQueryGeo, GenericTableGeo, get_geojson_feature
from utils_flask_sqla_geo.schema import GeoAlchemyAutoSchema

from utils_flask_sqla_geo.tests.geo_test_db import SCHEMA, TABLE

# A polygon intersecting the line and the polygon of the test table, but not the point
INTERSECTING_WKT = "POLYGON((-1 -1, -1 2, 2 2, 2 -1, -1 -1))"


def test_get_geojson_feature():
    feature = get_geojson_feature(from_shape(Point(6, 10)))
    assert feature["geometry"] == {"type": "Point", "coordinates": [6.0, 10.0]}
    assert feature["properties"] == {}


class TestGenericTableGeo:
    def test_not_a_geometry_column(self, db):
        with pytest.raises(TypeError, match="field name is not a geometry column"):
            GenericTableGeo(TABLE, SCHEMA, db.engine, geometry_field="name")

    def test_unknown_column(self, db):
        with pytest.raises(KeyError, match="field unknown doesn't exists"):
            GenericTableGeo(TABLE, SCHEMA, db.engine, geometry_field="unknown")

    def test_as_geofeature(self, db):
        view = GenericTableGeo(TABLE, SCHEMA, db.engine, geometry_field="geom", srid=4326)
        rows = {row.id: row for row in db.session.query(view.tableDef)}

        feature = view.as_geofeature(rows[1])
        assert feature["geometry"] == {"type": "Point", "coordinates": [6.0, 10.0]}
        assert feature["properties"] == {"id": 1, "name": "point", "value": 10}

        assert view.as_geofeature(rows[1], fields=["name"])["properties"] == {"name": "point"}
        with pytest.warns(DeprecationWarning):
            feature = view.as_geofeature(rows[1], columns=["name"])
        assert feature["properties"] == {"name": "point"}

        # no feature for rows without geometry
        assert view.as_geofeature(rows[4]) is None

    def test_as_shape(self, db, tmp_path):
        view = GenericTableGeo(TABLE, SCHEMA, db.engine, geometry_field="geom", srid=4326)
        data = db.session.query(view.tableDef).all()
        with pytest.warns(DeprecationWarning):
            view.as_shape(view.db_cols, data=data, dir_path=str(tmp_path), file_name="out")
        with zipfile.ZipFile(tmp_path / "out.zip") as zp:
            prefixes = {name.split("_")[0] for name in zp.namelist()}
        assert prefixes == {"POINT", "POLYLINE", "POLYGON"}

    def test_as_geofile_gpkg(self, db, tmp_path):
        view = GenericTableGeo(TABLE, SCHEMA, db.engine, geometry_field="geom", srid=4326)
        data = db.session.query(view.tableDef).all()
        with pytest.warns(DeprecationWarning):
            view.as_geofile(
                "gpkg", view.db_cols, data=data, dir_path=str(tmp_path), file_name="out"
            )
        with fiona.open(tmp_path / "out.gpkg") as f:
            # row without geometry is skipped
            assert sorted(feature["properties"]["name"] for feature in f) == [
                "line",
                "point",
                "polygon",
            ]

    def test_as_geofile_unsupported_format(self, db, tmp_path):
        view = GenericTableGeo(TABLE, SCHEMA, db.engine, geometry_field="geom", srid=4326)
        with pytest.raises(Exception, match="Unsupported format"):
            view.as_geofile("csv", view.db_cols, dir_path=str(tmp_path))


class TestGenericQueryGeo:
    def test_as_geofeature(self, db):
        result = GenericQueryGeo(db, TABLE, SCHEMA, geometry_field="geom").as_geofeature()
        assert result["total"] == 4
        assert result["total_filtered"] == 4
        assert result["page"] == 0
        assert result["limit"] == 100
        # row without geometry is excluded from the feature collection
        assert result["items"]["type"] == "FeatureCollection"
        assert [f["properties"]["id"] for f in result["items"]["features"]] == [1, 2, 3]

    def test_without_geometry_field(self, db):
        result = GenericQueryGeo(db, TABLE, SCHEMA).return_query()
        assert result["items"] == [
            {"id": 1, "name": "point", "value": 10},
            {"id": 2, "name": "line", "value": 20},
            {"id": 3, "name": "polygon", "value": 30},
            {"id": 4, "name": "no geom", "value": 40},
        ]

    @pytest.mark.parametrize("srid", [None, 4326])
    def test_geometry_filter(self, db, srid):
        query = GenericQueryGeo(
            db,
            TABLE,
            SCHEMA,
            geometry_field="geom",
            srid=srid,
            filters={"geometry": INTERSECTING_WKT, "orderby": "id:desc"},
        )
        result = query.as_geofeature()
        assert result["total"] == 4
        assert result["total_filtered"] == 2
        assert [f["properties"]["id"] for f in result["items"]["features"]] == [3, 2]

    def test_regular_filter(self, db):
        query = GenericQueryGeo(db, TABLE, SCHEMA, geometry_field="geom", filters={"name": "line"})
        result = query.as_geofeature()
        assert [f["properties"]["id"] for f in result["items"]["features"]] == [2]

    def test_get_model(self, db):
        model = GenericQueryGeo(db, TABLE, SCHEMA, geometry_field="geom").get_model()
        assert model.__mapper__.primary_key[0].key == "id"
        assert {o.name for o in db.session.query(model)} == {"point", "line", "polygon", "no geom"}

    def test_get_model_explicit_pk(self, db):
        model = GenericQueryGeo(db, TABLE, SCHEMA).get_model(pk_name="name")
        assert model.__mapper__.primary_key[0].key == "name"

    def test_get_model_without_pk(self, db):
        # first column is used as primary key
        model = GenericQueryGeo(db, "t_nopk", SCHEMA).get_model()
        assert model.__mapper__.primary_key[0].key == "code"

    def test_get_model_unknown_pk(self, db):
        with pytest.raises(Exception, match="unknown cannot be found in table"):
            GenericQueryGeo(db, TABLE, SCHEMA).get_model(pk_name="unknown")

    def test_get_marshmallow_schema(self, db):
        schema_class = GenericQueryGeo(
            db, TABLE, SCHEMA, geometry_field="geom"
        ).get_marshmallow_schema()
        assert issubclass(schema_class, GeoAlchemyAutoSchema)
        obj = db.session.query(schema_class.Meta.model).filter_by(id=1).one()
        assert schema_class().dump(obj) == {"id": 1, "name": "point", "value": 10}
        assert schema_class(as_geojson=True).dump(obj)["geometry"] == {
            "type": "Point",
            "coordinates": (6.0, 10.0),
        }


class TestRollback:
    """Changes committed by a test are rolled back by the utils_flask_sqla temporary
    transaction fixtures (tests run in definition order)"""

    def test_insert_and_commit(self, db):
        db.session.execute(sa.text(f"INSERT INTO {SCHEMA}.{TABLE} (id, name) VALUES (5, 'new')"))
        db.session.commit()
        assert GenericQueryGeo(db, TABLE, SCHEMA).as_geofeature()["total"] == 5

    def test_insert_was_rolled_back(self, db):
        assert GenericQueryGeo(db, TABLE, SCHEMA).as_geofeature()["total"] == 4
