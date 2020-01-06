from geoalchemy2.shape import to_shape, from_shape
from geojson import Feature, FeatureCollection
from utils_flask_sqla.serializers import serializable
from utils_flask_sqla.errors import GeonatureApiError
from shapely.geometry import asShape

from utils_flask_sqla.serializers import serializable
from utils_flask_sqla.errors import UtilsSqlaError

from geonature.utils.utilsgeometry import remove_third_dimension

def geoserializable(cls):
    """
        Décorateur de classe
        Permet de rajouter la fonction as_geofeature à une classe
    """

    # par defaut un geoserializable est aussi un serializable
    # pas besoin de deux decorateurs

    cls = serializable(cls)

    def serializegeofn(
        self, geoCol, idCol, recursif=False, columns=(), relationships=()
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
            properties=self.as_dict(recursif, columns, relationships),
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
            raise GeonatureApiError(
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
