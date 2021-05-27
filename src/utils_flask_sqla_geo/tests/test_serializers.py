import pytest
from unittest import TestCase

from shapely import wkt

from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry

from utils_flask_sqla_geo.serializers import geoserializable


db = SQLAlchemy()


class TestSerializers:
    def test_geom(self):
        @geoserializable
        class TestModel1(db.Model):
            pk = db.Column(db.Integer, primary_key=True)
            geom = db.Column(Geometry("GEOMETRY", 4326))

        o = TestModel1(pk=1, geom=wkt.loads('POINT(6 10)'))
        d = o.as_dict()
        TestCase().assertDictEqual({
            'pk': 1,
        }, d)

    def test_default_params(self):
        @geoserializable(exclude=['excluded'])
        class TestModel2(db.Model):
            pk = db.Column(db.Integer, primary_key=True)
            excluded = db.Column(db.Integer)
            geom = db.Column(Geometry("GEOMETRY", 4326))

        point = wkt.loads('POINT(6 10)')
        o = TestModel2(pk=1, excluded=2, geom=point)
        d = o.as_dict()
        TestCase().assertDictEqual({
            'pk': 1,
        }, d)

        d = o.as_dict(exclude=[])
        TestCase().assertDictEqual({
            'pk': 1,
            'excluded': 2,
            'geom': point,
        }, d)
