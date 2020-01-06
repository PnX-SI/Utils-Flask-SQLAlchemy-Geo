0.0.1 (2019-10-17)
------------------

Première version de la librairie

* Complète la librairie Utils-Flask-SQLAlchemy
* Serializer : geoserialization
* Décorateur : décorateur de classe permettant de geoserialiser des modèles SQLAlchemy en geofeature via la méthode `as_geofeature`
* GenericQueryGeo : complète les GenericQuery de Utils-Flask-SQLAlchemyGeo en permettant de gérer les géométries
* Méthode from_geofeature
* Le decorateur geoserializable ajoute les methodes du decorateur serializable
