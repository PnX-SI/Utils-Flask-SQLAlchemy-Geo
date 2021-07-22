from itertools import chain
from warnings import warn

from geojson import Feature, FeatureCollection
from geoalchemy2.shape import to_shape
from utils_flask_sqla.generic import GenericQuery, GenericTable
from .utilsgeometry import create_shapes_generic, export_geodata_as_file


def get_geojson_feature(wkb):
    """ retourne une feature geojson à partir d'un WKB"""
    geometry = to_shape(wkb)
    feature = Feature(geometry=geometry, properties={})
    return feature


class GenericTableGeo(GenericTable):
    """
        Classe permettant de créer à la volée un mapping
            d'une vue avec la base de données par rétroingénierie
            gère les géométries
    """

    def __init__(self, tableName, schemaName, engine, geometry_field=None, srid=None):

        super().__init__(tableName, schemaName, engine)

        if geometry_field:
            try:
                if (
                    not self.tableDef.columns[geometry_field].type.__class__.__name__
                    == "Geometry"
                ):
                    raise TypeError(
                        "field {} is not a geometry column".format(
                            geometry_field)
                    )
            except KeyError:
                raise KeyError(
                    "field {} doesn't exists".format(geometry_field))

        self.geometry_field = geometry_field
        self.srid = srid

    def as_geofeature(self, data, columns=[], fields=[]):
        fields = list(chain(fields, columns))
        if columns:
            warn("'columns' argument is deprecated. Please add columns to serialize "
                    "directly in 'fields' argument.", DeprecationWarning)
        if getattr(data, self.geometry_field) is not None:
            geometry = to_shape(getattr(data, self.geometry_field))
            return Feature(geometry=geometry, properties=self.as_dict(data, fields))

    def as_shape(
        self, db_cols, geojson_col=None, data=[], dir_path=None, file_name=None
    ):
        """
        # RMQ Pour le moment conservé pour des questions de rétrocompatibilité

        Create shapefile for generic table
        Parameters:
            db_cols (list): columns from a SQLA model (model.__mapper__.c)
            geojson_col (str): the geojson (from st_asgeojson()) column of the mapped table if exist
                            if None, take the geom_col (WKB) to generate geometry with shapely
            data (list<Model>): list of data of the shapefiles
            dir_path (str): directory path
            file_name (str): name of the file
        Returns
            Void (create a shapefile)
        """

        create_shapes_generic(
            view=self,
            db_cols=db_cols,
            srid=self.srid,
            data=data,
            geom_col=self.geometry_field,
            geojson_col=geojson_col,
            dir_path=dir_path,
            file_name=file_name,
        )

    def as_geofile(
        self, export_format, db_cols, geojson_col=None, data=[], dir_path=None, file_name=None
    ):
        """
        Create shapefile or geopackage for generic table
        Parameters:
            export_format (str): file format (shp or gpkg)
            db_cols (list): columns from a SQLA model (model.__mapper__.c)
            geojson_col (str): the geojson (from st_asgeojson()) column of the mapped table if exist
                            if None, take the geom_col (WKB) to generate geometry with shapely
            data (list<Model>): list of data of the shapefiles
            dir_path (str): directory path
            file_name (str): name of the file
        Returns
            Void (create a shapefile)
        """
        if export_format not in ("shp", "gpkg"):
            raise Exception("Unsupported format")

        export_geodata_as_file(
            view=self,
            db_cols=db_cols,
            srid=self.srid,
            data=data,
            geom_col=self.geometry_field,
            geojson_col=geojson_col,
            dir_path=dir_path,
            file_name=file_name,
            export_format=export_format
        )


class GenericQueryGeo(GenericQuery):
    """
        Classe permettant de manipuler des objets GenericTable
        gère les géométries
    """

    def __init__(
        self,
        DB,
        tableName,
        schemaName,
        filters=[],
        limit=100,
        offset=0,
        geometry_field=None,
        srid=None
    ):

        super().__init__(DB, tableName, schemaName, filters, limit, offset)

        self.geometry_field = geometry_field
        self.view = GenericTableGeo(
            tableName=tableName,
            schemaName=schemaName,
            engine=DB.engine,
            geometry_field=geometry_field,
            srid=srid
        )

    def as_geofeature(self):

        data, nb_result_without_filter, nb_results = self.query()

        if self.geometry_field:
            results = FeatureCollection(
                [
                    self.view.as_geofeature(d)
                    for d in data
                    if getattr(d, self.geometry_field) is not None
                ]
            )
        else:
            results = [self.view.as_dict(d) for d in data]

        return {
            "total": nb_result_without_filter,
            "total_filtered": nb_results,
            "page": self.offset,
            "limit": self.limit,
            "items": results,
        }
