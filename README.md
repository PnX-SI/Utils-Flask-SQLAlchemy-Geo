## Librairie "outil" pour SQLAlchemy et Flask

La librairie fournit des outils pour faciliter le développement avec Flask et SQLAlchemy.
Elle vient compléter la libraire [Utils-Flask-SQLAlchemy](https://github.com/PnX-SI/Utils-Flask-SQLAlchemy)

- **Les serialisers**

  Le décorateur de classe `@geoserializable` permet la sérialisation JSON d'objets Python issus des classes SQLAlchemy. Il rajoute dynamiquement une méthode `as_geofeature()` aux classes qu'il décore. Cette méthode transforme l'objet de la classe en dictionnaire en transformant les types Python non compatibles avec le format JSON. Pour cela, elle se base sur les types des colonnes décrits dans le modèle SQLAlchemy. Cette methode permet d'obtenir un objet de type geofeature

- **Les GenericTableGeo et les GenericQueryGeo**

    Ces classed héritent des classe GenericTable et GenericQuery et permettent de gérer le données de type géométrie.