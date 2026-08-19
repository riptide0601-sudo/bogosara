# LabelLens API

`LabelLens_ERD_v7.md` 스키마를 그대로 구현한 FastAPI 백엔드입니다. `data/labellens.db`(SQLite)에 실제 제품·성분 데이터가 들어있습니다.

## 로컬 실행 (개발용)

```bash
# 1. 가상환경 및 의존성 설치
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt

# 2. .env 생성
copy .env.example .env

# 3. 서버 실행
uvicorn app.main:app --reload
```

실행 후 http://127.0.0.1:8000 에서 검색 프론트엔드를, http://127.0.0.1:8000/docs 에서 API 문서를 확인할 수 있습니다.

"쉬운 설명 생성"(`/ingredients/{id}/generate-summary`) 기능을 쓰려면 로컬에 [Ollama](https://ollama.com)를 설치하고 `ollama pull gemma2:2b` 후 `ollama serve`로 띄워둬야 합니다. 없어도 나머지 기능은 정상 동작합니다.

## Docker로 배포

```bash
docker compose up -d --build
```

`app`(FastAPI, 포트 8000)과 `ollama`(gemma2:2b, 포트 11434) 두 컨테이너가 함께 뜨고, `ollama` 컨테이너가 최초 기동 시 모델을 자동으로 pull합니다(최초 1회는 다운로드 시간이 걸립니다). `data/` 폴더는 볼륨으로 마운트되어 있어 컨테이너를 내려도 DB가 유지됩니다.

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
  labellens.db # SQLite DB (실데이터)
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
