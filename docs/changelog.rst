0.0.1 (2020-02-06)
------------------

Première version de la librairie

* Complète la librairie Utils-Flask-SQLAlchemy
* Décorateur : décorateur de classe permettant sérialiser en geojson et de créer des shapefiles à partir de modèle SQLAlchemy
* GenericQueryGeo : complète les GenericQuery de Utils-Flask-SQLAlchemyGeo en permettant de gérer les géométries
* Méthode from_geofeature
* Le decorateur geoserializable ajoute les methodes du decorateur serializable
* Fonction utilitaires pour manipuler des objets géographique (`circle_from_point`, `convert_to_2d`, `remove_third_dimension`... ), et classe utilitaire pour créer des shapfiles (RIP soon ?): `FionaShapeService`

