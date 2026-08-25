import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import fuzzy_match
from app.database import SessionLocal
from app.llm_client import warm_up
from app.routers import auth, ingredients, ocr, products, purposes, users

app = FastAPI(title="LabelLens API")

# 로컬 개발용 — 프론트(Vite dev server)가 다른 포트에서 API를 호출할 수 있게 허용.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(ingredients.router)
app.include_router(purposes.router)
app.include_router(ocr.router)
app.include_router(auth.router)
app.include_router(users.router)


@app.on_event("startup")
def _warm_up_llm():
    try:
        warm_up()
    except Exception:
        logging.getLogger(__name__).warning("Ollama warm-up failed; LLM features may be slow on first use")


@app.on_event("startup")
def _build_fuzzy_match_cache():
    db = SessionLocal()
    try:
        fuzzy_match.build_cache(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
