# IncuBrix Script-to-B-Roll Video Engine (`ps3_engine`)

An asynchronous microservice that transforms plain-text scripts or voiceover audio URLs into finished, licence-clean, commercial-ready B-roll videos across multiple aspect ratios (`16:9`, `9:16`, `1:1`).

Built for **IncuBrix Engineering Assessment 3**.

---

## Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │              Client / Caller           │
                      └───────────────────┬────────────────────┘
                                          │ POST /api/v1/broll/jobs
                                          ▼ (Idempotency-Key header)
                      ┌────────────────────────────────────────┐
                      │          FastAPI Gateway               │
                      │  - Input validation (Pydantic)         │
                      │  - Idempotent deduplication            │
                      │  - Structured JSON error handler       │
                      └───────────────────┬────────────────────┘
                                          │ Enqueue Job
                                          ▼
                      ┌────────────────────────────────────────┐
                      │             Redis & RQ Queue           │
                      └───────────────────┬────────────────────┘
                                          │ Dequeue
                                          ▼
                      ┌────────────────────────────────────────┐
                      │           Background Worker            │
                      │                                        │
                      │  1. Audio Ingestion / TTS Synthesis    │
                      │     (SAPI / Synthetic Offline Mock)    │
                      │                                        │
                      │  2. Semantic Scene Segmentation        │
                      │     (Punctuation-aware: 1.5s - 7.0s)   │
                      │                                        │
                      │  3. Footage Acquisition & Deduplication│
                      │     (Pexels API -> Offline Fallback)   │
                      │                                        │
                      │  4. FFmpeg Single-Pass Render Engine   │
                      │     (H.264 / AAC / 30fps / Subtitles)  │
                      └───────────────────┬────────────────────┘
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   ▼                                             ▼
        ┌─────────────────────┐                       ┌─────────────────────┐
        │    Video Assets     │                       │     Provenance      │
        │  video_16x9.mp4     │                       │  timeline.json      │
        │  video_9x16.mp4     │                       │  manifest.json      │
        │  video_1x1.mp4      │                       │  captions.srt       │
        └─────────────────────┘                       └─────────────────────┘
```

---

## Quick Start (Under 10 Commands)

### 1. Using Docker Compose (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/abiramikumar08/assess-3.git
cd assess-3/ps3_engine

# 2. Configure environment (defaults work out of the box with zero API keys)
cp .env.example .env

# 3. Start Redis, API, and Worker services
docker compose up -d

# 4. Verify service health
curl http://localhost:8000/health
```

### 2. Local Setup (Python 3.11–3.13)

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run all tests (unit, integration, and end-to-end pipeline with zero API keys)
python -m pytest -v

# 4. Start local API server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Running the Batch Runner (Integration Standard 10)

The batch runner executes a folder or file of test inputs against the API or directly in-process, outputting all videos, SRT files, and provenance metadata into a designated target directory.

```bash
# Direct in-process batch execution
python batch_runner.py --input test_inputs --output test_pack --direct

# Via live HTTP server
python batch_runner.py --input test_inputs --output test_pack --api-url http://localhost:8000
```

---

## API Contract

All endpoints follow the **IncuBrix Integration Standard**:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service liveness probe (`{"status": "healthy"}`) |
| `GET` | `/ready` | Service readiness probe (checks Redis connectivity) |
| `POST` | `/api/v1/broll/jobs` | Submit asynchronous video generation job (HTTP 202) |
| `GET` | `/api/v1/jobs/{job_id}` | Retrieve job status, progress (0–100%), and result artifact URLs |

### Submit Video Job

```http
POST /api/v1/broll/jobs HTTP/1.1
Content-Type: application/json
Idempotency-Key: sample-request-uuid-101

{
  "script": "Managing your personal finances starts with tracking daily expenses. Consistent investing compounds into financial freedom.",
  "aspect_ratios": ["16:9", "9:16"],
  "captions": {
    "burn_in": false,
    "srt": true
  },
  "style": "clean, corporate, modern finance",
  "avoid": ["people's faces", "alcohol"]
}
```

**Response (HTTP 202 Accepted):**

```json
{
  "job_id": "3004d8ce-276e-4b65-959c-383f5cc8fc77",
  "status": "queued",
  "created_at": "2026-10-20T19:30:00Z",
  "status_url": "/api/v1/jobs/3004d8ce-276e-4b65-959c-383f5cc8fc77"
}
```

---

## Standard Error Codes

All errors return JSON in standard format: `{"error": {"code": "...", "message": "...", "retryable": bool, "details": {}}}`

| Error Code | HTTP Status | Retryable | Description |
| :--- | :--- | :--- | :--- |
| `INVALID_INPUT` | 400 | False | Missing input (neither script nor audio provided) or malformed payload. |
| `UNSUPPORTED_ASPECT_RATIO` | 400 | False | Aspect ratio not in `["16:9", "9:16", "1:1"]`. |
| `AUDIO_TOO_LONG` | 400 | False | Audio duration exceeds `MAX_AUDIO_SECONDS` (10 minutes). |
| `JOB_NOT_FOUND` | 404 | False | The requested `job_id` does not exist. |
| `QUEUE_ERROR` | 503 | True | Redis queue is temporarily unreachable. |
| `INTERNAL_ERROR` | 500 | True | Unhandled rendering or processing pipeline failure. |

---

## Configuration Settings

Configured exclusively via environment variables or `.env`:

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `OUTPUT_DIR` | `outputs` | Directory where rendered MP4s and manifests are saved. |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL for task queue. |
| `FOOTAGE_PROVIDER` | `mock` | Footage provider: `pexels` (requires key) or `mock` (offline synthetic). |
| `PEXELS_API_KEY` | `""` | Optional API key for Pexels commercial stock library. |
| `TTS_PROVIDER` | `mock` | Speech synthesizer: `sapi` (Windows offline) or `mock` (silent WAV). |
| `VIDEO_FPS` | `30` | Output frame rate. |
| `VIDEO_RESOLUTION_16_9` | `1280x720` | Output resolution for horizontal video. |
| `VIDEO_RESOLUTION_9_16` | `720x1280` | Output resolution for vertical video (Shorts/Reels). |
| `VIDEO_RESOLUTION_1_1` | `720x720` | Output resolution for square video. |
| `MAX_AUDIO_SECONDS` | `600` | Maximum narration length allowed (10 minutes). |
| `FFMPEG_BIN` | auto-detected | Path to FFmpeg binary (discovered dynamically). |

---

## Licence

All pipeline code is licensed under the MIT Licence. Sourced media from Pexels falls under the Pexels Commercial Free Licence. Generated synthetic test assets are Public Domain.
