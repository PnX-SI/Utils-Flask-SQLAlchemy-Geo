import ast

from abc import ABC, abstractmethod
from collections import OrderedDict

import numpy as np
import geog
import zipfile
import fiona

from fiona.crs import from_epsg
from geoalchemy2.shape import to_shape
from shapely.geometry import (
    mapping,
    shape,
    Point,
    MultiPoint,
    Polygon,
    MultiPolygon,
    LineString,
    MultiLineString,
    LinearRing,
    GeometryCollection,
)

from utils_flask_sqla.errors import UtilsSqlaError

# Creation des shapefiles avec la librairies fiona

FIONA_MAPPING = {
    "date": "str",
    "datetime": "str",
    "time": "str",
    "timestamp": "str",
    "uuid": "str",
    "text": "str",
    "unicode": "str",
    "varchar": "str",
    "char": "str",
    "integer": "int",
    "bigint": "int",
    "float": "float",
    "boolean": "str",
    "double_precision": "float",
    "jsonb": "str",
    "json": "str",
}

class FionaService(ABC):
    """
    Abstract class to provide functions to create geofiles with Fiona
    Class who inherite of this class must implement the following abstract methods:
    - create_fiona_struct
    - create_features_generic
    - save-files
    - close-files
    """

    supported_type = ("shp", "gpkg")

    @classmethod
    def create_fiona_properties(cls, db_cols, srid, dir_path, file_name, col_mapping=None):
        """
        Create three shapefiles (point, line, polygon) with the attributes give by db_cols
        Parameters:
            db_cols (list): columns from a SQLA model (model.__mapper__.c)
            srid (int): epsg code
            dir_path (str): directory path
            file_name (str): file of the shapefiles
            col_mapping (dict): mapping between SQLA class
                            attributes and 'beatifiul' columns name

        Returns:
            void
        """
        cls.db_cols = db_cols
        cls.source_crs = from_epsg(srid)
        cls.dir_path = dir_path
        cls.file_name = file_name
        cls.columns = []
        # if we want to change to columns name of the SQLA class
        # in the export shapefiles structures
        cls.shp_properties = OrderedDict()
        if col_mapping:
            for db_col in db_cols:
                cls.add_fiona_col_mapping(col_mapping.get(db_col.key), db_col)
        else:
            for db_col in db_cols:
                cls.add_fiona_col_mapping(db_col.key, db_col)

    @classmethod
    def add_fiona_col_mapping(cls, key, db_col):
        if not db_col.type.__class__.__name__ == "Geometry":
            cls.shp_properties.update(
                {key: FIONA_MAPPING.get(db_col.type.__class__.__name__.lower(), "str")}
            )
            cls.columns.append(key)

    @classmethod
    def create_features_generic(cls, view, data, geom_col, geojson_col=None):
        """
        Create the features of the shapefiles by serializing the datas from a GenericTable (non mapped table)

        Parameters:
            view (GenericTable): the GenericTable object
            data (list): Array of SQLA model
            geom_col (str): name of the WKB geometry column of the SQLA Model
            geojson_col (str): name of the geojson column if present. If None create the geojson from geom_col with shapely
                               for performance reason its better to use geojson_col rather than geom_col

        Returns:
            void

        """
        # if the geojson col is not given
        # build it with shapely via the WKB col
        if geojson_col is None:
            is_geojson = False
            geo_colname = geom_col
        else:
            is_geojson = True
            geo_colname = geojson_col

        for d in data:
            try:
                cls.build_feature(view, d, geo_colname, is_geojson)
            except UtilsSqlaError as e:
                # TODO raise error or warning ??
                pass

        cls.close_files()

    @classmethod
    def build_feature(cls, view, data, geo_colname, is_geojson):
        """
        Fonction qui créer une feature au sens de fiona

        Parameters:
            view (GenericTable): the GenericTable object
            is_geojson (boolean): la geometrie est elle sous forme de geojson
            data (Model) : SQLA model
            geo_colname (string) : nom de la colonne contenant le geom
        """
        # Test if geom data exists
        if not hasattr(data, geo_colname):
            raise UtilsSqlaError("Cannot create a shapefile record whithout a Geometry")
        # Build geometry
        if is_geojson:
            geom = ast.literal_eval(getattr(data, geo_colname))

        else:
            geom = getattr(data, geo_colname)

        # Build feature
        cls.create_feature(view.as_dict(data, columns=cls.columns), geom, is_geojson)

    @classmethod
    def create_feature(cls, data, geom, is_geojson=False):
        """
        Create and write feature (a record of the file) for WKB data
        by serializing an SQLAlchemy object

        Parameters:
            data (dict): the SQLAlchemy model serialized as a dict
            geom (WKB): the geom as WKB


        Returns:
            void
        """
        try:
            if is_geojson:
                geom_wkt = shape(geom)
                geom_geojson = geom
            else:
                geom_wkt = to_shape(geom)
                geom_geojson = mapping(geom_wkt)
            feature = {"geometry": geom_geojson, "properties": data}
            cls.write_a_feature(feature, geom_wkt)
        except AssertionError:
            # TODO déplacer car le fichier est fermé à la moindre erreur
            cls.close_files()
            raise UtilsSqlaError("Cannot create a shapefile record whithout a Geometry")
        except Exception as e:
            # TODO déplacer car le fichier est fermé à la moindre erreur
            cls.close_files()
            raise UtilsSqlaError(e)

    @classmethod
    @abstractmethod
    def create_fiona_struct(cls, db_cols, srid, dir_path, file_name, col_mapping=None):
        pass

    @classmethod
    @abstractmethod
    def write_a_feature(cls, feature, geom_wkt):
        pass

    @classmethod
    @abstractmethod
    def save_files(cls):
        pass

    @classmethod
    @abstractmethod
    def close_files(cls):
        pass


class FionaGpkgService(FionaService):
    """
    Service to create gpkg from sqlalchemy models

    How to use:
    FionaShapeService.create_shapes_struct(**args)
    FionaShapeService.create_features(**args)
    FionaShapeService.save_and_zip_shapefiles()
    """

    @classmethod
    def create_fiona_struct(cls, db_cols, srid, dir_path, file_name, col_mapping=None):
        cls.export_type = "gpkg"
        cls.create_fiona_properties(db_cols, srid, dir_path, file_name, col_mapping)

        cls.gpkg_schema = {"geometry": "Unknown", "properties": cls.shp_properties}

        cls.filename_gpkg = cls.dir_path + "/" + cls.file_name + ".gpkg"

        cls.gpkg_file = fiona.open(
            cls.filename_gpkg,
            "w",
            "GPKG",
            cls.gpkg_schema,
            crs=cls.source_crs,
        )

    @classmethod
    def write_a_feature(cls, feature, geom_wkt):
        """
        write a feature by checking the type of the shape given
        """
        cls.gpkg_file.write(feature)

    @classmethod
    def save_files(cls):
        """
        Save and zip the files
        Only zip files where there is at least on feature

        Returns:
            void
        """
        cls.export_type = "gpkg"
        cls.close_files()

    @classmethod
    def close_files(cls):
        """
        Save the files
        """
        cls.gpkg_file.close()


class FionaShapeService(FionaService):
    """
    Service to create shapefiles from sqlalchemy models

    How to use:
    FionaShapeService.create_shapes_struct(**args)
    FionaShapeService.create_features(**args)
    FionaShapeService.save_and_zip_shapefiles()
    """

    @classmethod
    def create_fiona_struct(cls, db_cols, srid, dir_path, file_name, col_mapping=None):
        """
        Create three shapefiles (point, line, polygon) with the attributes give by db_cols
        Parameters:
            db_cols (list): columns from a SQLA model (model.__mapper__.c)
            srid (int): epsg code
            dir_path (str): directory path
            file_name (str): file of the shapefiles
            col_mapping (dict): mapping between SQLA class attributes and 'beatifiul' columns name

        Returns:
            void
        """
        cls.export_type = "shp"
        # Création structure des proprités fiona
        cls.create_fiona_properties(db_cols, srid, dir_path, file_name, col_mapping)

        cls.polygon_schema = {
            "geometry": ["Polygon", "MultiPolygon"],
            "properties": cls.shp_properties,
        }
        cls.point_schema = {
            "geometry": ["Point", "MultiPoint"],
            "properties": cls.shp_properties,
        }
        cls.polyline_schema = {
            "geometry": ["LineString", "MultiLineString"],
            "properties": cls.shp_properties,
        }

        cls.file_point = cls.dir_path + "/POINT_" + cls.file_name
        cls.file_poly = cls.dir_path + "/POLYGON_" + cls.file_name
        cls.file_line = cls.dir_path + "/POLYLINE_" + cls.file_name
        # boolean to check if features are register in the shapefile
        cls.point_feature = False
        cls.polygon_feature = False
        cls.polyline_feature = False
        cls.point_shape = fiona.open(
            cls.file_point, "w", "ESRI Shapefile", cls.point_schema, crs=cls.source_crs
        )
        cls.polygone_shape = fiona.open(
            cls.file_poly, "w", "ESRI Shapefile", cls.polygon_schema, crs=cls.source_crs
        )
        cls.polyline_shape = fiona.open(
            cls.file_line,
            "w",
            "ESRI Shapefile",
            cls.polyline_schema,
            crs=cls.source_crs,
        )

    # TODO mark as deprecated
    create_shapes_struct = create_fiona_struct

    @classmethod
    def write_a_feature(cls, feature, geom_wkt):
        """
        write a feature by checking the type of the shape given
        """
        if isinstance(geom_wkt, Point):
            # Transform point as multipoint :
            #   In shape file point and multipoint canot be mixed
            geom_geojson = mapping(MultiPoint([geom_wkt]))
            feature["geometry"] = geom_geojson
            cls.point_shape.write(feature)
            cls.point_feature = True
        elif isinstance(geom_wkt, MultiPoint):
            cls.point_shape.write(feature)
            cls.point_feature = True
        elif isinstance(geom_wkt, Polygon) or isinstance(geom_wkt, MultiPolygon):
            cls.polygone_shape.write(feature)
            cls.polygon_feature = True
        elif isinstance(geom_wkt, LineString) or isinstance(geom_wkt, MultiLineString):
            cls.polyline_shape.write(feature)
            cls.polyline_feature = True

    @classmethod
    def save_files(cls):
        """
        Save and zip the files
        Only zip files where there is at least on feature

        Returns:
            void
        """
        cls.export_type = "shp"
        cls.close_files()

        format_to_save = []
        if cls.point_feature:
            format_to_save = ["POINT"]
        if cls.polygon_feature:
            format_to_save.append("POLYGON")
        if cls.polyline_feature:
            format_to_save.append("POLYLINE")

        zip_path = cls.dir_path + "/" + cls.file_name + ".zip"
        zp_file = zipfile.ZipFile(zip_path, mode="w")

        for shape_format in format_to_save:
            final_file_name = cls.dir_path + "/" + shape_format + "_" + cls.file_name
            final_file_name = (
                "{dir_path}/{shape_format}_{file_name}/{shape_format}_{file_name}".format(
                    dir_path=cls.dir_path,
                    shape_format=shape_format,
                    file_name=cls.file_name,
                )
            )
            extentions = ("dbf", "shx", "shp", "prj")
            for ext in extentions:
                zp_file.write(
                    final_file_name + "." + ext,
                    shape_format + "_" + cls.file_name + "." + ext,
                )
        zp_file.close()

    # TODO mark as deprecated
    save_and_zip_shapefiles = save_files

    @classmethod
    def close_files(cls):
        cls.point_shape.close()
        cls.polygone_shape.close()
        cls.polyline_shape.close()


def create_shapes_generic(view, srid, db_cols, data, dir_path, file_name, geom_col, geojson_col):
    """
    Export data in shape files (separated bu geometry type)
    Parameters:
        srid (int): epsg code
        db_cols (list): columns from a SQLA model (model.__mapper__.c)
        data (list): Array of SQLA model
        dir_path (str): directory path
        file_name (str): file of the shapefiles
        geom_col (str): name of the WKB geometry column of the SQLA Model
        geojson_col (str): name of the geojson column if present. If None create the geojson from geom_col with shapely
                           for performance reason its better to use geojson_col rather than geom_col
    """

    FionaShapeService.create_shapes_struct(db_cols, srid, dir_path, file_name)
    FionaShapeService.create_features_generic(view, data, geom_col, geojson_col)
    FionaShapeService.save_and_zip_shapefiles()


def create_gpkg_generic(view, srid, db_cols, data, dir_path, file_name, geom_col, geojson_col):
    """
    Export data in gpkg file
    Parameters:
        srid (int): epsg code
        db_cols (list): columns from a SQLA model (model.__mapper__.c)
        data (list): Array of SQLA model
        dir_path (str): directory path
        file_name (str): file of the shapefiles
        geom_col (str): name of the WKB geometry column of the SQLA Model
        geojson_col (str): name of the geojson column if present. If None create the geojson from geom_col with shapely
                           for performance reason its better to use geojson_col rather than geom_col
    """

    FionaGpkgService.create_fiona_struct(db_cols, srid, dir_path, file_name)
    FionaGpkgService.create_features_generic(view, data, geom_col, geojson_col)
    FionaGpkgService.save_files()


def export_geodata_as_file(
    view,
    srid,
    db_cols,
    data,
    dir_path,
    file_name,
    geom_col,
    geojson_col,
    export_format="gpkg",
):
    """
    Generic export data
    Parameters:
        srid (int): epsg code
        db_cols (list): columns from a SQLA model (model.__mapper__.c)
        data (list): Array of SQLA model
        dir_path (str): directory path
        file_name (str): file of the shapefiles
        geom_col (str): name of the WKB geometry column of the SQLA Model
        geojson_col (str): name of the geojson column if present. If None create the geojson from geom_col with shapely
                           for performance reason its better to use geojson_col rather than geom_col
        export_format (str) : name of the exported format
    """
    if export_format == "gpkg":
        create_gpkg_generic(view, srid, db_cols, data, dir_path, file_name, geom_col, geojson_col)
    elif export_format == "shp":
        create_shapes_generic(
            view, srid, db_cols, data, dir_path, file_name, geom_col, geojson_col
        )
    else:
        # TODO raise ERROR unsupported format
        pass


def circle_from_point(point, radius, nb_point=20):
    """
    return a circle (shapely POLYGON) from a point
    parameters:
        - point: a shapely POINT
        - radius: circle's diameter in meter
        - nb_point: nb of point of the polygo,

    """
    angles = np.linspace(0, 360, nb_point)
    polygon = geog.propagate(point, angles, radius)
    return Polygon(polygon)


def convert_to_2d(geojson):
    """
    Convert a geojson 3d in 2d
    """
    # if its a Linestring, Polygon etc...
    if geojson["coordinates"][0] is list:
        two_d_coordinates = [[coord[0], coord[1]] for coord in geojson["coordinates"]]
    else:
        two_d_coordinates = [geojson["coordinates"][0], geojson["coordinates"][1]]

    geojson["coordinates"] = two_d_coordinates


def remove_third_dimension(geom):
    if not geom.has_z:
        return geom

    if isinstance(geom, Polygon):
        exterior = geom.exterior
        new_exterior = remove_third_dimension(exterior)

        interiors = geom.interiors
        new_interiors = []
        for int in interiors:
            new_interiors.append(remove_third_dimension(int))

        return Polygon(new_exterior, new_interiors)

    elif isinstance(geom, LinearRing):
        return LinearRing([xy[0:2] for xy in list(geom.coords)])

    elif isinstance(geom, LineString):
        return LineString([xy[0:2] for xy in list(geom.coords)])

    elif isinstance(geom, Point):
        return Point([xy[0:2] for xy in list(geom.coords)])

    elif isinstance(geom, MultiPoint):
        points = list(geom.geoms)
        new_points = []
        for point in points:
            new_points.append(remove_third_dimension(point))

        return MultiPoint(new_points)

    elif isinstance(geom, MultiLineString):
        lines = list(geom.geoms)
        new_lines = []
        for line in lines:
            new_lines.append(remove_third_dimension(line))

        return MultiLineString(new_lines)

    elif isinstance(geom, MultiPolygon):
        pols = list(geom.geoms)

        new_pols = []
        for pol in pols:
            new_pols.append(remove_third_dimension(pol))

        return MultiPolygon(new_pols)

    elif isinstance(geom, GeometryCollection):
        geoms = list(geom.geoms)

        new_geoms = []
        for geom in geoms:
            new_geoms.append(remove_third_dimension(geom))

        return GeometryCollection(new_geoms)

    else:
        raise RuntimeError(
            "Currently this type of geometry is not supported: {}".format(type(geom))
        )
