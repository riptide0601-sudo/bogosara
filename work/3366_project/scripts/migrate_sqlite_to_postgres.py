"""One-off migration: copy data/labellens.db (SQLite) into the PostgreSQL database.

Usage (after `docker compose up -d db`, or against any reachable Postgres):
    python -m scripts.migrate_sqlite_to_postgres [--sqlite-path data/labellens.db]

Reads DATABASE_URL from the environment/.env (same as the app) for the Postgres target.
"""

import argparse

from sqlalchemy import create_engine, select

from app.config import settings
from app.database import Base
from app.models import (  # noqa: F401  (import registers tables on Base.metadata)
    Ingredient,
    IngredientPurpose,
    LLMSummary,
    Product,
    ProductIngredient,
    Purpose,
)

# Parent tables before the join/child tables that reference them.
TABLE_ORDER = [
    Purpose.__table__,
    Ingredient.__table__,
    Product.__table__,
    IngredientPurpose.__table__,
    ProductIngredient.__table__,
    LLMSummary.__table__,
]


def migrate(sqlite_path: str) -> None:
    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
    pg_engine = create_engine(settings.database_url)

    Base.metadata.create_all(pg_engine)

    with sqlite_engine.connect() as src, pg_engine.begin() as dst:
        # Delete child tables before parents to satisfy foreign keys.
        for table in reversed(TABLE_ORDER):
            dst.execute(table.delete())

        for table in TABLE_ORDER:
            rows = [dict(row._mapping) for row in src.execute(select(table))]
            if not rows:
                print(f"{table.name}: 0 rows, skipped")
                continue
            dst.execute(table.insert(), rows)
            print(f"{table.name}: {len(rows)} rows migrated")

    if pg_engine.dialect.name != "postgresql":
        return

    # Keep Postgres's SERIAL/IDENTITY sequences in sync with the copied ids.
    with pg_engine.begin() as conn:
        for table in TABLE_ORDER:
            pk_cols = [c for c in table.primary_key.columns if c.autoincrement is not False]
            for col in pk_cols:
                if col.type.python_type is int:
                    conn.exec_driver_sql(
                        f"SELECT setval(pg_get_serial_sequence('{table.name}', '{col.name}'), "
                        f"COALESCE((SELECT MAX({col.name}) FROM {table.name}), 1), "
                        f"(SELECT MAX({col.name}) IS NOT NULL FROM {table.name}))"
                    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite-path", default="data/labellens.db")
    args = parser.parse_args()
    migrate(args.sqlite_path)
