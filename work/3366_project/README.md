# LabelLens API

`LabelLens_ERD_v7.md` 스키마를 그대로 구현한 FastAPI 백엔드입니다.

## 실행 방법

```bash
# 1. DB 실행 (PostgreSQL)
docker compose up -d

# 2. 가상환경 및 의존성 설치
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt

# 3. .env 생성
copy .env.example .env

# 4. 마이그레이션 적용
alembic upgrade head

# 5. 서버 실행
uvicorn app.main:app --reload
```

실행 후 http://127.0.0.1:8000/docs 에서 API 문서를 확인할 수 있습니다.

## 구조

```
app/
  models/      # SQLAlchemy 모델 (ERD 테이블과 1:1)
  schemas/     # Pydantic 스키마
  routers/     # products / ingredients / purposes 엔드포인트
  database.py  # 엔진, 세션
  config.py    # 환경변수 설정
  main.py      # FastAPI 앱 엔트리포인트
alembic/       # DB 마이그레이션
```

## 주요 엔드포인트

- `POST /products`, `GET /products`, `GET /products/{id}` (성분·목적·LLM요약까지 포함한 상세 조회)
- `PUT /products/{id}/ingredients` — 상품에 성분 매칭 결과 연결 (중복은 `ON CONFLICT DO NOTHING`으로 무시)
- `POST /ingredients`, `GET /ingredients?query=` (name_kr/name_en/synonyms 검색), `GET /ingredients/{id}`
- `PUT /ingredients/{id}/purposes/{purpose_id}` — 성분에 배합목적 연결
- `GET|PUT /ingredients/{id}/llm-summary`
- `POST /purposes`, `GET /purposes`
