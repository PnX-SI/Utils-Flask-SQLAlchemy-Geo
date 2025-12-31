import json
from flask import jsonify
from marshmallow import fields
from geoalchemy2 import WKBElement
from shapely import to_geojson, from_wkb


class JsonifiableGenerator(list):
    """
    Inherite from list, so compatible with JSONEncoder, but must be initialized
    with a generator. Implement __bool__ as used by JSONEncoder.
    """

    def __init__(self, gen):
        self.gen = gen
        self.empty = None

    def __iter__(self):
        if self.empty is None:
            bool(self)
        if not self.empty:
            yield self.first_item
            yield from self.gen

    def __bool__(self):
        if self.empty is None:
            try:
                self.first_item = next(self.gen)
                self.empty = False
            except StopIteration:
                self.empty = True
        return not self.empty

    __repr__ = object.__repr__


class GeneratorField(fields.List):
    """
    As marshmallow List field, but if value is not a list (e.g. map or generator),
    return a JsonifiableGenerator instead of a list.
    """

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        result = map(lambda each: self.inner._serialize(each, attr, obj, **kwargs), value)
        if isinstance(value, list):
            result = list(result)
        else:
            result = JsonifiableGenerator(result)
        return result


def geojsonify(*args, **kwargs):
    response = jsonify(*args, **kwargs)
    response.mimetype = "application/geo+json"
    return response


def validGeoJSON(geojson):
    if "coordinates" in geojson and "type" in geojson:
        return geojson
    raise ValueError("Not a valid GeoJSON")


def parseGeom(geom):
    if isinstance(geom, WKBElement) or isinstance(geom, bytes):
        return json.loads(to_geojson(from_wkb(geom)))
    if isinstance(geom, dict):
        return validGeoJSON(geom)
    if isinstance(geom, str):
        try:
            geom = json.loads(geom)
            return validGeoJSON(geom)
        except json.JSONDecodeError:
            raise ValueError("Not a valid JSON")
        except ValueError:
            raise ValueError("Not a valid GeoJSON")

    raise ValueError(
        f"Not a valid type of geometry : {type(geom)}. Must be a GeoJSON dict or a GeoJSON string or WKBElement"
    )


def rows_to_geojson(rows, geom_field):
    features = []

    for row in rows:
        row = row._mapping  # SQLAlchemy Row → dict-like

        geom = row.get(geom_field)
        if geom:
            geometry = parseGeom(geom)
        else:
            geometry = None

        properties = {k: v for k, v in row.items() if k != geom_field}

        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": properties,
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
    }
