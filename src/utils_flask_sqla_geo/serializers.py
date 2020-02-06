import datetime

from geoalchemy2.shape import to_shape, from_shape
from geojson import Feature, FeatureCollection
from utils_flask_sqla.serializers import serializable
from shapely.geometry import asShape

from utils_flask_sqla.serializers import serializable
from utils_flask_sqla.errors import UtilsSqlaError

from .utilsgeometry import FionaShapeService, remove_third_dimension


def geoserializable(cls):
    """
        Décorateur de classe
        Permet de rajouter la fonction as_geofeature à une classe
    """

    # par defaut un geoserializable est aussi un serializable
    # pas besoin de deux decorateurs

    cls = serializable(cls)

    def serializegeofn(
        self, geoCol, idCol, recursif=False, columns=(), relationships=(), depth=None
    ):
        """
        Méthode qui renvoie les données de l'objet sous la forme
        d'une Feature geojson

        Parameters
        ----------
           geoCol: string
            Nom de la colonne géométrie
           idCol: string
            Nom de la colonne primary key
           recursif: boolean
            Spécifie si on veut que les sous objet (relationship) soit
            également sérialisé
           columns: liste
            liste des columns qui doivent être prisent en compte
        """

        if not getattr(self, geoCol) is None:
            geometry = to_shape(getattr(self, geoCol))
        else:
            geometry = {"type": "Point", "coordinates": [0, 0]}

        feature = Feature(
            id=str(getattr(self, idCol)),
            geometry=geometry,
            properties=self.as_dict(
                recursif, depth=depth, columns=columns, relationships=relationships),
        )
        return feature

    def populategeofn(self, geojson, col_geom_name="geom"):
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
        self.from_dict(properties)

        # voir si meilleure procédure pour mettre la geometrie en base
        shape = asShape(geometry)
        two_dimension_geom = remove_third_dimension(shape)
        geom = from_shape(two_dimension_geom, srid=4326)
        setattr(self, col_geom_name, geom)

    cls.as_geofeature = serializegeofn
    cls.from_geofeature = populategeofn

    return cls


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
        columns=None,
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

        file_name = file_name or datetime.datetime.now().strftime("%Y_%m_%d_%Hh%Mm%S")

        if columns:
            db_cols = [
                db_col for db_col in db_col in cls.__mapper__.c if db_col.key in columns
            ]
        else:
            db_cols = cls.__mapper__.c

        FionaShapeService.create_shapes_struct(
            db_cols=db_cols, dir_path=dir_path, file_name=file_name, srid=srid
        )
        for d in data:
            d = d.as_dict(columns)
            geom = getattr(d, geom_col)
            FionaShapeService.create_feature(d, geom)

        FionaShapeService.save_and_zip_shapefiles()

    cls.as_shape = to_shape_fn
    return cls
