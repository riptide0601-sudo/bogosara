"""Shared table-copy logic used by migrate_sqlite_to_postgres.py and migrate_postgres_to_sqlite.py."""

from sqlalchemy import select
from sqlalchemy.engine import Engine

from app.database import Base
from app.models import (  # noqa: F401  (import registers tables on Base.metadata)
    Ingredient,
    IngredientPurpose,
    IngredientRelation,
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
    IngredientRelation.__table__,
]


def sync(src_engine: Engine, dst_engine: Engine) -> None:
    Base.metadata.create_all(dst_engine)

    with src_engine.connect() as src, dst_engine.begin() as dst:
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

    if dst_engine.dialect.name == "sqlite":
        # Delete+reinsert leaves stale pages behind; reclaim the space so the
        # git-tracked file doesn't balloon on every export.
        with dst_engine.connect() as conn:
            conn.exec_driver_sql("VACUUM")
        return

    if dst_engine.dialect.name != "postgresql":
        return

    # Keep Postgres's SERIAL/IDENTITY sequences in sync with the copied ids.
    with dst_engine.begin() as conn:
        for table in TABLE_ORDER:
            pk_cols = [c for c in table.primary_key.columns if c.autoincrement is not False]
            for col in pk_cols:
                if col.type.python_type is int:
                    conn.exec_driver_sql(
                        f"SELECT setval(pg_get_serial_sequence('{table.name}', '{col.name}'), "
                        f"COALESCE((SELECT MAX({col.name}) FROM {table.name}), 1), "
                        f"(SELECT MAX({col.name}) IS NOT NULL FROM {table.name}))"
                    )
