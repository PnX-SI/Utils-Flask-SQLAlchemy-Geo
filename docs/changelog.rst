=========
CHANGELOG
=========

0.3.0 (unreleased)
------------------

**🚀 Nouveautés**

- Compatibilité Shapely 2.0 (#14)
- Mise à jour de Flask version 2 à 3 (#23)
- Amélioration de la compatibilité SQLAlchemy 1.4 (#23)

**🐛 Corrections**

- Correction d'une fonction et d'une variable ayant le même nom ``shape`` (#25)


0.2.8 (2023-05-24)
------------------

**🚀 Nouveautés**

- Ajout de SQLAlchemy 1.4 (en plus de 1.3) à l’intégration continue
- ``GeoAlchemyAutoSchema`` :

  - Sérialisation en JSON (et non GeoJSON) : encodage des géométries en WKT
  - Support de la sérialisation d’un générateur afin d’encoder un grand nombre de données avec une faible emprunte mémoire
- ``GenericQueryGeo`` :

  - ``get_model`` : génération automatique d’un modèle à partir d’une table
  - ``get_schema`` : génération automatique d’un schéma à partir d’un modèle
- Ajout de fonctions d’export en JSON, GeoJSON et GeoPackage performantes avec une faible emprunte mémoire


0.2.7 (2023-03-03)
------------------

**🚀 Nouveautés**

- Ajout du schéma ``GeoAlchemyAutoSchema`` permettant la sérialisation de modèle contenant des colonnes géographiques en GeoJSON
- Ajout de l’utilitaire ``geojsonify`` similaire à ``flask.jsonify`` mais définisant un ``Content-Type`` ``application/geo+json``
- Compatibilité SQLAlchemy 1.4 / Flask-SQLAlchemy 2
- Intégration continue avec ``pytest``

**🐛 Corrections**

- Correction des dépendances : ``shapely<2``


0.2.6 (2022-12-12)
------------------

**🚀 Nouveautés**

* Code formatté avec Black. Une Github Action y veille.
* Possibilité de spécifier l’encodage des fichiers Shape générés (#11)

**🐛 Corrections**

* Correction de la gestion des géométries nulles lors de la génération d’un fichier Shape.


0.2.5 (2022-09-01)
------------------

**🚀 Nouveautés**

* Suppression de la fonction ``circle_from_point``
* Suppression de ``geog`` des dépendances


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
