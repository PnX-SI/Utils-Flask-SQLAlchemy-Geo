from geojson import FeatureCollection


class GeoFeatureCollectionMixin:
    def as_geofeaturecollection(self, *args, **kwargs):
        return FeatureCollection([ o.as_geofeature(*args, **kwargs) for o in self.all() ])
