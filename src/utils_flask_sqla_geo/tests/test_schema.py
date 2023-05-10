import pytest
import json
from json import JSONEncoder
import re

import marshmallow as ma
from marshmallow.exceptions import ValidationError
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geometry
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point

from utils_flask_sqla.schema import SmartRelationshipsMixin
from utils_flask_sqla_geo.schema import GeoAlchemyAutoSchema


# TODO:
# - Test other geometries than Point & Polygon
# - Test relationships
# - Test geometry with third dimension


Base = declarative_base()


class Parent(Base):
    __tablename__ = "parent"
    pk = Column(Integer, primary_key=True)
    name = Column(String)
    geom = Column(Geometry("GEOMETRY", 4326))


# class ParentSchema(SmartRelationshipsMixin, GeoAlchemyAutoSchema):
class ParentSchema(GeoAlchemyAutoSchema):
    class Meta:
        model = Parent
        include_fk = True
        feature_id = "pk"


@pytest.fixture
def p1():
    return Parent(pk=1, name="p1", geom=from_shape(Point(6, 10)))


@pytest.fixture
def p2():
    return Parent(pk=2, name="p2", geom=from_shape(Point(10, 6)))


class TestGeoSchema:
    def test_to_json(self, p1):
        expected = {
            "pk": 1,
            "name": "p1",
            # geom field is automatically excluded
        }
        assert ParentSchema().dump(p1) == expected
        assert ParentSchema(only=["geom"]).dump(p1) == {
            "geom": {
                "type": "Point",
                "coordinates": (6.0, 10.0),
            },
        }
        assert ParentSchema(exclude=["pk"]).dump(p1) == {"name": "p1"}
        assert ParentSchema(only=["name", "geom"], exclude=["pk", "geom"]).dump(p1) == {
            "name": "p1"
        }

    def test_to_json_many(self, p1, p2):
        expected = [
            {
                "pk": 1,
                "name": "p1",
            },
            {
                "pk": 2,
                "name": "p2",
            },
        ]
        assert ParentSchema().dump([p1, p2], many=True) == expected
        assert ParentSchema(only=["pk", "geom"], exclude=["geom"]).dump([p1], many=True) == [
            {"pk": 1}
        ]
        assert ParentSchema(exclude=["pk"]).dump([p2], many=True) == [{"name": "p2"}]
        assert ParentSchema(only=["pk", "geom"], exclude=["pk"]).dump([p1], many=True) == [
            {"geom": {"type": "Point", "coordinates": (6, 10)}}
        ]

    def test_to_geojson_feature(self, p1):
        expected = {
            "id": 1,
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": (6.0, 10.0),
            },
            "properties": {
                "pk": 1,
                "name": "p1",
            },
        }
        assert ParentSchema(as_geojson=True).dump(p1) == expected
        expected = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": (6.0, 10.0),
            },
            "properties": {
                "name": "p1",
            },
        }
        assert ParentSchema(as_geojson=True, exclude=["pk", "geom"]).dump(p1) == expected
        expected = {
            "id": 1,
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": (6.0, 10.0),
            },
            "properties": {
                "pk": 1,
            },
        }
        assert ParentSchema(as_geojson=True, only=["pk", "geom"]).dump(p1) == expected
        assert ParentSchema(as_geojson=True, only=["pk"], exclude=["geom"]).dump(p1) == expected

    def test_to_geojson_feature_collection(self, p1, p2):
        expected = {
            "type": "FeatureCollection",
            "features": [
                {
                    "id": 1,
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": (6.0, 10.0),
                    },
                    "properties": {
                        "pk": 1,
                        "name": "p1",
                    },
                },
                {
                    "id": 2,
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": (10.0, 6.0),
                    },
                    "properties": {
                        "pk": 2,
                        "name": "p2",
                    },
                },
            ],
        }
        assert ParentSchema(as_geojson=True).dump([p1, p2], many=True) == expected

    def test_from_json(self):
        p1 = ParentSchema().load(
            {
                "name": "p1",
            }
        )
        p1 = ParentSchema().load(
            {
                "pk": 1,
                "name": "p1",
            }
        )

    def test_from_json_unexpected_geom(self):
        with pytest.raises(ValidationError, match="'geom': \\['Unknown field.'\\]"):
            ParentSchema().load(
                {
                    "pk": 1,
                    "name": "p1",
                    "geom": {
                        "type": "Point",
                        "coordinates": (6.0, 10.0),
                    },
                }
            )

    def test_from_geojson_feature(self):
        p1 = ParentSchema(as_geojson=True).load(
            {
                "id": 1,
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": (6.0, 10.0),
                },
                "properties": {
                    "pk": 1,
                    "name": "p1",
                },
            }
        )
        assert p1["pk"] == 1
        assert p1["name"] == "p1"
        assert to_shape(p1["geom"]).equals(Point(6, 10))

    def test_from_geojson_feature_collection(self):
        p1, p2 = ParentSchema(as_geojson=True).load(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "id": 1,
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": (6.0, 10.0),
                        },
                        "properties": {
                            "pk": 1,
                            "name": "p1",
                        },
                    },
                    {
                        "id": 2,
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": (10.0, 6.0),
                        },
                        "properties": {
                            "pk": 2,
                            "name": "p2",
                        },
                    },
                ],
            },
            many=True,
        )
        assert p1["pk"] == 1
        assert p1["name"] == "p1"
        assert to_shape(p1["geom"]).equals(Point(6, 10))
        assert p2["pk"] == 2
        assert p2["name"] == "p2"
        assert to_shape(p2["geom"]).equals(Point(10, 6))

    def test_to_geojson_null_geom(self):
        expected = {
            "id": 1,
            "type": "Feature",
            "geometry": None,
            "properties": {
                "pk": 1,
                "name": "p",
            },
        }
        p = Parent(pk=1, name="p")
        assert ParentSchema(as_geojson=True).dump(p) == expected

    def test_to_geojson_excluded_geom(self, p1):
        expected = {
            "id": 1,
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": (6.0, 10.0),
            },
            "properties": {
                "pk": 1,
                "name": "p1",
            },
        }
        assert ParentSchema(as_geojson=True, exclude=["geom"]).dump(p1) == expected

    def test_from_geojson_null_geom(self):
        p = ParentSchema(as_geojson=True).load(
            {
                "id": 1,
                "type": "Feature",
                "geometry": None,
                "properties": {
                    "pk": 1,
                    "name": "p",
                },
            }
        )

    def test_from_geojson_missing_geom(self):
        with pytest.raises(
            ValidationError, match="'geometry': \\['Missing data for required field.'\\]"
        ):
            ParentSchema(as_geojson=True).load(
                {
                    "id": 1,
                    "type": "Feature",
                    "properties": {
                        "pk": 1,
                        "name": "p",
                    },
                }
            )

    def test_from_geojson_bad_geom(self):
        with pytest.raises(
            ValidationError, match="'type': \\['Missing data for required field.'\\]"
        ):
            ParentSchema(as_geojson=True).load(
                {
                    "id": 1,
                    "type": "Feature",
                    "geometry": {
                        "invalid": "invalid",
                    },
                    "properties": {
                        "pk": 1,
                        "name": "p1",
                    },
                }
            )
        with pytest.raises(
            ValidationError, match="'coordinates': \\['Missing data for required field.'\\]"
        ):
            ParentSchema(as_geojson=True).load(
                {
                    "id": 1,
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                    },
                    "properties": {
                        "pk": 1,
                        "name": "p1",
                    },
                }
            )

    def test_from_geojson_invalid_geom(self):
        with pytest.raises(ValidationError, match="'geom': \\['Invalid geometry.'\\]"):
            p = ParentSchema(as_geojson=True).load(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                (0, 0),
                                (0, 3),
                                (3, 3),
                                (3, 0),
                                (2, 0),
                                (2, 2),
                                (1, 2),
                                (1, 1),
                                (2, 1),
                                (2, 0),
                                (0, 0),
                            ]
                        ],
                    },
                    "properties": {"pk": 1},
                }
            )

    def test_feature_id(self):
        class ModelA(Base):
            __tablename__ = "table_a"
            pk = Column(Integer, primary_key=True)
            name = Column(String)
            geom = Column(Geometry("GEOMETRY", 4326))

        class ModelASchema(GeoAlchemyAutoSchema):
            class Meta:
                model = ModelA
                include_fk = True

        a = ModelA(pk=1, name="a1")
        assert ModelASchema(as_geojson=True, only=["pk"]).dump(a) == {
            "type": "Feature",
            "geometry": None,
            "properties": {"pk": 1},
        }
        assert ModelASchema(as_geojson=True, only=["pk"], feature_id="name").dump(a) == {
            "type": "Feature",
            "geometry": None,
            "properties": {"pk": 1},
        }
        assert ModelASchema(as_geojson=True, only=["name"], feature_id="name").dump(a) == {
            "id": "a1",
            "type": "Feature",
            "geometry": None,
            "properties": {"name": "a1"},
        }

    def test_many_geometries(self):
        class ModelB(Base):
            __tablename__ = "table_b"
            pk = Column(Integer, primary_key=True)
            name = Column(String)
            geom1 = Column(Geometry("GEOMETRY", 4326))
            geom2 = Column(Geometry("GEOMETRY", 4326))

        class ModelBSchema1(GeoAlchemyAutoSchema):
            class Meta:
                model = ModelB
                include_fk = True

        class ModelBSchema2(GeoAlchemyAutoSchema):
            class Meta:
                model = ModelB
                include_fk = True
                feature_geometry = "geom2"

        ModelBSchema1(as_geojson=False)
        with pytest.raises(TypeError, match="Missing 'feature_geometry'"):
            ModelBSchema1(as_geojson=True)
        schema1 = ModelBSchema1(as_geojson=True, feature_geometry="geom2")
        ModelBSchema2(as_geojson=False)
        schema2 = ModelBSchema2(as_geojson=True)

        b = ModelB(
            pk=1, name="b1", geom1=from_shape(Point(1.2, 2.5)), geom2=from_shape(Point(3.5, 4.8))
        )
        expected = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": (3.5, 4.8),
            },
            "properties": {
                "pk": 1,
                "name": "b1",
            },
        }
        assert schema1.dump(b) == expected
        assert schema2.dump(b) == expected

    def test_generator_json(self):
        def generate_objects():
            for i in range(3):
                generate_objects.count += 1
                yield Parent(pk=i, name=f"Object {i}")

        generate_objects.count = 0

        schema = ParentSchema(as_geojson=False)

        d = schema.dump(generate_objects(), many=True)
        assert generate_objects.count == 0

        r = re.compile(r'"Object (\d+)"')
        result = ""
        for s in JSONEncoder().iterencode(d):
            g = r.match(s)
            if g:
                i = int(g.group(1))
                assert generate_objects.count == i + 1
            result += s

        # Verify json-string generated with iterencode is correct
        d = json.loads(result)
        expected = schema.dump(list(generate_objects()), many=True)
        assert d == expected

    def test_generator_geojson(self):
        def generate_objects():
            for i in range(3):
                generate_objects.count += 1
                yield Parent(pk=i, name=f"Object {i}")

        generate_objects.count = 0

        schema = ParentSchema(as_geojson=True)

        d = schema.dump(generate_objects(), many=True)
        assert generate_objects.count == 0

        r = re.compile(r'"Object (\d+)"')
        result = ""
        for s in JSONEncoder().iterencode(d):
            g = r.match(s)
            if g:
                i = int(g.group(1))
                assert generate_objects.count == i + 1
            result += s

        # Verify json-string generated with iterencode is correct
        d = json.loads(result)
        expected = schema.dump(list(generate_objects()), many=True)
        assert d == expected
