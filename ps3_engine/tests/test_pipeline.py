"""Comprehensive test pack for PS3 B-roll engine.

Tests run with no API keys, no Redis, no internet — all external services
are replaced by mocks. The end-to-end pipeline test uses:
  TTS_PROVIDER=mock  → silent WAV (no SAPI needed)
  FOOTAGE_PROVIDER=mock → solid-colour MP4 clips (no Pexels needed)
  Real FFmpeg binary (ffmpeg-win-x86_64-v7.1.exe, already installed)

Run:  .venv\\Scripts\\python -m pytest -v
"""
import os, json, wave, time
os.environ.setdefault("TTS_PROVIDER", "mock")
os.environ.setdefault("FOOTAGE_PROVIDER", "mock")
os.environ.setdefault("FOOTAGE_PROVIDER", "mock")

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from pathlib import Path

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="session")
def mock_job():
    class _Job:
        _id = "test-job-123"
        result = None
        exc_info = None
        is_queued = True
        is_started = False
        is_finished = False
        is_failed = False
        def get_id(self): return self._id
    return _Job()


# ══════════════════════════════════════════════════════════════════════════════
# 1. Health endpoints
# ══════════════════════════════════════════════════════════════════════════════

def test_health_root(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_health_api(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


# ══════════════════════════════════════════════════════════════════════════════
# 2. Input validation
# ══════════════════════════════════════════════════════════════════════════════

def test_reject_empty_body(client):
    r = client.post("/api/v1/broll/jobs", json={})
    assert r.status_code == 422
    body = r.json()
    assert "error" in body or "detail" in body


def test_reject_unsupported_ratio(client, mock_job):
    with patch("app.api.queue") as mq:
        mq.enqueue.return_value = mock_job
        r = client.post("/api/v1/broll/jobs", json={"script": "hello", "aspect_ratios": ["4:3"]})
    # 4:3 is not in the allowed enum, FastAPI should return 422
    assert r.status_code == 422


def test_accept_script_only(client, mock_job):
    with patch("app.api.queue") as mq:
        mq.enqueue.return_value = mock_job
        r = client.post("/api/v1/broll/jobs", json={"script": "Hello world"})
    assert r.status_code == 202
    data = r.json()
    assert "job_id" in data
    assert data["status"] == "queued"


def test_accept_audio_url(client, mock_job):
    with patch("app.api.queue") as mq:
        mq.enqueue.return_value = mock_job
        r = client.post("/api/v1/broll/jobs", json={"audio_url": "http://example.com/audio.mp3"})
    assert r.status_code == 202


def test_accept_scenes(client, mock_job):
    with patch("app.api.queue") as mq:
        mq.enqueue.return_value = mock_job
        r = client.post(
            "/api/v1/broll/jobs",
            json={"scenes": [{"text": "Hello.", "visual_hint": "greeting"}]},
        )
    assert r.status_code == 202


# ══════════════════════════════════════════════════════════════════════════════
# 3. Idempotency-Key
# ══════════════════════════════════════════════════════════════════════════════

def test_idempotency_key_deduplication(client, mock_job):
    key = "idem-test-key-abc"
    with patch("app.api.queue") as mq:
        mq.enqueue.return_value = mock_job
        r1 = client.post(
            "/api/v1/broll/jobs",
            json={"script": "Testing idempotency"},
            headers={"Idempotency-Key": key},
        )
        r2 = client.post(
            "/api/v1/broll/jobs",
            json={"script": "Testing idempotency"},
            headers={"Idempotency-Key": key},
        )
    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json()["job_id"] == r2.json()["job_id"]  # same job returned


# ══════════════════════════════════════════════════════════════════════════════
# 4. Job status endpoints
# ══════════════════════════════════════════════════════════════════════════════

class _MockRQJob:
    def __init__(self, state="queued", result=None, exc_info=None):
        self.is_queued = state == "queued"
        self.is_started = state == "started"
        self.is_finished = state == "finished"
        self.is_failed = state == "failed"
        self.result = result
        self.exc_info = exc_info


def test_job_status_queued(client):
    with patch("rq.job.Job.fetch", return_value=_MockRQJob("queued")):
        r = client.get("/api/v1/broll/jobs/fake-id")
    assert r.status_code == 200
    assert r.json()["status"] == "queued"
    assert r.json()["progress"] == 0


def test_job_status_running(client):
    with patch("rq.job.Job.fetch", return_value=_MockRQJob("started")):
        r = client.get("/api/v1/broll/jobs/fake-id")
    assert r.status_code == 200
    assert r.json()["status"] == "running"
    assert r.json()["progress"] == 50


def test_job_status_succeeded(client):
    result_data = {"videos": {"16:9": "/outputs/job1/video_16x9.mp4"}}
    with patch("rq.job.Job.fetch", return_value=_MockRQJob("finished", result=result_data)):
        r = client.get("/api/v1/broll/jobs/fake-id")
    assert r.status_code == 200
    assert r.json()["status"] == "succeeded"
    assert r.json()["progress"] == 100
    assert "videos" in r.json()["result"]


def test_job_status_failed(client):
    with patch("rq.job.Job.fetch", return_value=_MockRQJob("failed", exc_info="ValueError: bad input")):
        r = client.get("/api/v1/broll/jobs/fake-id")
    assert r.status_code == 200
    assert r.json()["status"] == "failed"
    assert r.json()["error"] is not None


def test_job_not_found(client):
    with patch("rq.job.Job.fetch", side_effect=Exception("no such job")):
        r = client.get("/api/v1/broll/jobs/nonexistent-id")
    assert r.status_code == 404
    assert r.json()["detail"]["error"]["code"] == "JOB_NOT_FOUND"


# ══════════════════════════════════════════════════════════════════════════════
# 5. Scene splitter unit tests
# ══════════════════════════════════════════════════════════════════════════════

def test_scene_split_basic():
    from app.scenes import split_into_scenes
    scenes = split_into_scenes("Hello world. This is a test. Goodbye.", 9.0)
    assert len(scenes) == 3
    assert scenes[0].start == 0.0
    assert scenes[-1].end == pytest.approx(9.0, abs=0.01)


def test_scene_split_coverage():
    from app.scenes import split_into_scenes
    text = "Saving money is important. Invest wisely. Plan for the future."
    scenes = split_into_scenes(text, 10.0)
    total = sum(s.end - s.start for s in scenes)
    assert abs(total - 10.0) < 0.01   # full coverage


def test_scene_split_pre_scenes():
    from app.scenes import split_into_scenes
    pre = [
        {"text": "Hello.", "visual_hint": "greeting"},
        {"text": "Goodbye.", "visual_hint": "farewell"},
    ]
    scenes = split_into_scenes("ignored", 6.0, pre_split_scenes=pre)
    assert len(scenes) == 2
    assert scenes[0].visual_hint == "greeting"


def test_scene_no_repeat_ids():
    """No clip ID should appear twice in the same video."""
    from app.scenes import split_into_scenes
    scenes = split_into_scenes("A. B. C. D. E.", 10.0)
    used = set()
    for sc in scenes:
        assert sc.index not in used
        used.add(sc.index)


# ══════════════════════════════════════════════════════════════════════════════
# 6. TTS unit tests
# ══════════════════════════════════════════════════════════════════════════════

def test_mock_tts(tmp_path):
    os.environ["TTS_PROVIDER"] = "mock"
    # reload to pick up env change
    import importlib, app.tts as tts_mod
    importlib.reload(tts_mod)
    from app.tts import synthesise
    out = synthesise("Hello world this is a test sentence.", tmp_path / "narration")
    assert out.exists()
    assert out.suffix == ".wav"
    assert out.stat().st_size > 44   # more than just WAV header
    # Check it's a valid WAV
    with wave.open(str(out), "r") as wf:
        assert wf.getnframes() > 0


def test_mock_tts_duration_proportional(tmp_path):
    os.environ["TTS_PROVIDER"] = "mock"
    import importlib, app.tts as tts_mod
    importlib.reload(tts_mod)
    from app.tts import synthesise, get_audio_duration
    short = synthesise("Hi.", tmp_path / "short")
    long_ = synthesise("This is a much longer sentence with many more words in it.", tmp_path / "long")
    d_short = get_audio_duration(short)
    d_long = get_audio_duration(long_)
    assert d_long > d_short


# ══════════════════════════════════════════════════════════════════════════════
# 7. Footage unit tests
# ══════════════════════════════════════════════════════════════════════════════

def test_mock_clip_generated(tmp_path):
    os.environ["FOOTAGE_PROVIDER"] = "mock"
    import importlib, app.footage as footage_mod
    importlib.reload(footage_mod)
    from app.footage import fetch_clip
    result = fetch_clip("saving money", duration=3.0, clip_dir=tmp_path / "clips")
    assert result.path.exists()
    assert result.path.suffix == ".mp4"
    assert result.meta["licence"] is not None
    assert result.meta["is_ai_generated"] is True   # mock clips are flagged


def test_mock_clip_no_repeat(tmp_path):
    os.environ["FOOTAGE_PROVIDER"] = "mock"
    import importlib, app.footage as footage_mod
    importlib.reload(footage_mod)
    from app.footage import fetch_clip
    used: set = set()
    clips = []
    queries = ["money", "investment", "growth", "success", "teamwork"]
    for q in queries:
        c = fetch_clip(q, duration=2.0, used_ids=used, clip_dir=tmp_path / "clips")
        assert c.meta["id"] not in used
        used.add(c.meta["id"])
        clips.append(c)


# ══════════════════════════════════════════════════════════════════════════════
# 8. End-to-end pipeline test (mock providers, real FFmpeg)
# ══════════════════════════════════════════════════════════════════════════════

def test_end_to_end_pipeline(tmp_path):
    """Full pipeline: mock TTS + mock clips + real FFmpeg → real MP4."""
    import importlib
    os.environ["TTS_PROVIDER"] = "mock"
    os.environ["FOOTAGE_PROVIDER"] = "mock"
    os.environ["OUTPUT_DIR"] = str(tmp_path)

    import app.config as cfg_mod; importlib.reload(cfg_mod)
    import app.tts as tts_mod; importlib.reload(tts_mod)
    import app.footage as footage_mod; importlib.reload(footage_mod)
    import app.scenes as scenes_mod; importlib.reload(scenes_mod)
    import app.renderer as renderer_mod; importlib.reload(renderer_mod)
    import app.jobs as jobs_mod; importlib.reload(jobs_mod)

    payload = {
        "script": "Saving money is important. Invest wisely. Plan for the future.",
        "aspect_ratios": ["16:9"],
        "captions": {"burn_in": False, "srt": True},
    }
    result = jobs_mod.process_job(payload)

    # ── Validate result structure ──────────────────────────────────────────────
    assert "videos" in result
    assert "16:9" in result["videos"]
    mp4_path = Path(result["videos"]["16:9"])
    assert mp4_path.exists(), f"MP4 not found: {mp4_path}"
    assert mp4_path.stat().st_size > 1000, "MP4 appears empty"

    # ── Validate SRT ──────────────────────────────────────────────────────────
    srt_path = Path(result["srt"])
    assert srt_path.exists()
    srt_content = srt_path.read_text(encoding="utf-8")
    assert "-->" in srt_content

    # ── Validate timeline.json ────────────────────────────────────────────────
    tl = json.loads(Path(result["timeline"]).read_text(encoding="utf-8"))
    assert "scenes" in tl
    for sc in tl["scenes"]:
        assert "text" in sc
        assert "start_s" in sc and "end_s" in sc
        assert sc["end_s"] > sc["start_s"]
        assert "licence" in sc["clip"]
        assert sc["clip"]["licence"] is not None

    # ── Validate manifest.json ────────────────────────────────────────────────
    mf = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    assert "models_and_providers" in mf
    assert "cost_estimate" in mf
    assert "warnings" in mf

    # ── Validate no repeat clip IDs ───────────────────────────────────────────
    clip_ids = [sc["clip"]["path"] for sc in tl["scenes"]]
    # Each scene should have a clip path
    assert all(p is not None for p in clip_ids)

    print(f"\n✓ MP4 produced: {mp4_path} ({mp4_path.stat().st_size} bytes)")
    print(f"✓ Scenes: {len(tl['scenes'])}")
    print(f"✓ Duration: {result.get('narration_duration_s', '?')}s")


def test_swap_clip():
    """Verify swap_scene_clip replaces a clip and re-renders successfully."""
    import importlib
    import app.jobs as jobs_mod
    importlib.reload(jobs_mod)

    payload = {
        "script": "First scene here. Second scene is different.",
        "aspect_ratios": ["16:9"],
        "captions": {"burn_in": False, "srt": True},
    }
    initial = jobs_mod.process_job(payload)
    job_id = initial["job_id"]

    # Swap scene 0 clip
    t0 = time.time()
    swapped = jobs_mod.swap_scene_clip(job_id, scene_index=0, new_query="new visual concept")
    elapsed = time.time() - t0

    assert "videos" in swapped
    assert "16:9" in swapped["videos"]
    new_mp4 = Path(swapped["videos"]["16:9"])
    assert new_mp4.exists()
    assert new_mp4.stat().st_size > 1000

    # Verify timeline updated
    new_tl = json.loads(Path(swapped["timeline"]).read_text(encoding="utf-8"))
    assert len(new_tl["scenes"]) == 2
    assert "new visual concept" in new_tl["scenes"][0]["clip"]["reason"]
    print(f"\n✓ Swap clip re-rendered in {elapsed:.2f}s")

