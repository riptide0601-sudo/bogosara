#!/usr/bin/env bash
# 로컬 실행 스크립트. PostgreSQL은 미리 띄워져 있어야 합니다
# (README.md "PostgreSQL 기동" 섹션의 방법 A(docker compose up -d db) 또는 방법 B 참고).
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    echo "[run.sh] .venv 없음 — 새로 생성합니다"
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

if [ ! -f .env ]; then
    echo "[run.sh] .env 없음 — .env.example을 복사합니다"
    cp .env.example .env
fi

echo "[run.sh] http://127.0.0.1:8000 에서 검색 프론트엔드, /docs 에서 API 문서 확인 가능"
exec uvicorn app.main:app --reload
