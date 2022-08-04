=========
CHANGELOG
=========

0.2.4 (2022-08-04)
------------------

**🐛 Corrections**

* Compatibilité Python 3.7 : ``numpy<1.22``

0.2.3 (2022-08-03)
------------------

**🐛 Corrections**

* Correction des dépendances : ``SQLAlchemy<1.4``, ``geoalchemy2<0.12``


0.2.2 (2022-01-03)
------------------

**🚀 Nouveautés**

* Ajout de ``GeoFeatureCollectionMixin`` définissant la fonction ``as_geofeaturecollection``

0.2.1 (2021-07-22)
------------------

**🐛 Corrections**

* Ajout du paramètre ``fields`` sur la fonction "générique" ``as_geofeature``

0.2.0 (2021-05-27)
------------------

**🚀 Nouveautés**

* Mise à jour en lien avec la version 0.2.0 de ``utils-flask-sqlalchemy`` (support des arguments ``fields`` et ``exclude``)
* Les champs géométriques sont détectés par le décorateur ``@geoserializable`` et sont passés en paramètre ``exclude`` au décorateur ``@serializable``

0.1.3 (2021-01-27)
------------------

**🚀 Nouveautés**

* Ajout du support de la sérialisation pour les types ``json`` et ``jsonb``

**🐛 Corrections**

* Les dépendances du fichier ``requirements.txt`` ne sont plus fixées à une version

0.1.2 (2020-10-21)
------------------

**🐛 Corrections**

* Mise à jour de la version de `utils-flask-sqlalchemy`

0.1.1 (2020-10-17)
------------------

**🚀 Nouveautés**

* Fonction pour générer du geojson à partir de PostgreSQL (#7)

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
