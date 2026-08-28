"""One-off: 마이페이지 "회원정보"에 나이/성별을 추가하기 위해 app_user 테이블에
age/gender 컬럼을 더한다.

app_user는 이미 있는 테이블이라 Base.metadata.create_all(tables=[...])로는 새 컬럼이
안 생긴다(create_all은 없는 테이블만 만들고, 있는 테이블의 스키마는 안 건드림) — 그래서
직접 ALTER TABLE로 컬럼만 추가한다. 이미 컬럼이 있으면 건드리지 않으니 재실행해도 안전하다.

Usage:
    python -m scripts.add_user_age_gender [--db-url URL]
"""

import argparse

from sqlalchemy import create_engine, inspect

from app.config import settings


def run(db_url: str) -> None:
    engine = create_engine(db_url)
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("app_user")}

    with engine.begin() as conn:
        if "age" not in columns:
            conn.exec_driver_sql("ALTER TABLE app_user ADD COLUMN age INTEGER")
            print("age 컬럼 추가함")
        else:
            print("age 컬럼 이미 있음")

        if "gender" not in columns:
            conn.exec_driver_sql("ALTER TABLE app_user ADD COLUMN gender VARCHAR")
            print("gender 컬럼 추가함")
        else:
            print("gender 컬럼 이미 있음")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=settings.database_url)
    args = parser.parse_args()
    run(args.db_url)
