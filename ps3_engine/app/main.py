"""FastAPI application entry point."""
import logging, json, os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api import router

# Structured JSON logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
)

app = FastAPI(
    title="IncuBrix PS3 — Script-to-B-roll Video Engine",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
)

# Top-level health (no prefix) + Integration Standard health
@app.get("/health", summary="Liveness check", tags=["health"])
async def health_root():
    return {"status": "healthy"}

@app.get("/ready", summary="Readiness check", tags=["health"])
async def ready_root():
    from app.jobs import get_redis
    try:
        get_redis().ping()
        return {"status": "ready", "redis": "ok"}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "REDIS_UNAVAILABLE", "message": str(exc), "retryable": True}},
        )

app.include_router(router, prefix="/api/v1", tags=["broll"])
