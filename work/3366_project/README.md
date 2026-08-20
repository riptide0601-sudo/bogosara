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

## 주요 엔드포인트

- `POST /products`, `GET /products?query=`, `GET /products/{id}` (성분·목적·LLM요약까지 포함한 상세 조회)
- `PUT /products/{id}/ingredients` — 상품에 성분 매칭 결과 연결 (중복은 `ON CONFLICT DO NOTHING`으로 무시)
- `POST /ingredients`, `GET /ingredients?query=` (name_kr/name_en/synonyms 검색, 배합목적 포함), `GET /ingredients/{id}`
- `PUT /ingredients/{id}/purposes/{purpose_id}` — 성분에 배합목적 연결
- `GET|PUT /ingredients/{id}/llm-summary` — 좋은 점/주의할 점 등 조회·수정
- `POST /ingredients/{id}/generate-summary` — 배합목적 설명을 gemma로 쉬운 문장으로 재작성
- `POST /purposes`, `GET /purposes`
