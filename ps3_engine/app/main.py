from fastapi import FastAPI
from .api import router

app = FastAPI(
    title="IncuBrix PS3 – Script‑to‑B‑roll Video Engine",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs"
)

# Top‑level health check without API prefix
@app.get("/health", summary="Health check")
async def health_check_root():
    return {"status": "healthy"}

app.include_router(router, prefix="/api/v1")
