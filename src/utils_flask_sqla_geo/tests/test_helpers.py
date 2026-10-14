import json

from flask import Flask
from geojson import Feature
from marshmallow import Schema, fields

from utils_flask_sqla_geo.mixins import GeoFeatureCollectionMixin
from utils_flask_sqla_geo.utils import GeneratorField, JsonifiableGenerator, geojsonify


class TestJsonifiableGenerator:
    def test_non_empty(self):
        gen = JsonifiableGenerator(iter([1, 2, 3]))
        assert gen
        assert list(gen) == [1, 2, 3]

    def test_iter_without_bool(self):
        assert list(JsonifiableGenerator(x for x in "ab")) == ["a", "b"]

    def test_empty(self):
        gen = JsonifiableGenerator(iter([]))
        assert not gen
        assert list(gen) == []

    def test_json_encoding(self):
        assert json.dumps(JsonifiableGenerator(iter([1, 2]))) == "[1, 2]"
        assert json.dumps(JsonifiableGenerator(iter([]))) == "[]"


class GeneratorSchema(Schema):
    values = GeneratorField(fields.Integer(), allow_none=True)


class TestGeneratorField:
    def test_list(self):
        assert GeneratorSchema().dump({"values": [1, 2]}) == {"values": [1, 2]}

    def test_generator(self):
        result = GeneratorSchema().dump({"values": (i for i in range(3))})
        assert isinstance(result["values"], JsonifiableGenerator)
        assert list(result["values"]) == [0, 1, 2]

    def test_none(self):
        assert GeneratorSchema().dump({"values": None}) == {"values": None}


def test_geojsonify():
    app = Flask(__name__)
    with app.app_context():
        response = geojsonify({"type": "FeatureCollection", "features": []})
    assert response.mimetype == "application/geo+json"
    assert response.get_json() == {"type": "FeatureCollection", "features": []}


class FakeQuery(GeoFeatureCollectionMixin):
    def __init__(self, objects):
        self.objects = objects

    def all(self):
        return self.objects


class FakeObject:
    def __init__(self, id):
        self.id = id

    def as_geofeature(self, *args, **kwargs):
        return Feature(id=self.id, geometry=None, properties=kwargs)


def test_as_geofeaturecollection():
    collection = FakeQuery([FakeObject(1), FakeObject(2)]).as_geofeaturecollection(name="x")
    assert collection["type"] == "FeatureCollection"
    assert [f["id"] for f in collection["features"]] == [1, 2]
    assert collection["features"][0]["properties"] == {"name": "x"}
