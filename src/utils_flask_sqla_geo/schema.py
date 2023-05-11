from enum import Enum

from marshmallow import Schema, fields, RAISE, EXCLUDE
from marshmallow.decorators import pre_load, post_dump
from marshmallow.validate import OneOf, Range
from marshmallow.exceptions import ValidationError

from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape, from_shape
from marshmallow_sqlalchemy.schema import SQLAlchemyAutoSchema, SQLAlchemyAutoSchemaOpts
from marshmallow_sqlalchemy.convert import ModelConverter
from marshmallow_geojson import (
    GeometryType,
    PointSchema,
    MultiPointSchema,
    PolygonSchema,
    MultiPolygonSchema,
    LineStringSchema,
    MultiLineStringSchema,
)
from shapely.geometry import shape
from shapely import wkt
from shapely.errors import WKTReadingError

from .utils import JsonifiableGenerator, GeneratorField


class GeometrySchema(Schema):
    schema_map = {
        GeometryType.point.value: PointSchema,
        GeometryType.multi_point.value: MultiPointSchema,
        GeometryType.polygon.value: PolygonSchema,
        GeometryType.multi_polygon.value: MultiPolygonSchema,
        GeometryType.line_string.value: LineStringSchema,
        GeometryType.multi_line_string.value: MultiLineStringSchema,
    }

    type = fields.Str(required=True, validate=OneOf(schema_map.keys()))

    def load(self, data, *, many=None, **kwargs):
        geometry_type = super().load(data, many=many, unknown=EXCLUDE)["type"]
        schema = self.schema_map[geometry_type]
        return schema(many=many, **kwargs).load(data)


class FeatureSchema(Schema):
    id = fields.Field()
    type = fields.Constant("Feature", required=True)
    # note: geometry validity done by GeometryField deserialization
    geometry = fields.Mapping(required=True, allow_none=True)
    properties = fields.Mapping(required=True)


class FeatureCollectionSchema(Schema):
    type = fields.Constant("FeatureCollection", required=True)
    features = GeneratorField(fields.Nested(FeatureSchema), required=True)


class GeometryField(fields.Field):
    geometry_schema = GeometrySchema()

    def _serialize_wkt(self, value, attr, obj):
        return to_shape(value).wkt if value else None

    def _serialize_geojson(self, value, attr, obj):
        return to_shape(value).__geo_interface__ if value else None

    def _deserialize_wkt(self, value, attr, data, **kwargs):
        try:
            return wkt.loads(value)
        except WKTReadingError as error:
            raise ValidationError("Invalid geometry.") from error

    def _deserialize_geojson(self, value, attr, data, **kwargs):
        try:
            geom = shape(self.geometry_schema.load(value))
            if not geom.is_valid:
                raise ValidationError("Invalid geometry.")
            if geom.has_z:
                raise ValidationError("Unexpected third dimension.")
            return from_shape(geom, srid=4326)
        except ValueError as error:
            raise ValidationError("Invalid geometry.") from error

    def _bind_to_schema(self, field_name, schema):
        super()._bind_to_schema
        if schema.as_geojson:
            self._serialize = self._serialize_geojson
            self._deserialize = self._deserialize_geojson
        else:
            self._serialize = self._serialize_wkt
            self._deserialize = self._deserialize_wkt


class GeoModelConverter(ModelConverter):
    """Model converter for models with geometric fields."""

    SQLA_TYPE_MAPPING = {
        **ModelConverter.SQLA_TYPE_MAPPING,
        Geometry: GeometryField,
    }


class GeoAlchemyAutoSchemaOpts(SQLAlchemyAutoSchemaOpts):
    """Options class for ``GeoAlchemyAutoSchema``.
    Adds the following options:

    - ``geometry_fields``: List of Geometry columns.
    - ``feature_id``: Identity field to use when generating features.
    - ``feature_geometry``: Geometry field to use when generating features.

    Thus, this options class define ``GeoModelConverter`` as default model converter.
    """

    def __init__(self, meta, *args, **kwargs):
        super().__init__(meta, *args, **kwargs)
        self.geometry_fields = set()
        if self.model:
            for column in self.model.__mapper__.columns:
                if isinstance(column.type, Geometry):
                    self.geometry_fields.add(column.key)
        # TODO: if self.table: …
        self.feature_id = getattr(meta, "feature_id", None)
        if len(self.geometry_fields) == 1:
            self.feature_geometry = getattr(
                meta, "feature_geometry", self.geometry_fields.copy().pop()
            )
        else:
            self.feature_geometry = getattr(meta, "feature_geometry", None)
        self.model_converter = getattr(meta, "model_converter", GeoModelConverter)


class GeoAlchemyAutoSchema(SQLAlchemyAutoSchema):
    """Auto schema with support for geometric fields and geojson generation.

    :param as_geojson: If ``true``, serialize and deserialize geojson instead of json.
    :param feature_id: Identity field to use when generating features.
        If ``None``, use ``feature_id`` specified on ``class Meta`` if any, otherwise
        features are generated without id.
    :param feature_geometry: Geometry field to use when generating features.
        If ``None``, use ``feature_geometry`` specified on ``class Meta``.
        If not specified on ``class Meta`` either, auto-detect the geometry field.
        If none or several geometric fields are detected, raise a ``TypeError``.

    Geometric fields are automatically removed from serialization.
    """

    OPTIONS_CLASS = GeoAlchemyAutoSchemaOpts

    def __init__(
        self,
        *args,
        as_geojson=False,
        feature_id=None,
        feature_geometry=None,
        only=None,
        exclude=(),
        **kwargs
    ):
        excluded_geometry_fields = self.opts.geometry_fields.copy()
        if only is not None:
            only = set(only)
            excluded_geometry_fields -= set(only)
        exclude = set(exclude) | excluded_geometry_fields
        self.as_geojson = as_geojson
        if as_geojson:
            self.feature_id = feature_id or self.opts.feature_id
            self.feature_geometry = feature_geometry or self.opts.feature_geometry
            if not self.feature_geometry:
                raise TypeError("Missing 'feature_geometry'")
            # Add feature geometry to serialized fields
            exclude.discard(self.feature_geometry)
            if only is not None:
                only = set(only) | {self.feature_geometry}
        super().__init__(*args, only=only, exclude=exclude, **kwargs)

    def to_feature(self, properties):
        feature = {
            "properties": properties,
            "geometry": properties.pop(self.feature_geometry),
        }
        if self.feature_id and self.feature_id in properties:
            feature.update(
                {
                    "id": properties[self.feature_id],
                }
            )
        return feature

    def from_feature(self, feature):
        properties = feature["properties"]
        properties[self.opts.feature_geometry] = feature["geometry"]
        return properties

    def _serialize(self, obj, *, many=None):
        if many:
            result = map(
                lambda o: super(GeoAlchemyAutoSchema, self)._serialize(o, many=False), obj
            )
            if isinstance(obj, list):
                return list(result)
            else:
                return result
        else:
            result = super(GeoAlchemyAutoSchema, self)._serialize(obj, many=False)
            return result

    @post_dump(pass_many=True)
    def to_geojson(self, data, many, **kwargs):
        if self.as_geojson:
            if many:
                features = map(self.to_feature, data)
                if isinstance(data, list):
                    features = list(features)
                return FeatureCollectionSchema().dump({"features": features})
            else:
                return FeatureSchema().dump(self.to_feature(data))
        else:
            if many and not isinstance(data, list):
                data = JsonifiableGenerator(data)
            return data

    @pre_load(pass_many=True)
    def from_geojson(self, data, many, **kwargs):
        if not self.as_geojson:
            return data
        if many:
            collection = FeatureCollectionSchema(partial=False, unknown=RAISE).load(data)
            return [self.from_feature(feature) for feature in collection["features"]]
        else:
            feature = FeatureSchema(partial=False, unknown=RAISE).load(data)
            return self.from_feature(feature)
