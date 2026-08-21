# LabelLens API

`LabelLens_ERD_v7.md` 스키마를 그대로 구현한 FastAPI 백엔드입니다. PostgreSQL에 실제 제품·성분 데이터가 들어있고, `data/labellens.db`(SQLite)는 그 원본 데이터 백업/마이그레이션 소스로 남아 있습니다.

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
  models/      # SQLAlchemy 모델 (ERD 테이블과 1:1)
  schemas/     # Pydantic 스키마
  routers/     # products / ingredients / purposes 엔드포인트
  static/      # 검색 프론트엔드 (index.html, FastAPI가 정적 서빙)
  llm_client.py # Ollama(gemma) 호출
  fuzzy_match.py # 자모 분리 + rapidfuzz 기반 오타/OCR 오인식 허용 검색
  database.py  # 엔진, 세션
  config.py    # 환경변수 설정
  main.py      # FastAPI 앱 엔트리포인트
data/
  labellens.db # SQLite DB (마이그레이션 원본 데이터, 운영 DB는 PostgreSQL)
scripts/
  migrate_sqlite_to_postgres.py # SQLite → PostgreSQL 데이터 이관
  migrate_postgres_to_sqlite.py # PostgreSQL → SQLite 데이터 내보내기 (git 반영용)
  _db_sync.py                   # 위 두 스크립트가 공유하는 테이블 복사 로직
Dockerfile
docker-compose.yml
```

## 알고리즘 개요

실제 계산 로직이 있는 "알고리즘"은 5개다. (`ingredient_relation`의 성분 궁합, `product_concern`의 수분/진정/미백/모공 태그는 curated된 값을 그대로 보여주는 데이터라 계산 로직이 없어 여기서는 제외.)

| 알고리즘 | 무엇을 하는가 | 구현 |
|---|---|---|
| 성분 매칭 | 검색어/OCR 토큰 하나를 표준 성분(ingredient)과 매칭 | `app/ingredient_matching.py`, `app/fuzzy_match.py` — 아래 "성분 매칭" 참고 |
| 제품 유사도 | 두 제품이 성분 구성상 얼마나 비슷한지 0~100%로 계산 | `app/similarity.py` — 아래 "제품 유사도" 참고 |
| 피부 타입별 적합도 | 제품이 지성/복합성/건성/민감성에 얼마나 맞는지 0~100점 | `app/skin_fit.py` — 아래 "피부 타입별 적합도" 참고 |
| 제품 카테고리 분류 | 제품명 키워드로 스킨케어 루틴 단계(스킨/토너 → 세럼·에센스·앰플 → 크림) 분류 | `app/product_category.py` — 아래 "제품 카테고리 분류" 참고 |
| LLM 요약 생성 | 배합목적·전성분 설명을 gemma로 쉬운 문장으로 재작성해 DB에 저장 | `app/llm_client.py` |

`oliveyoung_url`(제품명으로 올리브영 검색 링크 생성)은 계산이랄 게 없는 단순 문자열 조합이라 위 5개와 같은 급으로 치지 않는다 (`app/schemas/product.py`의 `computed_field`).

## 주요 엔드포인트

- `POST /products`, `GET /products?query=`, `GET /products/{id}` (성분·목적·LLM요약·`key_ingredients`·`similar_products`까지 포함한 상세 조회)
- `GET /products/{id}/similar?top_k=&min_score=&limit=` — 성분 유사 제품 추천 (아래 "제품 유사도" 참고)
- `GET /products/{id}/skin-fit?skin_type=` — 피부 타입별 적합도 (아래 "피부 타입별 적합도" 참고)
- `PUT /products/{id}/ingredients` — 상품에 성분 매칭 결과 연결 (중복은 `ON CONFLICT DO NOTHING`으로 무시)
- `POST /ingredients`, `GET /ingredients?query=` (name_kr/name_en/synonyms 검색, 배합목적 포함; 정확/부분일치가 없으면 자모 단위 유사도로 오타·OCR 오인식을 보정하는 fuzzy 검색으로 자동 폴백), `GET /ingredients/{id}`
- `PUT /ingredients/{id}/purposes/{purpose_id}` — 성분에 배합목적 연결
- `GET|PUT /ingredients/{id}/llm-summary` — 좋은 점/주의할 점 등 조회·수정
- `POST /ingredients/{id}/generate-summary` — 배합목적 설명을 gemma로 쉬운 문장으로 재작성
- `POST /purposes`, `GET /purposes`

## 성분 매칭

자유 텍스트(검색창 입력어, OCR로 읽은 라벨 원문 토큰)를 표준 성분(ingredient) 하나와 이어붙이는 알고리즘. 검색창(`GET /ingredients?query=`)과 OCR 분석(`POST /ocr/analyze`)이 이 로직을 공유한다.

1. **정확/부분 일치** — `name_kr`/`name_en`/`synonyms`에 대한 substring 매칭. 여러 개 걸리면 검색어와 정확히 일치하는 이름을 먼저 배치(알파벳순만으로는 "잔탄검" 검색 시 "데하이드로잔탄검"이 먼저 나오는 문제 방지).
2. **자모 기반 fuzzy 매칭** — 1단계에서 하나도 안 걸리면, `hgtk`로 자모 분해한 뒤 `rapidfuzz`로 유사도(85% 이상)를 계산해 오타·OCR 오독을 보정한다(예: "나이아신아미드" → "나이아신아마이드"). 서버 시작 시 전체 성분명을 한 번 자모 분해해 메모리에 캐싱해두고 재사용한다(`app/fuzzy_match.py`).
3. **파묻힌 성분명 찾기** — OCR 전용 마지막 폴백. 라벨 원문에 쉼표가 없는 지점(문장 경계 등)에서 이웃 문구와 통째로 합쳐진 토큰(예: "...아데노신사용할 때의 주의사항...")에서, 토큰 안에 성분명이 부분 문자열로 파묻혀 있는지 역방향으로 찾는다. 겹치지 않는 구간을 긴 것부터 그리디하게 채택해 한 토큰에서 성분 여러 개를 복원할 수도 있다.

구현: `app/ingredient_matching.py`(공유 로직), `app/fuzzy_match.py`(2단계), `app/routers/ingredients.py`의 `search_ingredient_ids`(1~2단계).

## 제품 유사도

화장품 전성분표는 배합량이 많은 성분부터 순서대로 적히므로(`product_ingredient.label_rank`), 이 순서를 "얼마나 핵심적인 성분인가"의 대용치로 쓴다.

- `label_rank` 기준 상위 `DEFAULT_TOP_K`개(기본 5개)를 **주요 성분**, 그 뒤 나머지를 **나머지 성분**으로 나눈다.
- 두 제품을 비교할 때 주요 성분 집합끼리, 나머지 성분 집합끼리 각각 자카드 유사도(교집합 개수 ÷ 합집합 개수)를 구한다.
- 종합 점수 = 주요 성분 유사도 × 0.7 + 나머지 성분 유사도 × 0.3 — 핵심 활성 성분이 같을수록 점수에 크게 반영되고, 베이스/보조 성분이 비슷한 정도는 30%만 반영된다.
- `GET /products/{id}` 상세 응답에는 이 기준으로 계산한 `key_ingredients`(주요 성분)와, 50% 이상인 것만 자동으로 채운 `similar_products`가 같이 내려간다. 기준을 직접 조절하려면 `GET /products/{id}/similar?top_k=&min_score=&limit=`을 쓴다.
- 구현: `app/similarity.py`. `key_ingredients` 계산(`app/routers/products.py`)도 같은 `DEFAULT_TOP_K` 상수를 공유해서, "주요 성분"의 정의가 두 곳에서 어긋나지 않는다.

## 피부 타입별 적합도

큰 흐름: 피부 타입 → 피부 고민 → 필요한 성분 기능 → 실제 제품 성분 → 적합도 점수 → 추천.

- `ingredient_skin_score` 테이블에 성분마다 지성/복합성/건성/민감성 4개 피부 타입 각각에 대한 점수(-3~+3), 기능(Humectant/Occlusive/Emollient 등), 근거 수준(`evidence_level`), 출처(`source`), 주의사항(`caution`)을 저장한다.
- 제품 적합도 = 그 제품 전성분 중 점수 데이터가 있는 성분들의 점수를 모두 더한 뒤, 매칭된 성분 개수 기준 이론적 최대/최솟값(±3×매칭개수) 구간에서 0~100점으로 정규화한 값 (50점 = 중립). 예: 나이아신아마이드(+3)·하이알루로닉애씨드(+1)만 매칭된 제품의 지성 적합도 = 83.3점.
- `GET /products/{id}/skin-fit`은 4개 타입 전부, `?skin_type=건성`처럼 지정하면 하나만 반환하며, 어떤 성분이 점수에 기여했는지 `breakdown`으로 같이 내려준다.
- 구현: `app/skin_fit.py` (계산 로직), `app/models/ingredient_skin_score.py` (스키마), `scripts/seed_ingredient_skin_scores.py` (시드 데이터).
- ⚠️ **시드 데이터는 설계 단계 예시 점수다.** 57개 성분에 대해 채워져 있고, `evidence_level`/`source`로 근거 수준을 성분마다 구분해뒀다:
  - `D` + AAD — aad.org의 "피부타입별 보습제 고르는 법" 페이지에서 실제로 이름을 명시한 8종(하이알루로닉애씨드·소듐하이알루로네이트·글리세린·미네랄오일·페트롤라텀·다이메티콘·락틱애씨드·호호바씨오일·시어버터)
  - `D` + DermNet — dermnetnz.org의 humectant/occlusive/emollient 성분 분류를 따른 항목
  - `D` + 대한화장품협회 — 향료·에탄올
  - `E` + 화장품 성분과학 컨센서스 — 나머지(펩타이드, 병풀 유도체, 비타민C 유도체, 점증제 등). 개별 문헌으로 검증한 게 아니라 일반적으로 합의된 성분 기능을 바탕으로 만든 예시 점수라, 실제 서비스에 쓰려면 문헌(PubMed 등) 재검토가 필요하다.
  - 나머지 22,000여 개 성분은 매칭되는 점수가 없어 적합도 계산에서 그냥 빠진다.

## 제품 카테고리 분류

DB에 카테고리 컬럼(`product.category`)이 있지만, 값 자체는 제품명 키워드로 판정한다 — 제품 생성 시(`POST /products`) 한 번 계산해서 저장하고, 이후에는 필터링(`GET /products?category=`)에 그대로 쓴다.

- 스킨케어 루틴 순서를 그대로 반영: **스킨/토너**(1) → **세럼/에센스/앰플**(2) → **크림**(3) → 어디에도 안 걸리면 **기타**(99).
- 키워드 검사 순서에 주의: "스킨"은 "스킨1004"처럼 브랜드명에도 흔히 들어가서, 세럼/에센스/앰플·크림처럼 더 명확한 키워드를 먼저 확인한 뒤 스킨/토너는 맨 마지막에 확인한다. (순서를 안 지키면 "스킨1004 ... 앰플" 제품이 토너로 잘못 분류된다.)
- 구현: `app/product_category.py`. `classify()`는 제품 생성/백필 때 이름으로 분류할 때, `get_info()`는 이미 저장된 `category` 값에서 순서·설명 문구(`category_order`, `category_description`)를 다시 찾아올 때 쓴다 — 매번 제품명을 재분류하지 않고 저장된 값을 기준으로 하기 위함.
