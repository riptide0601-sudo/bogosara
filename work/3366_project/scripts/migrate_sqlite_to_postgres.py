"""One-off migration: copy data/labellens.db (SQLite) into the PostgreSQL database.

Usage (after `docker compose up -d db`, or against any reachable Postgres):
    python -m scripts.migrate_sqlite_to_postgres [--sqlite-path data/labellens.db]

Reads DATABASE_URL from the environment/.env (same as the app) for the Postgres target.
Overwrites the Postgres tables with the SQLite content (SQLite is treated as the source of truth).
"""

import argparse

from sqlalchemy import create_engine

from app.config import settings
from scripts._db_sync import sync


def migrate(sqlite_path: str) -> None:
    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
    pg_engine = create_engine(settings.database_url)
    sync(sqlite_engine, pg_engine)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite-path", default="data/labellens.db")
    args = parser.parse_args()
    migrate(args.sqlite_path)
