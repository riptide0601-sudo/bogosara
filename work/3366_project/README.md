# LabelLens API

화장품 라벨(전성분표)을 분석해 핵심 성분·효능·피부타입별 위험/궁합 성분·비슷한 제품을 보여주는 FastAPI 백엔드입니다. PostgreSQL에 실제 제품·성분 데이터가 들어있고, `data/labellens.db`(SQLite)는 그 원본 데이터 백업/마이그레이션 소스로 남아 있습니다.

## 로컬 실행 (개발용)

```bash
# 1. 가상환경 및 의존성 설치
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt

# 2. .env 생성
copy .env.example .env
```

`.env`의 `DATABASE_URL`은 기본적으로 `postgresql+psycopg2://labellens:labellens@localhost:5432/labellens`를 가리킵니다. PostgreSQL을 아래 두 방법 중 편한 쪽으로 띄우세요.

### PostgreSQL 기동 — 방법 A: Docker (권장)

```bash
docker compose up -d db
```

`db` 서비스가 `postgres:16-alpine` 이미지로 뜨고, `postgres_data` named volume에 데이터가 영속됩니다. 컨테이너를 내렸다 올려도 데이터는 유지됩니다.

### PostgreSQL 기동 — 방법 B: 네이티브 설치 (Docker를 못 쓰는 환경, 예: 이 devenv sandbox)

Docker-in-Docker가 막혀 있는 환경(권한 없는 컨테이너 등)에서는 PostgreSQL을 직접 설치해서 띄워야 합니다.

```bash
# 최초 1회 설치
sudo apt-get install -y postgresql postgresql-contrib

# 기동 (systemd가 없는 환경이라 수동으로 클러스터를 켜야 함)
sudo pg_ctlcluster 14 main start

# 계정/DB 생성 (.env와 동일한 자격증명, 최초 1회)
sudo -u postgres psql -c "CREATE USER labellens WITH PASSWORD 'labellens';"
sudo -u postgres psql -c "CREATE DATABASE labellens OWNER labellens;"
```

⚠️ 이 방식은 PostgreSQL 데이터 디렉터리(`/var/lib/postgresql/`)가 컨테이너 로컬(비영속) 파일시스템에 있는 경우가 많습니다. `/home` 같은 영속 스토리지가 아니라면 devenv가 재시작될 때 데이터가 사라질 수 있으니, 그때는 위 설치·기동·계정 생성 과정과 아래 마이그레이션을 다시 실행하면 됩니다.

- 상태 확인: `sudo pg_lsclusters`
- 정지: `sudo pg_ctlcluster 14 main stop`
- 접속 확인: `psql "postgresql://labellens:labellens@localhost:5432/labellens"`

### 데이터 이관 (방법 A/B 공통, 최초 1회 또는 data/labellens.db 갱신 시)

```bash
python -m scripts.migrate_sqlite_to_postgres
```

`data/labellens.db`(SQLite)의 전체 데이터를 PostgreSQL로 복사합니다. 실행할 때마다 기존 PostgreSQL 데이터를 지우고 SQLite 원본 기준으로 다시 채우므로(멱등), 원본이 최신 상태(source of truth)입니다.

### PostgreSQL에서 바꾼 내용을 git에 반영하기

git은 `data/labellens.db` 파일만 추적하고 PostgreSQL 자체(서버·볼륨)는 추적하지 않습니다. 앱 API나 DB 클라이언트로 PostgreSQL 데이터를 직접 수정했다면, 그 내용을 git에 남기기 위해 반대 방향 스크립트로 SQLite 파일에 다시 내보낸 뒤 커밋하세요.

```bash
python -m scripts.migrate_postgres_to_sqlite
git add data/labellens.db
git commit -m "..."
git push
```

### 백엔드 서버 실행

```bash
uvicorn app.main:app --reload
```

실행 후 http://127.0.0.1:8000 에서 검색 프론트엔드를, http://127.0.0.1:8000/docs 에서 API 문서를 확인할 수 있습니다.

"쉬운 설명 생성"(`/ingredients/{id}/generate-summary`) 기능을 쓰려면 로컬에 [Ollama](https://ollama.com)를 설치하고 `ollama pull gemma2:2b` 후 `ollama serve`로 띄워둬야 합니다. 없어도 나머지 기능은 정상 동작합니다.

## Docker로 배포

```bash
docker compose up -d --build
```

`db`(PostgreSQL 16, 포트 5432), `app`(FastAPI, 포트 8000), `ollama`(gemma2:2b, 포트 11434) 세 컨테이너가 함께 뜨고, `ollama` 컨테이너가 최초 기동 시 모델을 자동으로 pull합니다(최초 1회는 다운로드 시간이 걸립니다). `db`는 named volume(`postgres_data`)에, `data/`는 바인드 마운트로 유지되어 컨테이너를 내려도 데이터가 보존됩니다. `app`은 `db`가 healthy 상태가 될 때까지 기동을 기다립니다.

최초 기동 후 PostgreSQL이 비어 있으므로 한 번은 마이그레이션을 실행해야 합니다:

```bash
docker compose exec app python -m scripts.migrate_sqlite_to_postgres
```

## 구조

```
app/
  models/          # SQLAlchemy 모델: product, ingredient, purpose, ingredient_purpose,
                    # product_ingredient, ingredient_skin_score, ingredient_relation,
                    # llm_summary, product_concern
  schemas/         # Pydantic 스키마
  routers/         # products / ingredients / purposes / ocr 엔드포인트
  static/          # 검색 프론트엔드 (index.html, FastAPI가 정적 서빙)
  core_ingredient_selector.py # 핵심 성분/효능 추출
  search_service.py           # 제품 검색 (이름/브랜드/카테고리 토큰 매칭)
  similarity.py               # 제품 유사도
  skin_fit.py                 # 피부 타입별 위험/궁합 성분 탐지
  ingredient_matching.py      # 자유 텍스트 → 표준 성분 매칭 (공유 로직)
  fuzzy_match.py               # 자모 분리 + rapidfuzz 기반 오타/OCR 오인식 허용 검색
  product_category.py         # 제품명 → 스킨케어 루틴 단계 분류
  llm_client.py                # Ollama(gemma) 호출
  database.py      # 엔진, 세션
  config.py        # 환경변수 설정
  main.py          # FastAPI 앱 엔트리포인트
data/
  labellens.db     # SQLite DB (마이그레이션 원본 데이터, 운영 DB는 PostgreSQL)
  ingredient_purpose_all_processed.csv # 배합목적 사전(KCIA) 원본
  궁합성분.xlsx      # 피부타입별 궁합성분(추천 성분) 원본 — import_compatible_ingredients.py가 읽음
  성분_관계성.xlsx    # 성분 간 시너지/악화 관계 원본 — load_ingredient_relations.py가 읽음
scripts/
  migrate_sqlite_to_postgres.py    # SQLite → PostgreSQL 데이터 이관
  migrate_postgres_to_sqlite.py    # PostgreSQL → SQLite 데이터 내보내기 (git 반영용)
  _db_sync.py                      # 위 두 스크립트가 공유하는 테이블 복사 로직
  backfill_key_ingredients.py      # core_ingredient_selector 결과를 product.key_ingredients/key_purposes에 백필
  backfill_product_category.py     # product.category 백필
  seed_ingredient_skin_scores.py   # ingredient_skin_score 위험 성분 시드
  import_compatible_ingredients.py # 궁합성분(추천 성분) 데이터를 ingredient_skin_score에 적재
  migrate_ingredient_skin_score_polarity.py # ingredient_skin_score is_risk 컬럼 추가 마이그레이션
  load_ingredient_relations.py     # ingredient_relation(성분 시너지/악화) 시드
  import_product_list.py, import_serum_concern_list.py, _product_import_helpers.py # 제품/고민 태그 일괄 임포트
Dockerfile
docker-compose.yml
```

## 알고리즘 개요

실제 계산 로직이 있는 "알고리즘"은 7개다. (`ingredient_relation`의 성분 궁합, `product_concern`의 수분/진정/미백/모공 태그는 curated된 값을 그대로 보여주는 데이터라 계산 로직이 없어 여기서는 제외.)

| 알고리즘 | 무엇을 하는가 | 구현 |
|---|---|---|
| 검색 | 검색어를 토큰화해 제품명/브랜드/카테고리 전부에서 AND 매칭, 랭킹 점수로 정렬 | `app/search_service.py` — 아래 "검색" 참고 |
| 성분 매칭 | 검색어/OCR 토큰 하나를 표준 성분(ingredient)과 매칭 | `app/ingredient_matching.py`, `app/fuzzy_match.py` — 아래 "성분 매칭" 참고 |
| 핵심 성분/효능 추출 | 전성분표에서 정제수·용제·계면활성제 등 순수 기술적 성분을 걸러내고, 화학적으로 비슷한 성분끼리 묶어서 "핵심 성분 최대 5개 + 효능"을 뽑음 | `app/core_ingredient_selector.py` — 아래 "핵심 성분/효능 추출" 참고 |
| 제품 유사도 | 두 제품이 성분 구성 + 배합목적 분포상 얼마나 비슷한지 0~100%로 계산 | `app/similarity.py` — 아래 "제품 유사도" 참고 |
| 피부 타입별 위험/궁합 성분 탐지 | 제품 성분 중 피부타입별로 위험하다고/좋다고 근거가 있는 성분이 있는지 확인해 문장으로 요약 | `app/skin_fit.py` — 아래 "피부 타입별 위험/궁합 성분 탐지" 참고 |
| 제품 카테고리 분류 | 제품명 키워드로 스킨케어 루틴 단계(스킨/토너 → 세럼·에센스·앰플 → 크림) 분류 | `app/product_category.py` — 아래 "제품 카테고리 분류" 참고 |
| LLM 요약 생성 | 배합목적·전성분 설명을 gemma로 쉬운 문장으로 재작성해 DB에 저장 | `app/llm_client.py` |

`oliveyoung_url`(제품명으로 올리브영 검색 링크 생성)은 계산이랄 게 없는 단순 문자열 조합이라 위 7개와 같은 급으로 치지 않는다 (`app/schemas/product.py`의 `computed_field`).

## 주요 엔드포인트

- `POST /products`, `GET /products?query=&category=` — 목록/검색. 검색어가 있으면 이름/브랜드/카테고리 토큰 매칭으로 찾는다(아래 "검색" 참고). 응답마다 `key_ingredients`/`key_purposes`/`skin_score_summary`가 같이 내려간다.
- `GET /products/{id}` — 성분·배합목적·LLM 요약·`top_ingredients`·`similar_products`·`skin_score_summary`까지 포함한 상세 조회
- `GET /products/{id}/similar?min_score=&limit=` — 성분 유사 제품 추천 (아래 "제품 유사도" 참고)
- `GET /products/{id}/skin-fit?skin_type=` — 피부 타입별 위험/궁합 성분 탐지 (아래 "피부 타입별 위험/궁합 성분 탐지" 참고)
- `PUT /products/{id}/ingredients`, `DELETE /products/{id}/ingredients/{ingredient_id}` — 성분 매칭 결과 연결/해제 (중복 연결은 `ON CONFLICT DO NOTHING`으로 무시)
- `POST /products/{id}/generate-summary` — 전성분 목록을 gemma로 한두 문장 요약해 저장 (이미 있으면 캐시된 값을 그대로 반환)
- `POST /ocr/analyze` — 라벨 사진 업로드 → OCR로 텍스트 추출 → 표준 성분 매칭까지 한 번에 (아래 "성분 매칭" 참고)
- `POST /ingredients`, `GET /ingredients?query=` (name_kr/name_en/synonyms 검색, 배합목적 포함; 정확/부분일치가 없으면 자모 단위 유사도로 오타·OCR 오인식을 보정하는 fuzzy 검색으로 자동 폴백), `GET /ingredients/{id}`, `PATCH /ingredients/{id}`
- `GET /ingredients/{id}/relations` — 이 성분과 시너지/악화 관계로 등록된 다른 성분 목록
- `PUT /ingredients/{id}/purposes/{purpose_id}`, `DELETE /ingredients/{id}/purposes/{purpose_id}` — 성분에 배합목적 연결/해제
- `GET|PUT /ingredients/{id}/llm-summary` — 좋은 점/주의할 점 등 조회·수정
- `POST /ingredients/{id}/generate-summary` — 배합목적 설명을 gemma로 쉬운 문장으로 재작성
- `POST /purposes`, `GET /purposes`, `GET /purposes/{id}`

## 검색

`GET /products?query=`가 쓰는 제품 검색 알고리즘. 성분명·배합목적은 검색 대상이 아니다 — "성분을 검색해도 그 성분이 든 제품이 뜨는 건 원치 않는다"는 요구에 맞춰 제품 자체의 표면 정보(이름/브랜드/카테고리)로만 좁혔다.

1. 검색어를 공백 기준으로 토큰화한다.
2. 각 토큰이 이름/브랜드/카테고리 중 하나 이상에 부분 문자열로 있어야 결과에 포함시킨다(토큰 간 AND, 필드 간 OR). 예: "아누아 세럼" → "아누아"는 브랜드에서, "세럼"은 이름 또는 카테고리에서 각각 찾아서 둘 다 있으면 매칭. 순서나 붙어있는지는 안 따진다.
3. 랭킹 점수 = 검색어 전체와 이름이 완전히 일치하면 보너스 + 토큰별로 이름(40)/브랜드(35)/카테고리(20) 부분일치 가중치를 합산한 값. 점수 내림차순으로 정렬해 상위 결과를 반환한다.

`?category=` 필터를 같이 주면 검색 결과에서 한 번 더 걸러낸다.

- 구현: `app/search_service.py`.

## 성분 매칭

자유 텍스트(검색창 입력어, OCR로 읽은 라벨 원문 토큰)를 표준 성분(ingredient) 하나와 이어붙이는 알고리즘. 검색창(`GET /ingredients?query=`)과 OCR 분석(`POST /ocr/analyze`)이 이 로직을 공유한다.

1. **정확/부분 일치** — `name_kr`/`name_en`/`synonyms`에 대한 substring 매칭. 여러 개 걸리면 검색어와 정확히 일치하는 이름을 먼저 배치(알파벳순만으로는 "잔탄검" 검색 시 "데하이드로잔탄검"이 먼저 나오는 문제 방지).
2. **자모 기반 fuzzy 매칭** — 1단계에서 하나도 안 걸리면, `hgtk`로 자모 분해한 뒤 `rapidfuzz`로 유사도(85% 이상)를 계산해 오타·OCR 오독을 보정한다(예: "나이아신아미드" → "나이아신아마이드"). 서버 시작 시 전체 성분명을 한 번 자모 분해해 메모리에 캐싱해두고 재사용한다(`app/fuzzy_match.py`).
3. **파묻힌 성분명 찾기** — OCR 전용 마지막 폴백. 라벨 원문에 쉼표가 없는 지점(문장 경계 등)에서 이웃 문구와 통째로 합쳐진 토큰(예: "...아데노신사용할 때의 주의사항...")에서, 토큰 안에 성분명이 부분 문자열로 파묻혀 있는지 역방향으로 찾는다. 겹치지 않는 구간을 긴 것부터 그리디하게 채택해 한 토큰에서 성분 여러 개를 복원할 수도 있다.

구현: `app/ingredient_matching.py`(공유 로직), `app/fuzzy_match.py`(2단계), `app/routers/ingredients.py`의 `search_ingredient_ids`(1~2단계).

## 핵심 성분/효능 추출

전성분표에 적힌 성분 전부가 "이 제품이 피부에 하는 일"을 말해주진 않는다 — 용제·점증제·계면활성제 같은 순수 제형 재료도 섞여 있다. `core_ingredient_selector`는 배합목적(KCIA) 사전을 기준으로 이런 성분을 걸러내고, 실제 피부 효능이 있는 성분만 남겨서 "핵심 성분"을 뽑는다.

1. **필터링** — 정제수는 하드코딩으로 제외, 나머지는 배합목적이 전부 `EXCLUDE_CATEGORIES`(용제·점증제·계면활성제·방부제·착향제 등 피부 효능이 없는 순수 기술적 역할)에 속하면 제외.
2. **화학적 유사군 그룹핑** — 글리세린·부틸렌글라이콜 같은 폴리올류, 하이알루로네이트 유도체군, 세라마이드군 등은 배합목적까지 같아야 대표 성분 1개로 묶는다(`CHEMICAL_GROUPS`).
3. **정렬·상위 선정** — 남은 성분을 `label_rank`(배합순서) 기준으로 정렬해 상위 5개를 채택.
4. **효능 라벨링** — 채택된 성분마다 배합목적을 사람이 읽기 쉬운 단어로 정리(`normalize_purpose_wording`: "피부보습제" → "보습" 등)해 중복 제거된 효능 리스트를 만든다.

DB 버전(`load_purpose_db_from_db`)은 별도 엑셀 없이 `ingredient`/`ingredient_purpose`/`purpose` 테이블에서 바로 배합목적 사전을 만든다. `analyze_product_from_orm()`이 이미 매칭이 끝난 `product_ingredient`(label_rank) 순서를 그대로 써서 OCR 텍스트를 다시 파싱하지 않는다.

- 결과는 `product.key_ingredients`/`product.key_purposes`(JSON 배열 문자열)에 저장되고, `GET /products` · `GET /products/{id}` 응답에는 파싱된 `list[str]`로 내려간다.
- 요청 경로에서 직접 계산하지 않는다 — `scripts/backfill_key_ingredients.py`가 전체 제품을 돌며 미리 계산해 DB에 써 두고, API는 그 결과만 읽는다. 새 제품을 추가하거나 성분 매칭이 바뀌면 다시 실행해야 최신화된다.
- 구현: `app/core_ingredient_selector.py`, `scripts/backfill_key_ingredients.py`.

## 제품 유사도

세 가지 신호를 가중 합산해 종합 점수를 낸다.

1. **주요 성분 자카드 유사도 (50%)** — `product.key_ingredients`(아래 "핵심 성분/효능 추출" 참고 — `core_ingredient_selector`가 정제수·용제·계면활성제 등을 걸러내고 뽑은 성분 최대 5개) 집합끼리 교집합 ÷ 합집합.
2. **나머지 성분 자카드 유사도 (20%)** — 주요 성분을 제외한 나머지 전성분 집합끼리 같은 방식.
3. **배합목적 TF-IDF 벡터 코사인 유사도 (30%)** — 제품마다 배합목적(purpose) 분포를 TF-IDF 벡터로 만들어 코사인 유사도를 구한다. 성분 이름이 하나도 안 겹쳐도 "하는 일"이 비슷한 제품(예: 서로 다른 비타민C 유도체를 쓰지만 둘 다 미백/항산화 위주인 제품)까지 잡아낸다.
   - TF = 그 제품 안에서 해당 배합목적을 가진 성분 개수
   - IDF = `log((전체 제품 수 + 1) / (그 목적이 등장하는 제품 수 + 1)) + 1` — "피부컨디셔닝제(기타)"처럼 거의 모든 제품에 등장하는 흔한 목적은 낮게, "미백"·"자외선차단"처럼 일부 제품에만 등장하는 목적은 높게 가중한다.

종합 점수 = `KEY_INGREDIENT_WEIGHT(0.5)` × 주요 성분 유사도 + `REST_INGREDIENT_WEIGHT(0.2)` × 나머지 성분 유사도 + `PURPOSE_VECTOR_WEIGHT(0.3)` × 배합목적 코사인 유사도. 세 상수 다 `app/similarity.py` 상단에 있어 바로 조절 가능하다.

- `GET /products/{id}` 상세 응답에는 50% 이상인 것만 자동으로 채운 `similar_products`가 같이 내려간다. 기준을 직접 조절하려면 `GET /products/{id}/similar?min_score=&limit=`을 쓴다.
- 구현: `app/similarity.py`.
- ⚠️ "주요 성분"이라는 이름이 두 군데서 다른 뜻으로 쓰인다 — 유사도가 쓰는 `product.key_ingredients`(core_ingredient_selector 결과, 배합목적 기반 필터링+그룹핑)와, 제품 상세의 `top_ingredients`(`label_rank` 상위 `DEFAULT_TOP_K`개를 그대로 슬라이스한 것)는 서로 다른 로직으로 뽑힌 다른 리스트다.

## 피부 타입별 위험/궁합 성분 탐지

[2026-08-21 개편] 원래는 성분마다 -3(피하는 게 좋음)~+3(적극 권장) 점수를 매겨 제품 전체 적합도를 0~100점으로 합산하는 방식이었다. 점수 자체가 근거 없는 가짜 정밀도(-2점과 -3점의 차이가 실제로 뭘 의미하는지는 근거가 없음)라 폐기했고, 지금은 "위험 성분인지 / 이 피부타입에 좋다고 근거가 있는 성분인지"만 본다. 점수 합산·정규화는 하지 않는다.

- `ingredient_skin_score` 테이블에 성분 × 피부타입(지성/복합성/건성/민감성, 또는 피부타입과 무관한 "전체" — 향료 알레르겐처럼 개인 감작 여부로 생기는 위험용) 조합마다 `is_risk`(위험이면 True, 궁합 좋은 성분이면 False), 기능(`function`), 근거(`source`), 설명(`caution`)을 저장한다.
  - [2026-08-24] `score`/`evidence_level` 컬럼은 삭제했다. `score`는 처음부터 "위험 여부"만 판단하는 데 쓰였던 죽은 컬럼이었고, `evidence_level`은 문서화용일 뿐 실제 조회 로직에서 필터로 쓰인 적이 없었다.
  - 처음엔 "위험 성분"만 기록했지만, 궁합성분(추천 성분) 데이터를 같은 테이블에 넣으면서 `is_risk`로 위험/궁합을 구분하게 됐다.
- `GET /products/{id}/skin-fit`은 제품 성분 중 `is_risk=True`로 등록된 것과 겹치는 게 있으면 그 목록(`risk_ingredients`: 위험 유형/설명/출처, `has_risk`)을 그대로 보여준다. `skin_type`을 지정하면 하나만, 생략하면 4개 타입 전부 반환한다.
- 검색 결과·제품 상세 응답에는 이 테이블 전체(위험 + 궁합)를 한 문장으로 요약한 `skin_score_summary`가 같이 내려간다 — 예: `"지성에 좋은 성분 2개, 건성에 유의해야할 성분 1개 있습니다."`. 매칭이 하나도 없으면 `"..."`. 위험 성분만 보는 `/skin-fit`과 달리, 이 요약은 위험/궁합 양쪽을 `is_risk` 기준으로 한 쿼리에서 같이 집계한다.
- 구현: `app/skin_fit.py`(위험 탐지 + 요약 문장), `app/models/ingredient_skin_score.py`(스키마), `scripts/seed_ingredient_skin_scores.py`(위험 성분 시드), `scripts/import_compatible_ingredients.py`(궁합성분 시드), `scripts/migrate_ingredient_skin_score_polarity.py`(`is_risk` 컬럼 추가 + `score`/`evidence_level` 제거 마이그레이션).
- ⚠️ **극히 일부 성분만 다룬다.** 전체 22,000여 개 성분 중 30개(위험 21건, 궁합 21건, 겹치는 성분 있음)만 등록돼 있다. 위험 성분은 실제 논문/공식기관 자료(향료 알레르겐 EU SCCS 목록, 에탄올·캠퍼 관련 임상연구 등)로 뒷받침되는 것만 남겼고, 궁합성분은 건성/지성·여드름성/피부노화 관련 근거 논문 기반이다. "매칭되는 성분이 없다"는 결과가 "검증된 안전"을 의미하지 않는다 — 현재까지 확인된 것만 반영된 것이고, 계속 늘려가야 하는 작업이다.

## 제품 카테고리 분류

DB에 카테고리 컬럼(`product.category`)이 있지만, 값 자체는 제품명 키워드로 판정한다 — 제품 생성 시(`POST /products`) 한 번 계산해서 저장하고, 이후에는 필터링(`GET /products?category=`)에 그대로 쓴다.

- 스킨케어 루틴 순서를 그대로 반영: **스킨/토너**(1) → **세럼/에센스/앰플**(2) → **크림**(3) → 어디에도 안 걸리면 **기타**(99).
- 키워드 검사 순서에 주의: "스킨"은 "스킨1004"처럼 브랜드명에도 흔히 들어가서, 세럼/에센스/앰플·크림처럼 더 명확한 키워드를 먼저 확인한 뒤 스킨/토너는 맨 마지막에 확인한다. (순서를 안 지키면 "스킨1004 ... 앰플" 제품이 토너로 잘못 분류된다.)
- 구현: `app/product_category.py`. `classify()`는 제품 생성/백필 때 이름으로 분류할 때, `get_info()`는 이미 저장된 `category` 값에서 순서·설명 문구(`category_order`, `category_description`)를 다시 찾아올 때 쓴다 — 매번 제품명을 재분류하지 않고 저장된 값을 기준으로 하기 위함.
