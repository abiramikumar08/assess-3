from fastapi import APIRouter, HTTPException, BackgroundTasks
from .jobs import queue, get_redis, process_job
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Literal

router = APIRouter()

class JobRequest(BaseModel):
    audio_url: Optional[HttpUrl] = Field(default=None, description='URL to an audio file (mp3, wav, m4a) – ≤10 min')
    script: Optional[str] = Field(default=None, description='Plain‑text script to be narrated')
    scenes: Optional[List[dict]] = Field(default=None, description='Optional IncuBrix scene list [{text, visual_hint}]')
    voice: Optional[str] = Field(default="en-US", description='TTS voice identifier (used when script is supplied)')
    aspect_ratios: Optional[List[Literal["16:9", "9:16", "1:1"]]] = Field(default=["16:9"], description='Requested output ratios')
    style: Optional[str] = Field(default='bright, modern, real‑world footage')
    avoid: Optional[List[str]] = Field(default=None, description="Content to avoid (e.g. faces, alcohol)")
    captions: Optional[dict] = Field(default={"burn_in": True, "srt": True})

@router.get("/health", summary="Health check")
async def health_check():
    """Simple health endpoint used by the integration standard."""
    return {"status": "healthy"}

@router.post("/broll/jobs", status_code=202, summary="Create B‑roll job (stub)")
async def create_job(request: JobRequest, background_tasks: BackgroundTasks):
    """Validate that at least one of the supported inputs is supplied.
    The actual background processing is not implemented yet – this is a stub.
    """
    if not (request.audio_url or request.script or request.scenes):
        raise HTTPException(
            status_code=422,
            detail="At least one of 'audio_url', 'script', or 'scenes' must be provided."
        )
    # Enqueue background job and return its ID
    job = queue.enqueue(process_job, request.dict())
    return {"job_id": job.get_id(), "status": "queued"}

@router.get("/broll/jobs/{job_id}", summary="Get job status")
async def get_job_status(job_id: str):
    from rq.job import Job
    try:
        job = Job.fetch(job_id, connection=get_redis())
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.is_queued:
        status = "queued"
    elif job.is_started:
        status = "processing"
    elif job.is_finished:
        status = "completed"
    elif job.is_failed:
        status = "failed"
    else:
        status = "unknown"
    return {"job_id": job_id, "status": status, "result": job.result if job.is_finished else None}

