"""ingredient_family / ingredient_family_member 테이블을 생성한다 (alembic 미사용 — 이 프로젝트의
scripts/create_auth_tables.py 등과 같은 패턴). 이미 있으면 아무 것도 안 한다.

Usage:
    python -m scripts.create_marketing_family_tables
"""
from app.database import Base, engine
from app.models.ingredient_family import IngredientFamily
from app.models.ingredient_family_member import IngredientFamilyMember


def main() -> None:
    Base.metadata.create_all(
        engine, tables=[IngredientFamily.__table__, IngredientFamilyMember.__table__]
    )
    print("ingredient_family, ingredient_family_member 테이블 준비 완료")


if __name__ == "__main__":
    main()
