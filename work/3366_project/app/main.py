from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import ingredients, products, purposes

app = FastAPI(title="LabelLens API")

app.include_router(products.router)
app.include_router(ingredients.router)
app.include_router(purposes.router)


@app.get("/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
