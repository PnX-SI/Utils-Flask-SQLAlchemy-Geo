import os

# Must be set before utils_flask_sqla.generic (and so utils_flask_sqla_geo.generic) is imported
os.environ.setdefault("FLASK_SQLALCHEMY_DB", "utils_flask_sqla_geo.tests.geo_test_db.db")

import pytest
from flask import Flask
from sqlalchemy import text

# ---------------------------------------------------------------------------
# Tests require a PostGIS database. Its URI can be overridden with the
# TEST_PG_DATABASE_URI env var, e.g.:
#   docker run --rm -p 5432:5432 -e POSTGRES_USER=geonatadmin \
#       -e POSTGRES_PASSWORD=geonatadmin -e POSTGRES_DB=geonature2db \
#       postgis/postgis:15-3.4
#
# Changes made through db.session are rolled back after each test by the
# temporary transaction fixtures of the utils_flask_sqla pytest plugin
# (see utils_flask_sqla/tests/fixtures.py), which rely on the _session fixture.
# ---------------------------------------------------------------------------

from utils_flask_sqla_geo.tests.geo_test_db import PG_URI, SCHEMA, TABLE, db as _db


@pytest.fixture(scope="session")
def _app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = PG_URI
    _db.init_app(app)

    with app.app_context():
        # GenericTable reflects tables with its own connection: the test schema is
        # committed (outside of the rolled back transactions) and dropped at the end
        with _db.engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            conn.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
            conn.execute(text(f"CREATE SCHEMA {SCHEMA}"))
            conn.execute(text(f"""
                CREATE TABLE {SCHEMA}.{TABLE} (
                    id integer PRIMARY KEY,
                    name text,
                    value integer,
                    geom geometry(Geometry, 4326)
                )
                """))
            conn.execute(text(f"""
                INSERT INTO {SCHEMA}.{TABLE} (id, name, value, geom) VALUES
                (1, 'point', 10, ST_GeomFromText('POINT(6 10)', 4326)),
                (2, 'line', 20, ST_GeomFromText('LINESTRING(0 0, 1 1)', 4326)),
                (3, 'polygon', 30, ST_GeomFromText('POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))', 4326)),
                (4, 'no geom', 40, NULL)
                """))
            # table without primary key, to test GenericQueryGeo.get_model fallback
            conn.execute(text(f"CREATE TABLE {SCHEMA}.t_nopk (code text, label text)"))
        yield app
        _db.session.remove()
        with _db.engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA {SCHEMA} CASCADE"))
        _db.engine.dispose()


@pytest.fixture(scope="session")
def _session(_app):
    return _db.session


@pytest.fixture(scope="session", autouse=True)
def app(_app, _session):
    return _app


@pytest.fixture
def db(app):
    return _db
