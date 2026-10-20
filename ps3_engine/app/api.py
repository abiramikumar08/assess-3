"""FastAPI router — IncuBrix PS3 B-roll engine API.

All routes live under /api/v1/ (mounted in main.py).
Follows the IncuBrix Integration Standard:
  • 202 + job_id for slow operations (IS-3)
  • Idempotency-Key header deduplication (IS-4)
  • Structured JSON errors (IS-5)
  • Structured JSON logs with correlation ID (IS-8)
"""
from __future__ import annotations
import json, logging, os, uuid
from typing import List, Optional, Literal

from fastapi import APIRouter, Header, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, HttpUrl, Field

from app.jobs import queue, get_redis

log = logging.getLogger(__name__)
router = APIRouter()

# ── In-memory idempotency store (replace with Redis in production) ────────────
_idempotency: dict[str, dict] = {}


# ─── Models ───────────────────────────────────────────────────────────────────

class CaptionOptions(BaseModel):
    burn_in: bool = True
    srt: bool = True


class JobRequest(BaseModel):
    audio_url: Optional[str] = Field(
        default=None,
        description="URL to an audio file (mp3, wav, m4a) — ≤10 min",
    )
    script: Optional[str] = Field(
        default=None,
        description="Plain-text script to be narrated via TTS",
    )
    scenes: Optional[List[dict]] = Field(
        default=None,
        description='IncuBrix scene list: [{"text": "...", "visual_hint": "..."}]',
    )
    voice: Optional[str] = Field(default="en-US", description="TTS voice identifier")
    aspect_ratios: Optional[List[Literal["16:9", "9:16", "1:1"]]] = Field(
        default=["16:9"], description="Requested output aspect ratios",
    )
    style: Optional[str] = Field(default="bright, modern, real-world footage")
    avoid: Optional[List[str]] = Field(
        default=None, description="Content tags to avoid (e.g. faces, alcohol)",
    )
    captions: Optional[CaptionOptions] = Field(
        default_factory=CaptionOptions,
    )
    callback_url: Optional[str] = Field(
        default=None, description="Webhook URL for job completion notification",
    )


def _error(code: str, message: str, retryable: bool = False, details: dict | None = None):
    return {"error": {"code": code, "message": message, "retryable": retryable, "details": details or {}}}


# ─── Health endpoints ─────────────────────────────────────────────────────────

@router.get("/health", summary="Liveness check")
async def health():
    return {"status": "healthy"}


@router.get("/ready", summary="Readiness check — verifies Redis connectivity")
async def ready():
    try:
        get_redis().ping()
        return {"status": "ready", "redis": "ok"}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=_error("REDIS_UNAVAILABLE", str(exc), retryable=True),
        )


# ─── Job submission ───────────────────────────────────────────────────────────

@router.post("/broll/jobs", status_code=202, summary="Submit a B-roll video job")
async def create_job(
    request: JobRequest,
    req: Request,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
):
    correlation_id = x_correlation_id or str(uuid.uuid4())
    log.info(json.dumps({
        "event": "job_submitted", "correlation_id": correlation_id,
        "has_script": bool(request.script),
        "has_audio_url": bool(request.audio_url),
        "has_scenes": bool(request.scenes),
    }))

    # Validate — at least one input must be supplied
    if not (request.audio_url or request.script or request.scenes):
        raise HTTPException(
            status_code=422,
            detail=_error(
                "INVALID_INPUT",
                "At least one of 'audio_url', 'script', or 'scenes' must be provided.",
            ),
        )

    # Idempotency: return existing job if same key already used
    if idempotency_key and idempotency_key in _idempotency:
        return _idempotency[idempotency_key]

    # Enqueue (raises ConnectionError if Redis is down — no silent fallback)
    try:
        job = queue.enqueue(request.model_dump())
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=_error("QUEUE_UNAVAILABLE", str(exc), retryable=True),
        )

    response = {
        "job_id": job.get_id(),
        "status": "queued",
        "correlation_id": correlation_id,
    }
    if idempotency_key:
        _idempotency[idempotency_key] = response
    return response


class SwapClipRequest(BaseModel):
    scene_index: int
    new_query: Optional[str] = None


# ─── Job status ───────────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}", summary="Get job status and result links")
@router.get("/broll/jobs/{job_id}", summary="Get job status and result links")
async def get_job_status(
    job_id: str,
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
):
    from rq.job import Job
    try:
        job = Job.fetch(job_id, connection=get_redis())
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=_error("JOB_NOT_FOUND", f"No job with id {job_id!r}"),
        )

    if job.is_queued:
        status, progress = "queued", 0
    elif job.is_started:
        status, progress = "running", 50
    elif job.is_finished:
        status, progress = "succeeded", 100
    elif job.is_failed:
        status, progress = "failed", 0
    else:
        status, progress = "unknown", 0

    return {
        "job_id": job_id,
        "status": status,
        "progress": progress,
        "result": job.result if job.is_finished else None,
        "error": str(job.exc_info) if job.is_failed else None,
    }


# ─── Swap clip (Advanced level) ──────────────────────────────────────────────

@router.post("/jobs/{job_id}/swap-clip", summary="Swap scene clip and re-render affected parts")
@router.post("/broll/jobs/{job_id}/swap-clip", summary="Swap scene clip and re-render affected parts")
async def swap_clip_endpoint(
    job_id: str,
    request: SwapClipRequest,
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
):
    from app.jobs import swap_scene_clip
    try:
        result = swap_scene_clip(job_id, request.scene_index, request.new_query)
        return result
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=_error("JOB_NOT_FOUND", str(exc)),
        )
    except IndexError as exc:
        raise HTTPException(
            status_code=400,
            detail=_error("INVALID_SCENE_INDEX", str(exc)),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=_error("SWAP_FAILED", str(exc)),
        )
