import os

# Must be set before utils_flask_sqla.generic (and so utils_flask_sqla_geo.generic) is imported
os.environ.setdefault("FLASK_SQLALCHEMY_DB", "utils_flask_sqla_geo.tests.geo_test_db.db")

import pytest
from flask import Flask
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# ---------------------------------------------------------------------------
# Tests requiring a PostGIS database use the ``app`` fixture.
# The database URI can be overridden with the TEST_PG_DATABASE_URI env var, e.g.:
#   docker run --rm -p 5432:5432 -e POSTGRES_USER=geonatadmin \
#       -e POSTGRES_PASSWORD=geonatadmin -e POSTGRES_DB=geonature2db \
#       postgis/postgis:15-3.4
# Tests are skipped automatically if no server is reachable.
# ---------------------------------------------------------------------------

from utils_flask_sqla_geo.tests.geo_test_db import PG_URI, SCHEMA, TABLE, db as _db


@pytest.fixture(scope="session")
def app():
    engine = create_engine(PG_URI)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL test database not reachable at {PG_URI}: {exc}")
    finally:
        engine.dispose()

    db = _db
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = PG_URI
    db.init_app(app)

    with app.app_context():
        # GenericTable reflects tables with its own connection: data must be committed
        with db.engine.begin() as conn:
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
        db.session.remove()
        with db.engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA {SCHEMA} CASCADE"))
        db.engine.dispose()


@pytest.fixture
def db(app):
    yield _db
    _db.session.rollback()
