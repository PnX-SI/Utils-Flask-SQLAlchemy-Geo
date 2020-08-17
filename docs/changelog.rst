=========
CHANGELOG
=========

0.1.1 (unreleased)
------------------

**🚀 Nouveautés**

* ajout d'un parametre `exclude` dans as_dict pour ne pas demander une propriété ou une relation


**🐛 Corrections**

* 

0.1.0 (2020-06-17)
------------------

**🚀 Nouveautés**

* Ajout de l'export au format GeoPackage en plus du format Shapefile existant, avec la fonction ``as_geofile`` qui remplace ``as_shape`` (conservée pour rétrocompatibilité) (#3)
* Mise à jour de la librairie Fiona (version 1.7.13 à version 1.8.13.post1)
* Forcer les points de géométries simples en multiples pour les exports en SHP (#5)

**🐛 Corrections**

* Gestion des géométries multiples (#4)
* Compléments et révision de la documentation

0.0.2 (2020-02-21)
------------------

**🐛 Corrections**

* Indentation de la fonction ``as_geofeature`` qui n'était pas considérée comme une méthode de ``GenericQueryGeo``

0.0.1 (2020-02-06)
------------------

Première version fonctionnelle de la librairie.

* Complète la librairie Utils-Flask-SQLAlchemy
* Décorateur : décorateur de classe permettant de sérialiser en GeoJSON et de créer des shapefiles à partir de modèles SQLAlchemy
* GenericQueryGeo : complète les GenericQuery de Utils-Flask-SQLAlchemy en permettant de gérer les géométries
* Méthode ``from_geofeature``
* Le décorateur ``geoserializable`` ajoute les méthodes du décorateur serializable
* Fonctions utilitaires pour manipuler des objets géographiques (``circle_from_point``, ``convert_to_2d``, ``remove_third_dimension``... ), et classe utilitaire pour créer des shapfiles (``FionaShapeService``)
