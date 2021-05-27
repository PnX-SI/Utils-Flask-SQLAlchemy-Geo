import datetime
from itertools import chain 
from warnings import warn

from shapely import wkb
from shapely.geometry import asShape

from geojson import Feature, FeatureCollection

from sqlalchemy.sql import text
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape, from_shape

from utils_flask_sqla.serializers import serializable
from utils_flask_sqla.errors import UtilsSqlaError

from .utilsgeometry import (
    FionaShapeService, 
    remove_third_dimension, 
    FionaGpkgService
)


def get_geoserializable_decorator(geoCol=None, idCol=None, **kwargs):
    """
        Décorateur de classe
        Permet de rajouter la fonction as_geofeature à une classe
    """
    defaultGeoCol = geoCol
    defaultIdCol = idCol

    def _geoserializable(cls):

        # par defaut un geoserializable est aussi un serializable
        # pas besoin de deux decorateurs

        mapper = inspect(cls)

        exclude = kwargs.get('exclude', [])
        geom_exclude = [ key
                         for key, col in mapper.columns.items()
                         if isinstance(col.type,  Geometry) ]
        kwargs['exclude'] = list(chain(geom_exclude, exclude))
        cls = serializable(**kwargs)(cls)

        def serializegeofn(self, geoCol=None, idCol=None, *args, **kwargs):
            """
            Méthode qui renvoie les données de l'objet sous la forme
            d'une Feature geojson

            Parameters
            ----------
               geoCol: string
                Nom de la colonne géométrie
               idCol: string
                Nom de la colonne primary key

            Pour les autres paramètres, voir la doc de @serializable
            """
            if geoCol is None:
                geoCol = defaultGeoCol
            if idCol is None:
                idCol = defaultIdCol

            if not getattr(self, geoCol) is None:
                geometry = to_shape(getattr(self, geoCol))
            else:
                geometry = {"type": "Point", "coordinates": [0, 0]}

            feature = Feature(
                id=str(getattr(self, idCol)),
                geometry=geometry,
                properties=self.as_dict(*args, **kwargs),
            )
            return feature

        def populategeofn(self, geojson, recursif=True, col_geom_name="geom"):
            '''
            Méthode qui initie les valeurs de l'objet SQLAlchemy à partir d'un geojson

            Parameters
            ----------
                geojfeature_in : dictionnaire contenant les valeurs à passer à l'objet
            '''

            typeg = geojson.get('type')
            properties = geojson.get('properties')
            geometry = geojson.get('geometry')

            if not properties or not geometry or typeg != "Feature":
                raise UtilsSqlaError(
                    "Input must be a geofeature"
                )

            # set properties
            self.from_dict(properties, recursif=recursif)

            # voir si meilleure procédure pour mettre la geometrie en base
            shape = asShape(geometry)
            two_dimension_geom = remove_third_dimension(shape)
            geom = from_shape(two_dimension_geom, srid=4326)
            setattr(self, col_geom_name, geom)

        cls.as_geofeature = serializegeofn
        cls.from_geofeature = populategeofn

        return cls

    return _geoserializable


def geoserializable(*args, **kwargs):
    if not kwargs and len(args) == 1 and isinstance(args[0], type):  # e.g. @geoserializable
        return get_geoserializable_decorator()(args[0])
    else:
        return get_geoserializable_decorator(*args, **kwargs)  # e.g. @geoserializable(idCol='geom')


def shapeserializable(cls):
    @classmethod
    def to_shape_fn(
        cls,
        geom_col=None,
        geojson_col=None,
        srid=None,
        data=None,
        dir_path=None,
        file_name=None,
        columns=[],
        fields=[]
    ):
        """
        Class method to create 3 shapes from datas
        Parameters

        geom_col (string): name of the geometry column 
        geojson_col (str): name of the geojson column if present. If None create the geojson from geom_col with shapely
                            for performance reason its better to use geojson_col rather than geom_col
        data (list): list of datas 
        file_name (string): 
        columns (list): columns to be serialize

        Returns:
            void
        """
        if not data:
            data = []
        if columns:
            warn("'columns' argument is deprecated. Please add columns to serialize "
                    "directly in 'fields' argument.", DeprecationWarning)
            fields = chain(fields, columns)
        file_name = file_name or datetime.datetime.now().strftime("%Y_%m_%d_%Hh%Mm%S")

        fields = list(fields)

        if fields:
            db_cols = [
                db_col for db_col in fields in cls.__mapper__.c if db_col.key in fields
            ]
        else:
            db_cols = cls.__mapper__.c

        FionaShapeService.create_shapes_struct(
            db_cols=db_cols, dir_path=dir_path, file_name=file_name, srid=srid
        )
        for d in data:
            d = d.as_dict(fields)
            geom = getattr(d, geom_col)
            FionaShapeService.create_feature(d, geom)

        FionaShapeService.save_and_zip_shapefiles()

    cls.as_shape = to_shape_fn
    return cls


def geofileserializable(cls):
    @classmethod
    def to_geofile_fn(
        cls,
        export_format="shp",
        geom_col=None,
        geojson_col=None,
        srid=None,
        data=None,
        dir_path=None,
        file_name=None,
        columns=[],
        fields=[]
    ):
        """
        Class method to create 3 shapes from datas
        Parameters

        geom_col (string): name of the geometry column 
        geojson_col (str): name of the geojson column if present. If None create the geojson from geom_col with shapely
                            for performance reason its better to use geojson_col rather than geom_col
        data (list): list of datas 
        file_name (string): 
        columns (list): columns to be serialize

        Returns:
            void
        """
        if export_format not in ("shp", "gpkg"):
            raise Exception("Unsupported format")

        if not data:
            data = []

        file_name = file_name or datetime.datetime.now().strftime("%Y_%m_%d_%Hh%Mm%S")
        
        if columns:
            warn("'columns' argument is deprecated. Please add columns to serialize "
                    "directly in 'fields' argument.", DeprecationWarning)
            fields = chain(columns, fields)

        fields = list(fields)

        if fields:
            db_cols = [
                db_col for db_col in fields in cls.__mapper__.c if db_col.key in fields
            ]
        else:
            db_cols = cls.__mapper__.c

        if export_format == 'shp':
            fionaService = FionaShapeService
        else:
            fionaService = FionaGpkgService

        fionaService.create_fiona_struct(
            db_cols=db_cols, dir_path=dir_path, file_name=file_name, srid=srid
        )
        for d in data:
            d = d.as_dict(fields)
            geom = getattr(d, geom_col)
            fionaService.create_feature(d, geom)

        fionaService.save_files()

    cls.as_geofile = to_geofile_fn
    return cls


def sqla_query_to_text(query):
    """
        Transformation d'une requete de type Select en sqlalchemy
            en text

        Parameters
            query : requete au format Select sqlalchemy
        Returns:
            text : requete au format text
    """
    # Cas particulier intersection geographique => WKB
    # Par défaut la valeur de l'intersection est égale à NULL
    # https://github.com/geoalchemy/geoalchemy2/issues/151
    params = {}
    for k, v in query.compile().params.items():
        if "ST_GeomFromWKB" in k and isinstance(v, memoryview):
            params[k] = "'" + str(wkb.loads(bytes(v)).wkt) + "'"
        else:
            params[k] = v

    strquery = (str(query.compile(dialect=postgresql.dialect())) % params)
    strquery = strquery.replace("ST_GeomFromWKB", "ST_GeomFromText")
    return strquery


def txt_query_as_geojson(
    session,
    query,
    id_col,
    geom_col,
    geom_srid=4326,
    is_geojson=False,
    keep_id_col=False
):
    """
        Fonction qui permet de convertir une requete sql en geojson
            En utilisant les fonctionnalités de serialisation de postresql

        Parameters

        session : Session sqlalchemy
        query : requete au format text
        id_col : nom de la colonne identifiant (id du geojson)
        geom_col (string): nom de la colonne géométrique
        geom_srid (int): srid de la géométrie
        is_geojson (boolean): Est-ce que la colonne géometrie est déjà un geojson
        keep_id_col (boolean): Est-ce que les valeurs de la colonne id_col doit être concervée dans les properties

        Returns:
            FeatureCollection
        """

    #  TODO add tests !!!!!

    if is_geojson:
        q_geom = geom_col
    else:
        if geom_srid == 4326:
            q_geom = "ST_AsGeoJSON({})".format(geom_col)
        else:
            q_geom = "ST_AsGeoJSON(st_transform({}, 4326))".format(geom_col)
    q_asgeojson = "{}::jsonb".format(q_geom)

    q_rm_col = ["'" + geom_col + "'"]
    if not keep_id_col:
        q_rm_col.append("'" + id_col + "'")

    statement = text("""
        SELECT jsonb_build_object(
            'type',     'FeatureCollection',
            'features', jsonb_agg(feature)
        ) as data
        FROM (
        SELECT jsonb_build_object(
            'type',       'Feature',
            'id',         {id_col},
            'geometry',   {q_asgeojson},
            'properties', to_jsonb(row) - {q_rm_col}
        ) AS feature
        FROM (
            {query}
        ) row) features;
    """.format(
        id_col=id_col,
        q_asgeojson=q_asgeojson,
        q_rm_col=" - ".join(q_rm_col),
        query=query
    ))

    results = session.execute(statement)
    for r in results:
        return r[0]


def sqla_query_to_geojson(
    session,
    query,
    id_col,
    geom_col,
    geom_srid=4326,
    is_geojson=False,
    keep_id_col=False
):
    """
        Fonction qui permet de convertir une requete sql en geojson
            En utilisant les fonctionnalités de serialisation de postresql

        Parameters

        session : Session sqlalchemy
        query : requete au format Select
        id_col : nom de la colonne identifiant (id du geojson)
        geom_col (string): nom de la colonne géométrique
        geom_srid (int): srid de la géométrie
        is_geojson (boolean): Est-ce que la colonne géometrie est déjà un geojson
        keep_id_col (boolean): Est-ce que les valeurs de la colonne id_col doit être concervée dans les properties

        Returns:
            FeatureCollection
    """

    txt_query = sqla_query_to_text(query)
    return txt_query_as_geojson(
        session,
        txt_query,
        id_col,
        geom_col,
        geom_srid=geom_srid,
        is_geojson=is_geojson,
        keep_id_col=keep_id_col
    )
