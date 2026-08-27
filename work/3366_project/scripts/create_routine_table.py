"""One-off: 마이페이지 "내 화장품 조합" 기능에 필요한 routine_item 테이블을 만든다.

scripts/create_auth_tables.py와 같은 패턴 — create_all은 이미 있는 테이블은 건드리지
않으므로 재실행해도 안전하다.

Usage:
    python -m scripts.create_routine_table [--db-url URL]
"""

import argparse

from sqlalchemy import create_engine

from app.config import settings
from app.database import Base
from app.models.routine_item import RoutineItem


def run(db_url: str) -> None:
    engine = create_engine(db_url)
    Base.metadata.create_all(engine, tables=[RoutineItem.__table__])
    print(f"routine_item table ensured in {db_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=settings.database_url)
    args = parser.parse_args()
    run(args.db_url)
