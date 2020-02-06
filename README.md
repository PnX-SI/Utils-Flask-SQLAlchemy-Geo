## Librairie "outil géographique" pour SQLAlchemy et Flask

Cette librairie fournit des outils pour faciliter le développement avec Flask et SQLAlchemy.
Elle vient compléter la libraire [Utils-Flask-SQLAlchemy](https://github.com/PnX-SI/Utils-Flask-SQLAlchemy) en y ajoutant des fonctionnalités liées aux objets géographiques.

- **Les serialisers**

  Le décorateur de classe `@geoserializable` permet la sérialisation JSON d'objets Python issus des classes SQLAlchemy. Il rajoute dynamiquement une méthode `as_geofeature()` aux classes qu'il décore. Cette méthode transforme l'objet de la classe en dictionnaire en transformant les types Python non compatibles avec le format JSON. Pour cela, elle se base sur les types des colonnes décrits dans le modèle SQLAlchemy. Cette methode permet d'obtenir un objet de type `geofeature`.

  **Utilisation**


    - ``utils_flask_sqla_geo.serializers.geoserializable``


    Décorateur pour les modèles SQLA : Ajoute une méthode as_geofeature qui
    retourne un dictionnaire serialisable sous forme de Feature geojson.


    Fichier définition modèle :

        from geonature.utils.env import DB
        from utils_flask_sqla_geo.serializers import geoserializable

        @geoserializable
        class MyModel(DB.Model):
            __tablename__ = 'bla'
            ...


    fichier utilisation modele :

        instance = DB.session.query(MyModel).get(1)
        result = instance.as_geofeature()

Le décorateur de classe `@shapeserializable` permet la création de shapefiles issus des classes SQLAlchemy:

- Ajoute une méthode `as_list` qui retourne l'objet sous forme de tableau
  (utilisé pour créer des shapefiles)
- Ajoute une méthode de classe `to_shape` qui crée des shapefiles à partir
  des données passées en paramètre

**Utilisation**

- `utils_flask_sqla_geo.serializers.shapeserializable`

Fichier définition modèle :

      from geonature.utils.env import DB

      from utils_flask_sqla_geo.serializers import shapeserializable


      @shapeserializable
      class MyModel(DB.Model):
          __tablename__ = 'bla'
          ...

Fichier utilisation modele :

    data = DB.session.query(MyShapeserializableClass).all()
    MyShapeserializableClass.as_shape(
        geom_col='geom_4326',
        srid=4326,
        data=data,
        dir_path=str(ROOT_DIR / 'backend/static/shapefiles'),
        file_name=file_name
    )

- **La classe FionaShapeService pour générer des shapesfiles**

  - `utils_flask_sqla_geo.serializers.FionaShapeService`

  Classe utilitaire pour crer des shapefiles.

  La classe contient 3 méthode de classe:

  - FionaShapeService.create_shapes_struct(): crée la structure de 3 shapefiles
    (point, ligne, polygone) à partir des colonens et de la geom passé en
    paramètre
  - FionaShapeService.create_feature(): ajoute un enregistrement aux shapefiles
  - FionaShapeService.save_and_zip_shapefiles(): sauvegarde et zip les shapefiles
    qui ont au moin un enregistrement


          data = DB.session.query(MySQLAModel).all()

          for d in data:
                  FionaShapeService.create_shapes_struct(
                          db_cols=db_cols,
                          srid=current_app.config['LOCAL_SRID'],
                          dir_path=dir_path,
                          file_name=file_name,
                          col_mapping=current_app.config['SYNTHESE']['EXPORT_COLUMNS']
                  )
          FionaShapeService.create_feature(row_as_dict, geom)
                  FionaShapeService.save_and_zip_shapefiles()

- **Les GenericTableGeo et les GenericQueryGeo**

  Ces classes héritent des classes `GenericTable` et `GenericQuery` et permettent de gérer le données de type géométrie.
