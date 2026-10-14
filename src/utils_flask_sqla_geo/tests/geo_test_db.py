"""Flask-SQLAlchemy instance and database constants used by the tests.

``utils_flask_sqla.generic`` resolves its ``db`` object at import time from the
``FLASK_SQLALCHEMY_DB`` environment variable, which conftest.py points at this module.
"""

import os

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

PG_URI = os.environ.get(
    "TEST_PG_DATABASE_URI",
    "postgresql+psycopg2://geonatadmin:geonatadmin@localhost:5432/geonature2db",
)

SCHEMA = "utils_flask_sqla_geo_tests"
TABLE = "t_geo"
