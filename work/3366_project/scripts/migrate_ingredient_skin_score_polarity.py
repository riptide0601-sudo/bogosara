"""One-off migration: ingredient_skin_score에 is_risk(위험/궁합 구분) 컬럼을 추가하고,
더 이상 쓰이지 않는 score/evidence_level 컬럼을 제거한다 (app/models/ingredient_skin_score.py
2026-08-24 개편 참고 — 궁합성분(추천 성분) 데이터를 같은 테이블에 넣기 위한 선행 작업).

기존 행은 전부 "위험 성분"이었으므로 is_risk=True로 채운다.

Usage:
    python -m scripts.migrate_ingredient_skin_score_polarity [--db-url URL]

Safe to re-run — 이미 마이그레이션된 상태면 아무 것도 하지 않는다.
"""

import argparse

from sqlalchemy import create_engine, inspect

from app.config import settings

# SQLite의 "ALTER TABLE ... DROP COLUMN"은 테이블 레벨 복합 PRIMARY KEY 제약(ingredient_id,
# skin_type)을 내부적으로 다시 만들어주지 않고 그냥 날려버린다(실제로 겪은 버그 — DROP COLUMN 후
# sqlite_master에 PRIMARY KEY 절이 사라짐). 그래서 SQLite에서는 단순 DROP COLUMN 대신 테이블을
# 통째로 다시 만들어 데이터를 옮긴다. Postgres는 이 문제가 없어 DROP COLUMN을 그대로 쓴다.
_SQLITE_REBUILD_DDL = """
CREATE TABLE ingredient_skin_score_new (
    ingredient_id INTEGER NOT NULL,
    skin_type VARCHAR NOT NULL,
    is_risk BOOLEAN NOT NULL DEFAULT 1,
    function VARCHAR,
    source VARCHAR,
    caution TEXT,
    PRIMARY KEY (ingredient_id, skin_type),
    FOREIGN KEY(ingredient_id) REFERENCES ingredient (ingredient_id)
)
"""


def migrate(db_url: str) -> None:
    engine = create_engine(db_url)
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("ingredient_skin_score")}

    with engine.begin() as conn:
        if "is_risk" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE ingredient_skin_score ADD COLUMN is_risk BOOLEAN DEFAULT 1"
            )
            conn.exec_driver_sql(
                "UPDATE ingredient_skin_score SET is_risk = 1 WHERE is_risk IS NULL"
            )
            print("added is_risk column (backfilled existing rows as True)")
        else:
            print("is_risk column already present, skipping add")

        needs_column_drop = "score" in columns or "evidence_level" in columns
        if not needs_column_drop:
            return

        if engine.dialect.name == "postgresql":
            if "score" in columns:
                conn.exec_driver_sql("ALTER TABLE ingredient_skin_score DROP COLUMN score")
                print("dropped score column")
            if "evidence_level" in columns:
                conn.exec_driver_sql("ALTER TABLE ingredient_skin_score DROP COLUMN evidence_level")
                print("dropped evidence_level column")
        else:
            conn.exec_driver_sql(_SQLITE_REBUILD_DDL)
            conn.exec_driver_sql(
                "INSERT INTO ingredient_skin_score_new "
                "(ingredient_id, skin_type, is_risk, function, source, caution) "
                "SELECT ingredient_id, skin_type, is_risk, function, source, caution "
                "FROM ingredient_skin_score"
            )
            conn.exec_driver_sql("DROP TABLE ingredient_skin_score")
            conn.exec_driver_sql(
                "ALTER TABLE ingredient_skin_score_new RENAME TO ingredient_skin_score"
            )
            print("rebuilt table without score/evidence_level (PRIMARY KEY preserved)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=settings.database_url)
    args = parser.parse_args()
    migrate(args.db_url)
