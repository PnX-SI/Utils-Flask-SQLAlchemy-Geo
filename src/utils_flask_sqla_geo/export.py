import csv
import json
from typing import Type

import fiona
from fiona.crs import from_epsg

from utils_flask_sqla_geo.schema import GeoAlchemyAutoSchema
from utils_flask_sqla_geo.utilsgeometry import FIONA_MAPPING


def export_csv(
    query,
    schema_class: Type[GeoAlchemyAutoSchema],
    fp,
    columns: list = [],
    chunk_size: int = 1000,
    separator=";",
    geometry_field_name=None,
):
    """Exporte une generic query au format csv

    la geométrie n'est pas présente par défaut
    elle peut être dans les données exportées si geometry_field_name est précisé

    Args:
        query (QueryClass): requete select
        schema_class: marshmallow_schema
        fp (file pointer): pointer vers un fichier (un stream, etc..)
        columns (list, optioname): liste des colonnes à exporter. Defaults to [] (toutes les colonnes de la vue).
        chunk_size (int, optional): taille pour le traitement par lots. Defaults to 1000.
        separator (str, optional): sparateur pour le csv. Defaults to ";".
        geometry_field_name (_type_, optional): nom du champ pour la colonne geométrique. Defaults to None.
    """
    # gestion de only
    only = columns

    # ajout du champs geométrique si demandé (sera exporté en WKT)
    if geometry_field_name:
        only.append(f"+{geometry_field_name}")

    # instantiation du schema avec only
    schema = schema_class(only=only or None)

    csv_columns = list(schema.dump_fields.keys())

    # écriture du fichier cscv
    writer = csv.DictWriter(
        fp, csv_columns, delimiter=separator, quoting=csv.QUOTE_ALL, extrasaction="ignore"
    )

    writer.writeheader()  # ligne d'entête

    # écriture des lignes dans le fichier csv
    for line in schema.dump(query.yield_per(chunk_size), many=True):
        writer.writerow(line)


def export_geojson(
    query,
    schema_class: Type[GeoAlchemyAutoSchema],
    fp,
    columns: list = [],
    chunk_size: int = 1000,
    geometry_field_name=None,
):
    """Exporte une generic query au format geojson

    le champs geomtrique peut être précisé
    ou choisi par défaut si la vue ne comporte qu'un seul champs geométrique

    Args:
        query (QueryClass): requete select
        schema_class: marshmallow_schema
        fp (file pointer): pointer vers un fichier (un stream, etc..)
        columns (list, optioname): liste des colonnes à exporter. Defaults to [] (toutes les colonnes de la vue).
        chunk_size (int, optional): taille pour le traitement par lots. Defaults to 1000.
        geometry_field_name (_type_, optional): nom du champ pour la colonne geométrique. Defaults to None.
    """

    # instantiation du schema
    schema = schema_class(
        only=columns or None, as_geojson=True, feature_geometry=geometry_field_name
    )

    # serialisation
    feature_collection = schema.dump(query.yield_per(chunk_size), many=True)

    # écriture du ficher geojson
    for chunk in json.JSONEncoder().iterencode(feature_collection):
        fp.write(chunk)


def export_json(
    query,
    schema_class: Type[GeoAlchemyAutoSchema],
    fp,
    columns: list = [],
    chunk_size: int = 1000,
    geometry_field_name=None,
):
    """Exporte une generic query au format json

    la geométrie n'est pas présente par défaut
    elle peut être dans les données exportées si geometry_field_name est précisé

    Args:
        query (QueryClass): requete select
        schema_class: marshmallow_schema
        fp (_type_): pointer vers un fichier (un stream, etc..)
        columns (list, optioname): liste des colonnes à exporter. Defaults to [] (toutes les colonnes de la vue).
        chunk_size (int, optional): taille pour le traitement par lots. Defaults to 1000.
        separator (str, optional): sparateur pour le csv. Defaults to ";".
        geometry_field_name (_type_, optional): nom du champ pour la colonne geométrique. Defaults to None.
    """

    # gestion de only
    only = columns

    # ajout du champs geométrique si demandé (sera exporté en WKT)
    if geometry_field_name:
        only.append(f"+{geometry_field_name}")
    # instantiation du schema avec only
    schema = schema_class(only=only or None)

    # serialisation
    iterable_data = schema.dump(query.yield_per(chunk_size), many=True)

    # écriture du fichier json
    for chunk in json.JSONEncoder().iterencode(iterable_data):
        fp.write(chunk)


def export_geopackage(
    query,
    schema_class: Type[GeoAlchemyAutoSchema],
    filename: str,
    srid: int,
    geometry_field_name=None,
    columns: list = [],
    chunk_size: int = 1000,
):
    schema = schema_class(
        only=columns or None, as_geojson=True, feature_geometry=geometry_field_name
    )

    feature_collection = schema.dump(query.yield_per(chunk_size), many=True)

    # FIXME: filter tableDef columns with columns
    properties = {
        db_col.key: FIONA_MAPPING.get(db_col.type.__class__.__name__.lower(), "str")
        for db_col in schema_class.Meta.model.__table__.columns
        if not db_col.type.__class__.__name__ == "Geometry"
        and (not columns or db_col.key in columns)
    }
    gpkg_schema = {"geometry": "Unknown", "properties": properties}

    with fiona.open(filename, "w", "GPKG", schema=gpkg_schema, crs=from_epsg(srid)) as f:
        for feature in feature_collection["features"]:
            f.write(feature)
