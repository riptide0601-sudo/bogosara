"""

입력:
  1. 전처리된 배합목적 데이터 (ingredient_purpose_all_processed.xlsx) - 고정
  2. OCR로 추출한 전성분표 텍스트 (제품마다 다름)

출력:
  - 주요 성분 5개
  - 주요 효능 리스트 (중복 제거 최대 5개)

핵심 원칙: "이 제품이 실제로 피부에 무엇을 하는가"
  - 피부 효능이 있으면 포함
  - 피부 효능이 없는 순수 기술적 역할(제형 재료)만 제외
  - 정제수만 하드코딩으로 직접 예외 처리, 나머지는 전부 배합목적 사전 조회로 판단
  - 화학적으로 유사한 성분군(폴리올류 등)은 배합목적까지 같아야 대표 1개로 묶임
  - 순위 계산은 오직 order_index(배합순서) 기준
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models.product import Product


# ============================================================
# 1. 배합목적 사전 로드
# ============================================================
def load_purpose_db(kcia_path: str) -> dict:
    """전처리된 배합목적 엑셀 파일을 {성분명: [배합목적, ...]} 형태로 로드 (구명칭 alias 포함).

    이 프로젝트 백엔드에는 pandas가 의존성으로 없다 (standalone 분석 스크립트용 경로라
    여기서만 지연 import). DB에 이미 적재된 배합목적을 쓰려면 load_purpose_db_from_db()를
    대신 사용할 것 — analyze_product_from_orm()이 그 경로다.
    """
    import pandas as pd

    kcia = pd.read_excel(kcia_path)

    def normalize(x):
        if pd.isna(x):
            return []
        x = str(x).replace('，', ',').replace('.', ',')
        x = re.sub(r'\s+', '', x)
        return [p for p in re.split(r'[,、]', x) if p and p != '배합목적없음']

    db = {}
    for _, row in kcia.iterrows():
        name = str(row['성분명']).strip()
        purposes = normalize(row['배합목적'])
        # set 대신 순서를 보존하며 중복만 제거 (dict.fromkeys 활용)
        existing = db.setdefault(name, [])
        for p in purposes:
            if p not in existing:
                existing.append(p)
        if pd.notna(row.get('구명칭')):
            for alias in re.split(r'[,、]', str(row['구명칭'])):
                alias = alias.strip()
                if alias:
                    alias_existing = db.setdefault(alias, [])
                    for p in purposes:
                        if p not in alias_existing:
                            alias_existing.append(p)
    return db


def load_purpose_db_from_db(db: "Session") -> dict:
    """load_purpose_db()의 DB 버전. app.models(ingredient/ingredient_purpose/purpose)에
    이미 적재된 KCIA 배합목적 데이터로 {성분명: [배합목적, ...]} 사전을 만든다
    (ingredient.synonyms를 구명칭 alias로 취급). 엑셀 파일을 다시 읽지 않아도 된다."""
    from sqlalchemy import select

    from app.models.ingredient import Ingredient
    from app.models.ingredient_purpose import IngredientPurpose
    from app.models.purpose import Purpose

    rows = db.execute(
        select(Ingredient.name_kr, Purpose.purpose_name)
        .join(IngredientPurpose, IngredientPurpose.ingredient_id == Ingredient.ingredient_id)
        .join(Purpose, Purpose.purpose_id == IngredientPurpose.purpose_id)
        .where(Ingredient.name_kr.isnot(None))
    ).all()

    purpose_db: dict[str, list[str]] = {}
    for name_kr, purpose_name in rows:
        existing = purpose_db.setdefault(name_kr, [])
        if purpose_name not in existing:
            existing.append(purpose_name)

    synonym_rows = db.execute(
        select(Ingredient.name_kr, Ingredient.synonyms).where(
            Ingredient.name_kr.isnot(None), Ingredient.synonyms.isnot(None)
        )
    ).all()
    for name_kr, synonyms in synonym_rows:
        # synonyms 컬럼이 SQL NULL은 아니어도 JSON null 값을 담은 행이 있어서(isnot(None)
        # 필터는 SQL NULL만 걸러내고, JSON null은 역직렬화되면 파이썬 None이 된다),
        # 여기서 한 번 더 방어한다.
        if not synonyms:
            continue
        purposes = purpose_db.get(name_kr)
        if not purposes:
            continue
        for alias in synonyms:
            alias_existing = purpose_db.setdefault(alias, [])
            for p in purposes:
                if p not in alias_existing:
                    alias_existing.append(p)
    return purpose_db


# ============================================================
# 2. 고정 규칙 (배합목적 기반이므로 데이터가 바뀌어도 이 부분은 안정적)
# ============================================================
PURE_SOLVENT = {"정제수", "물"}

EXCLUDE_CATEGORIES = {
    # 용매/제형 구조
    "용제", "점도증가제(수성)", "점도증가제(비수성)", "점증제-수용성", "점증제-비수용성",
    "점증제", "증점제", "점도조절제", "점도감소제",
    "유화안정제", "결합제", "벌킹제", "벌킹제(증량제)", "불투명화제", "표면조정제",
    "흡착제",
    # 계면활성 (세정/유화 목적, 피부효능 아님)
    "계면활성제", "계면활성제(유화제)", "계면활성제(세정제)", "계면활성제(거품촉진제)",
    "계면활성제(거품형성제)", "계면활성제(용해보조제)", "계면활성제(친수제)",
    "계면활성제(분산제)", "계면활성제(수성)", "계면활성제(점도증가제)", "계면활성제(현탁화제)",
    "분산제(비계면활성제)", "현탁화제(비계면활성제)", "활성제(세정제)",
    "유화제", "연제", "유연화제",
    # 보존/안정화
    "방부제", "방부보조제", "보존제", "pH조정제", "PH조정제", "pH완충제", "pH 조정제", "pH 완충제",
    "금속이온봉쇄제", "킬레이트화제", "부식방지제", "변색방지제", "산화방지제(제형용)",
    # 감각/외관 (피부 효능 아님)
    "착색제", "착향제", "향료", "착색제(화장비누)",
    # 기타 순수 기술 재료
    "가소제", "안티케이킹제", "정전기방지제", "미끄럼조정제/활택제", "미끄럼개선제", "미끄럼조정제",
    "기포방지제", "변성제", "분사제", "산화제", "환원제", "연마제",
    "점착제", "완충화제", "감미제",
    # 스킨케어 프로젝트라 신체 다른 부위 전용 목적 제외
    "헤어컨디셔닝제", "모발컨디셔닝제", "두피컨디셔닝제", "모발고정제",
    "네일컨디셔닝제", "헤어스트레이트너용제", "헤어컨디셔닝제(보습제)", "헤어고정제",
    "속눈썹컨디셔닝제", "비듬방지제",
    # 스킨케어(도포형 화장품)와 무관한 시술/처리 용도
    "제모제", "제모제(물리적)", "제모제(화학적)", "염모제", "퍼머넌트웨이브용제",
}

# 정보 가치가 낮아 최후 fallback으로만 쓰는 라벨
# (kcia에서 지나치게 광범위하게 쓰이는 카테고리들 - 건수가 많을수록 의미가 뭉뚱그려지는 경향)
LOW_INFO_PURPOSES = {
    "피부컨디셔닝제(기타)",  # 8,001건
    "피부컨디셔닝제",       # 1,019건
    "피부보호제",           # 1,912건
}

# 딱딱한 배합목적 원문 -> 자연스러운 사용자용 워딩
# 사용자 지정 예외 워딩 - 일반 규칙(제/피부 제거)을 타지 않고 이 값을 그대로 사용
WORDING_OVERRIDES = {
    "수렴제": "수렴제",
    "피부보호제": "피부보호",
    "피부유연화제": "피부유연화",
    "필름형성제": "필름형성제",
    "흡수제": "흡수제",
}


def normalize_purpose_wording(raw: str, prefer_bracket_for_conditioning: bool = True) -> str:
    """
    임의 번역(단어 자체를 바꾸는 것) 없이, 괄호 표기만 규칙적으로 정리한다.
      - 끝의 "제"는 떼어낸다 (예: "보습제"->"보습", "유연제"->"유연")
        -> "보습"과 "보습제"처럼 사실상 같은 말이 중복으로 남는 것을 방지
      - "피부"로 시작하면 "피부"도 떼어낸다 (예: "피부보습"->"보습")
      - "피부컨디셔닝제(보습제)" 처럼 "컨디셔닝제"가 앞에 붙은 경우 -> 괄호 안 값만 사용 ("보습제")
      - "미백개선(기능성화장품)" 처럼 그 외의 경우 -> 괄호를 떼고 앞부분만 사용 ("미백개선")
      - 괄호가 없으면 원문 그대로
      - prefer_bracket_for_conditioning=False 이면, "컨디셔닝제"라도 괄호 안 값 대신
        앞부분을 사용 (예: LOW_INFO fallback에서 "피부컨디셔닝제(기타)"의 "기타"처럼
        괄호 안 값 자체가 의미 없는 경우를 위한 예외)
      
      - WORDING_OVERRIDES에 등록된 항목은 위 규칙을 타지 않고 지정된 값을 그대로 사용
    """
    if raw in WORDING_OVERRIDES:
        return WORDING_OVERRIDES[raw]

    if '(' in raw and raw.endswith(')'):
        front, bracket = raw.split('(', 1)
        bracket = bracket.rstrip(')')
        if prefer_bracket_for_conditioning and '컨디셔닝제' in front:
            word = bracket
        else:
            word = front
    else:
        word = raw

    if word.endswith('제') and len(word) > 1:
        word = word[:-1]
    if word.startswith('피부') and len(word) > 2:
        word = word[2:]
    return word

# 화학적 유사군: 이름 패턴 -> 대표 표시 라벨
# (같은 그룹 안에서도 실제 배합목적이 다르면 대표가 여러 개로 갈라짐)
CHEMICAL_GROUPS = {
    "폴리올류": {
        "pattern": re.compile(r"^(글리세린|부틸렌글라이콜|다이프로필렌글라이콜|프로필렌글라이콜|"
                               r"프로판다이올|메틸프로판다이올|트라이프로필렌글라이콜|폴리글리세린-?\d*)$"),
        "label": "보습",
    },
    "하이알루론산_유도체군": {
        "pattern": re.compile(r"하이알루로네이트|하이알루로닉애씨드"),
        "label": "보습",
    },
    "콜라겐_엘라스틴군": {
        "pattern": re.compile(r"콜라겐|엘라스틴"),
        "label": "탄력/보습",
    },
    "펩타이드군": {
        "pattern": re.compile(r"펩타이드"),
        "label": "피부재생/컨디셔닝",
    },
    "세라마이드군": {
        "pattern": re.compile(r"^세라마이드"),
        "label": "피부장벽강화",
    },
}
AMINO_ACID_LIST = {
    "글라이신", "세린", "글루타믹애씨드", "아스파틱애씨드", "류신", "알라닌", "라이신", "알지닌",
    "타이로신", "페닐알라닌", "트레오닌", "프롤린", "발린", "아이소류신", "히스티딘", "메티오닌", "시스테인"
}
AMINO_ACID_LABEL = "보습(천연보습인자)"


def get_chemical_group(name: str):
    if name in AMINO_ACID_LIST:
        return "아미노산_콤플렉스군", AMINO_ACID_LABEL
    for group_name, info in CHEMICAL_GROUPS.items():
        if info["pattern"].search(name):
            return group_name, info["label"]
    return None, None


# ============================================================
# 3. OCR 텍스트 파싱
# ============================================================
def parse_ingredient_text(text: str) -> list:
    """
    OCR로 추출한 전성분표 텍스트 -> [(order_index, 성분명), ...]
    - ppm/% 등 괄호 표기 제거
    - "1,2-헥산다이올"처럼 성분명 내부에 쉼표가 있는 경우를 보호 처리
    """
    text = text.replace('，', ',').replace('\n', ' ')
    text = re.sub(r'(\d),(\d+-)', r'\1@COMMA@\2', text)  # 숫자,숫자- 패턴 보호
    parts = re.split(r'[,]', text)

    result, idx = [], 1
    for p in parts:
        p = p.replace('@COMMA@', ',')
        name = re.sub(r'\(.*?\)', '', p).strip()  # (29,049ppm) 등 제거
        if name:
            result.append((idx, name))
            idx += 1
    return result


# ============================================================
# 4. STEP 0~2: 필터링 -> 그룹화 -> 정렬 -> top5
# ============================================================
def select_top_ingredients(ingredient_list: list, purpose_db: dict, top_n: int = 5) -> list:
    # ---- STEP 0: 필터링 ----
    candidates = []
    for order_index, name in ingredient_list:
        if name in PURE_SOLVENT:
            continue
        purposes = purpose_db.get(name)
        if not purposes:  # 사전 매칭 실패 또는 배합목적없음 -> 제외
            continue
        if all(p in EXCLUDE_CATEGORIES for p in purposes):
            continue
        candidates.append({"order_index": order_index, "name": name, "purposes": purposes})

    # ---- STEP 0.5: 화학적 유사군 -> 배합목적 재분할 -> 대표 선정 ----
    chem_grouped, ungrouped = {}, []
    for c in candidates:
        group_name, group_label = get_chemical_group(c["name"])
        c["chem_group"] = group_name
        c["chem_group_label"] = group_label
        (chem_grouped.setdefault(group_name, []) if group_name else ungrouped).append(c)

    representatives = list(ungrouped)
    for group_name, members in chem_grouped.items():
        sub_groups = {}
        for m in members:
            key = tuple(sorted(m["purposes"]))  # 실제 배합목적 조합이 같은 것끼리만 묶임
            sub_groups.setdefault(key, []).append(m)
        for key, sub_members in sub_groups.items():
            sub_members.sort(key=lambda x: x["order_index"])
            rep = sub_members[0]
            if len(sub_members) > 1:
                rep["group_note"] = f"{group_name} 대표 (동일역할 {len(sub_members)}개 중)"
            representatives.append(rep)

    # ---- STEP 1~2: 정렬 후 상위 N개 ----
    representatives.sort(key=lambda x: x["order_index"])
    return representatives[:top_n]


# ============================================================
# 5. 표시 라벨 (우선순위: 화학그룹 라벨 > 사전 유의미 라벨 > 최후 fallback)
# ============================================================
def get_display_labels(item: dict) -> list:
    """
    우선순위를 임의로 정하지 않고, 필터링만으로 라벨을 뽑는다.
      1. 화학적 그룹에 속하면 그 그룹 라벨만 사용
      2. 그게 아니면, EXCLUDE_CATEGORIES와 LOW_INFO_PURPOSES를 제외하고
         "남은 배합목적을 전부" 라벨로 사용 (1개로 줄이지 않음)
      3. 필터링 후 아무것도 안 남으면(전부 LOW_INFO뿐이었으면),
         그때만 LOW_INFO 중 하나를 최후 수단으로 사용
    """
    if item.get("chem_group_label"):
        return [item["chem_group_label"]]

    purposes = item["purposes"]
    filtered = [p for p in purposes if p not in EXCLUDE_CATEGORIES and p not in LOW_INFO_PURPOSES]

    if filtered:
        labels = [normalize_purpose_wording(p) for p in filtered]
    else:
        low_info_only = [p for p in purposes if p in LOW_INFO_PURPOSES]
        labels = [normalize_purpose_wording(low_info_only[0], prefer_bracket_for_conditioning=False)] if low_info_only else ["피부컨디셔닝제"]

    seen = []
    for l in labels:
        if l not in seen:
            seen.append(l)
    return seen


def split_effects(label: str) -> list:
    """'탄력/보습' 같은 슬래시 결합 라벨을 개별 단어로 분리"""
    return [p.strip() for p in label.split('/') if p.strip()]


# ============================================================
# 6. 최종 실행 함수 - 성분/효능 분리 출력
# ============================================================
def analyze_product(ingredient_text: str, purpose_db: dict) -> dict:
    ing_list = parse_ingredient_text(ingredient_text)
    top_items = select_top_ingredients(ing_list, purpose_db, top_n=5)

    ingredients = [item["name"] for item in top_items]

    effects = []
    for item in top_items:
        for label in get_display_labels(item):
            for eff in split_effects(label):
                if eff not in effects:
                    effects.append(eff)

    return {
        "ingredients": ingredients,
        "effects": effects,
        "detail": top_items,  # 그룹 노트 등 상세 확인용
    }


def analyze_product_from_orm(product: "Product", purpose_db: dict, top_n: int = 5) -> dict:
    """analyze_product()의 DB 버전. OCR 원문을 다시 파싱하지 않고, 이미
    ingredient_matching으로 매칭되어 product_ingredient(label_rank)에 저장된 순서를
    그대로 order_index로 써서 STEP0~2를 돈다. purpose_db는 load_purpose_db_from_db()로 만든다.
    product.product_ingredients와 각 pi.ingredient는 미리 selectinload 되어 있어야 한다."""
    ingredient_list = [
        (pi.label_rank, pi.ingredient.name_kr or pi.ingredient.name_en)
        for pi in product.product_ingredients
        if pi.label_rank is not None and (pi.ingredient.name_kr or pi.ingredient.name_en)
    ]
    top_items = select_top_ingredients(ingredient_list, purpose_db, top_n=top_n)

    ingredients = [item["name"] for item in top_items]

    effects = []
    for item in top_items:
        for label in get_display_labels(item):
            for eff in split_effects(label):
                if eff not in effects:
                    effects.append(eff)

    return {
        "ingredients": ingredients,
        "effects": effects,
        "detail": top_items,
    }


# ============================================================
# 실행 예시
# ============================================================
if __name__ == "__main__":
    PURPOSE_DB = load_purpose_db("/mnt/user-data/uploads/ingredient_purpose_all_processed.xlsx")

    PRODUCTS = {
        "아누아 PDRN 히알루론산 캡슐 100 세럼": "하이드롤라이즈드하이알루로닉애씨드(29,049ppm),나이아신아마이드,하이드롤라이즈드콜라겐,소듐하이알루로네이트(800ppm),아데노신,소듐디엔에이(100ppm),하이알루로닉애씨드(30ppm),하이드롤라이즈드소듐하이알루로네이트(30ppm),하이드록시프로필트라이모늄하이알루로네이트(30ppm),포타슘하이알루로네이트(30ppm),소듐하이알루로네이트크로스폴리머(30ppm),소듐아세틸레이티드하이알루로네이트(1ppm),시트릭애씨드",

        "메디큐브 PDRN 핑크 펩타이드 앰플": "정제수,글리세린,다이프로필렌글라이콜,아이소프로필미리스테이트,글리세레스-26,나이아신아마이드,1,2-헥산다이올,소듐디엔에이,부틸렌글라이콜,폴리글리세린-3,소듐아크릴레이트/소듐아크릴로일다이메틸타우레이트코폴리머,폴리아이소부텐,아크릴레이트/C10-30알킬아크릴레이트크로스폴리머,이리추출물,트로메타민,글리세릴아크릴레이트/아크릴릭애씨드코폴리머,피브이엠/엠에이코폴리머,에틸헥실글리세린,카프릴릴글라이콜,향료,인도멀구슬나무잎추출물,아데노신,카프릴릴/카프릴글루코사이드,솔비탄올리에이트,인도멀구슬나무꽃추출물,소듐하이알루로네이트,다이소듐이디티에이,울금뿌리추출물,사이아노코발아민,하이드롤라이즈드콜라겐,유비퀴논,홀리바질잎추출물,참산호말추출물,팔미토일펜타펩타이드-4,팔미토일트라이펩타이드-1,팔미토일테트라펩타이드-7,카퍼트라이펩타이드-1,아세틸헥사펩타이드-8,연어알추출물,아텔로콜라겐",

        "아누아 TXA 나이아신 흔적 세럼": "정제수,글리세린,나이아신아마이드(10%),트라넥사믹애씨드(4%),부틸렌글라이콜,다이에톡시에틸석시네이트,1,2-헥산다이올,알부틴,펜틸렌글라이콜,소듐하이알루로네이트,잔탄검,베타인살리실레이트,알파-알부틴,수크로오스팔미테이트,아이비고드열매추출물,한련초추출물,하이드로제네이티드레시틴,젤란검,퀸즈랜드넛오일,올리브오일,호호바씨오일,포도씨오일,소듐파이테이트,셀룰로오스,카프릴릭/카프릭트라이글리세라이드,판테놀,사이아노코발아민,폴리글루타믹애씨드,3-O-에틸아스코빅애씨드,세라마이드엔피,덱스트린,카카오추출물,하이드롤라이즈드하이알루로닉애씨드",

        "넘버즈인 1번 판토텐산 액티브업 수딩세럼": "정제수,부틸렌글라이콜,나이아신아마이드,글리세린,다이프로필렌글라이콜,1,2-헥산다이올,판테놀,도둑놈의지팡이뿌리추출물,아크릴레이트/C10-30알킬아크릴레이트크로스폴리머,프로판다이올,다이에톡시에틸석시네이트,트로메타민,하이드로제네이티드레시틴,암모늄아크릴로일다이메틸타우레이트/브이피코폴리머,베타인,판토테닉애씨드,트레할로오스,에틸헥실글리세린,글리세릴올리에이트,소듐파이테이트,알란토인,알파-알부틴",

        "더마팩토리 나이아신아마이드 20% 세럼": "다마스크장미꽃수,나이아신아마이드,글리세린,부틸렌글라이콜,1,2-헥산다이올,아크릴레이트/C10-30알킬아크릴레이트크로스폴리머,에틸헥실글리세린,트로메타민,잔탄검,다이소듐이디티에이",

        "VT 리들샷 100 에센스": "정제수,다이프로필렌글라이콜,글리세린,나이아신아마이드,부틸렌글라이콜,마카다미아씨오일,1,2-헥산다이올,에틸헥실팔미테이트,소듐아크릴레이트/소듐아크릴로일다이메틸타우레이트코폴리머,폴리아이소부텐,실리카,글리세레스-26,에틸헥실글리세린,카프릴릴글라이콜,아데노신,소듐폴리아크릴레이트,소듐하이알루로네이트,병풀추출물,카프릴릴/카프릴글루코사이드,솔비탄올리에이트,잔탄검,프로폴리스추출물",

        "에스트라 아토베리어365 하이드로에센스": "정제수,부틸렌글라이콜,글리세린,스쿠알란,1,2-헥산다이올,아크릴레이트/C10-30알킬아크릴레이트크로스폴리머,카보머,트로메타민,글리세릴카프릴레이트,에틸헥실글리세린,다이소듐이디티에이,낫토검,스테아릭애씨드,하이드록시프로필비스팔미타마이드엠이에이,만니톨,피씨에이,락틱애씨드,글루코오스,글라이신,우레아,소듐글리세로포스페이트,세린,글루타믹애씨드,토코페롤",

        "아누아 복숭아 70 나이아신아마이드 세럼": "복숭아수(70%),글리세린,나이아신아마이드(5%),부틸렌글라이콜,다이에톡시에틸석시네이트,정제수,1,2-헥산다이올,락토바실러스발효물,소듐하이알루로네이트,스핑고모나스발효추출물,알파-알부틴,인도멀구슬나무꽃추출물,홀리바질잎추출물,인도멀구슬나무잎추출물,잇꽃씨오일,멕시칸치아씨오일,울금뿌리추출물,참산호말추출물,하이드롤라이즈드하이알루로닉애씨드,편백잎추출물",

        "메디힐 비타민씨 브라이트닝 세럼": "정제수,글리세린,부틸렌글라이콜,베타인,나이아신아마이드(30,000ppm),1,2-헥산다이올,메틸프로판다이올,인도멀구슬나무꽃추출물,홀리바질잎추출물,인도멀구슬나무잎추출물,울금뿌리추출물,참산호말추출물,소듐하이알루로네이트,하이드롤라이즈드하이알루로닉애씨드,카카오추출물,하이알루로닉애씨드,판테놀(5,000ppm),폴리글리세릴-10라우레이트,하이드로제네이티드레시틴,암모늄아크릴로일다이메틸타우레이트/브이피코폴리머,트로메타민,카프릴릭/카프릭트라이글리세라이드,에틸헥실글리세린,프로판다이올,아데노신,소듐하이알루로네이트크로스폴리머,토코페롤(200ppm)",

        "스킨1004 마다가스카르 센텔라 앰플": "정제수,글리세린,부틸렌글라이콜,병풀추출물,1,2-헥산다이올,셀룰로오스검,에틸헥실글리세린",
    }

    print("="*70)
    print("S-03 핵심 성분/효능 분석 결과 (전처리 배합목적 데이터 + OCR 성분표만 사용)")
    print("="*70)

    for pname, text in PRODUCTS.items():
        result = analyze_product(text, PURPOSE_DB)
        print(f"\n【{pname}】")
        print(f"  주요 성분(5): {', '.join(result['ingredients'])}")
        print(f"  주요 효능({len(result['effects'])}): {', '.join(result['effects'])}")
