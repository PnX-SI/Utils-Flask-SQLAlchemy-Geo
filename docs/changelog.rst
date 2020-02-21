=========
CHANGELOG
=========

0.0.2 (2020-02-21)
------------------

**Corrections**

* Indentation de la fonction ``as_geofeature`` qui n'était pas considérée comme une méthode de GenericQueryGeo

0.0.1 (2020-02-06)
------------------

Première version fonctionnelle de la librairie.

* Complète la librairie Utils-Flask-SQLAlchemy
* Décorateur : décorateur de classe permettant sérialiser en GeoJSON et de créer des shapefiles à partir de modèle SQLAlchemy
* GenericQueryGeo : complète les GenericQuery de Utils-Flask-SQLAlchemyGeo en permettant de gérer les géométries
* Méthode ``from_geofeature``
* Le decorateur ``geoserializable`` ajoute les méthodes du décorateur serializable
* Fonctions utilitaires pour manipuler des objets géographiques (``circle_from_point``, ``convert_to_2d``, `remove_third_dimension``... ), et classe utilitaire pour créer des shapfiles (RIP soon ?): ``FionaShapeService``
