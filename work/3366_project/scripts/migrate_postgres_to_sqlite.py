"""One-off export: copy the PostgreSQL database back into data/labellens.db (SQLite).

Run this after making changes directly in PostgreSQL (via the app's API or a DB client)
that you want to persist into git, since only the SQLite file is tracked in version control.

Usage:
    python -m scripts.migrate_postgres_to_sqlite [--sqlite-path data/labellens.db]

After running, review the diff and commit/push data/labellens.db as usual:
    git add data/labellens.db
    git commit -m "..."
    git push

Reads DATABASE_URL from the environment/.env (same as the app) for the Postgres source.
Overwrites the SQLite file's tables with the current Postgres content.
"""

import argparse

from sqlalchemy import create_engine

from app.config import settings
from scripts._db_sync import sync


def export(sqlite_path: str) -> None:
    pg_engine = create_engine(settings.database_url)
    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
    sync(pg_engine, sqlite_engine)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite-path", default="data/labellens.db")
    args = parser.parse_args()
    export(args.sqlite_path)
