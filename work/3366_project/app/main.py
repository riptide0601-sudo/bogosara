import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import fuzzy_match
from app.database import SessionLocal
from app.llm_client import warm_up
from app.routers import ingredients, ocr, products, purposes

app = FastAPI(title="LabelLens API")

app.include_router(products.router)
app.include_router(ingredients.router)
app.include_router(purposes.router)
app.include_router(ocr.router)


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
