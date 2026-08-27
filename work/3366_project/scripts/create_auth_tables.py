"""One-off: 로그인/마이페이지 기능에 필요한 app_user / saved_result 테이블을 만든다.

이 프로젝트는 alembic 마이그레이션 대신 새 테이블마다 이런 one-off 스크립트로
Base.metadata.create_all(tables=[...])을 호출하는 방식을 쓴다(scripts/
seed_ingredient_skin_scores.py 등 참고). create_all은 이미 있는 테이블은 건드리지
않으므로 재실행해도 안전하다.

Usage:
    python -m scripts.create_auth_tables [--db-url URL]
"""

import argparse

from sqlalchemy import create_engine

from app.config import settings
from app.database import Base
from app.models.saved_result import SavedResult
from app.models.user import User


def run(db_url: str) -> None:
    engine = create_engine(db_url)
    Base.metadata.create_all(engine, tables=[User.__table__, SavedResult.__table__])
    print(f"app_user / saved_result tables ensured in {db_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=settings.database_url)
    args = parser.parse_args()
    run(args.db_url)
