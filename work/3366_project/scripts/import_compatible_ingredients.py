"""One-off import: data/궁합성분.xlsx의 "건성_궁합성분" 시트를 ingredient_skin_score에
is_risk=False 행으로 적재한다 (app/models/ingredient_skin_score.py 2026-08-24 개편 참고).

시트의 "관련" 컬럼:
  - "건성" -> skin_type="건성"
  - "지성 여드름성" -> skin_type="지성" (SKIN_TYPES 중 가장 가까운 값. "여드름성"은 지성의
    하위 맥락으로 취급)
  - "피부 노화" -> skin_type="전체" (특정 피부타입 전용이 아니라 노화 관리 목적이라 향료
    알레르겐처럼 피부타입 무관 행으로 취급)

성분명이 영문/복합명이라 ingredient 테이블과 바로 매칭되지 않는 행은 _NAME_ALIASES로 실제
ingredient.name_kr로 치환한다. "·"로 여러 성분이 묶인 행("알로에·히알루론산 (보습 성분)" 등)은
같은 근거 텍스트를 공유하는 별도 행 여러 개로 나눠 넣는다("나눠서 넣어줘" 요청).

"보류" 시트는 원본에 근거 부족으로 보류 권장이라고 명시돼 있어 애초에 읽지 않는다.

Usage:
    python -m scripts.import_compatible_ingredients [--xlsx-path PATH] [--db-url URL] [--dry-run]
"""

import argparse

import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models.ingredient import Ingredient
from app.models.ingredient_skin_score import SKIN_TYPES, IngredientSkinScore

_SHEET_NAME = "건성_궁합성분"
_RELATED_TO_SKIN_TYPE = {
    "건성": "건성",
    "지성 여드름성": "지성",
    "피부 노화": "전체",
}

# 시트의 "성분명"이 영문/복합명이라 ingredient.name_kr과 바로 매칭 안 되는 행 -> 실제
# ingredient 이름 목록. 한 행이 여러 성분을 가리키면(예: "알로에·히알루론산") 같은 근거를
# 공유하는 별도 행으로 나눠 넣는다.
_NAME_ALIASES = {
    "AHA (알파 하이드록시산)": ["글라이콜릭애씨드"],  # 근거 원문이 글리콜산(40%) 실험
    "BHA (베타 하이드록시산) - 살리실산": ["살리실릭애씨드"],
    "알로에·히알루론산 (보습 성분)": ["알로에잎즙", "하이알루로닉애씨드"],
    "카올린·벤토나이트 (점토)": ["카올린", "벤토나이트"],
    "Glycolic Acid": ["글라이콜릭애씨드"],
    "Lactic Acid": ["락틱애씨드"],
    "Malic Acid": ["말릭애씨드"],
    "Citric Acid": ["시트릭애씨드"],
    "Palmitoyl Pentapeptide-4 (Pal-KTTKS, 마트릭실)": ["팔미토일펜타펩타이드-4"],
    "Vitamin C": ["아스코빅애씨드"],
}


def _load_rows(xlsx_path: str) -> list[dict]:
    df = pd.read_excel(xlsx_path, sheet_name=_SHEET_NAME)
    rows = []
    for _, row in df.iterrows():
        related = str(row["관련"]).strip()
        skin_type = _RELATED_TO_SKIN_TYPE.get(related)
        raw_name = str(row["성분명"]).strip()
        summary = None if pd.isna(row["핵심 근거 요약"]) else str(row["핵심 근거 요약"]).strip()
        paper = None if pd.isna(row["출처(논문)"]) else str(row["출처(논문)"]).strip()
        link = None if pd.isna(row["링크"]) else str(row["링크"]).strip()

        for name in _NAME_ALIASES.get(raw_name, [raw_name]):
            rows.append(
                {
                    "related": related,
                    "skin_type": skin_type,
                    "raw_name": raw_name,
                    "name": name,
                    "summary": summary,
                    "paper": paper,
                    "link": link,
                }
            )
    return rows


def import_compatible_ingredients(xlsx_path: str, db_url: str, dry_run: bool = False) -> None:
    rows = _load_rows(xlsx_path)

    engine = create_engine(db_url)
    with Session(engine) as db:
        names = {r["name"] for r in rows if r["skin_type"]}
        id_by_name = dict(
            db.execute(
                select(Ingredient.name_kr, Ingredient.ingredient_id).where(
                    Ingredient.name_kr.in_(names)
                )
            ).all()
        )

        insert_fn = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
        inserted, skipped_relation, skipped_not_found = 0, [], []

        for row in rows:
            if row["skin_type"] is None:
                skipped_relation.append((row["related"], row["name"]))
                continue
            if row["skin_type"] not in SKIN_TYPES and row["skin_type"] != "전체":
                raise ValueError(f"매핑 오류: {row['skin_type']!r}는 SKIN_TYPES/전체에 없습니다")

            ingredient_id = id_by_name.get(row["name"])
            if ingredient_id is None:
                skipped_not_found.append(row["name"])
                continue

            source = " / ".join(p for p in (row["paper"], row["link"]) if p)
            values = dict(
                ingredient_id=ingredient_id,
                skin_type=row["skin_type"],
                is_risk=False,
                function=None,
                source=source or None,
                caution=row["summary"],
            )

            if dry_run:
                print(
                    f"[dry-run] insert: {row['name']} ({ingredient_id}) x {row['skin_type']}"
                    + (f"  [from: {row['raw_name']}]" if row["raw_name"] != row["name"] else "")
                )
                continue

            stmt = (
                insert_fn(IngredientSkinScore)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=["ingredient_id", "skin_type"],
                    set_={
                        "is_risk": False,
                        "function": None,
                        "source": values["source"],
                        "caution": values["caution"],
                    },
                )
            )
            db.execute(stmt)
            inserted += 1

        if not dry_run:
            db.commit()

        print(f"{inserted} rows upserted into {db_url}")
        if skipped_relation:
            print(f"skipped (관련 값이 skin_type에 매핑되지 않음, {len(skipped_relation)}건):")
            for related, name in skipped_relation:
                print(f"  - [{related}] {name}")
        if skipped_not_found:
            print(f"skipped (ingredient 테이블에 이름이 없음, {len(skipped_not_found)}건): {skipped_not_found}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx-path", default="data/궁합성분.xlsx")
    parser.add_argument("--db-url", default=settings.database_url)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    import_compatible_ingredients(args.xlsx_path, args.db_url, dry_run=args.dry_run)
