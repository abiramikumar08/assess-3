"""Background job processing — the real end-to-end pipeline.

States:  queued → processing → completed | failed

Pipeline steps:
  1. Validate input
  2. Download / generate narration audio
  3. Split into timed scenes
  4. Fetch one B-roll clip per scene (deduplicated)
  5. Render MP4(s) + captions + timeline + manifest
"""
from __future__ import annotations
import os, json, uuid, logging, tempfile, time
from pathlib import Path
from redis import Redis
from rq import Queue as RQQueue

from app.config import REDIS_URL, OUTPUT_DIR

log = logging.getLogger(__name__)


# ─── Redis / Queue ────────────────────────────────────────────────────────────

def get_redis() -> Redis:
    return Redis.from_url(REDIS_URL)


class JobQueue:
    """Thin wrapper: enqueue(payload) → job object.

    Raises ConnectionError clearly if Redis is unreachable — no silent fallback
    in production. In test mode (TTS_PROVIDER=mock, FOOTAGE_PROVIDER=mock) the
    queue.enqueue is monkey-patched by tests.
    """

    def __init__(self):
        self._redis: Redis | None = None
        self._q: RQQueue | None = None

    def _connect(self) -> RQQueue:
        if self._q is None:
            r = get_redis()
            r.ping()                       # raises ConnectionError if down
            self._q = RQQueue("broll", connection=r)
        return self._q

    def enqueue(self, payload: dict):
        q = self._connect()
        return q.enqueue(process_job, payload)


queue = JobQueue()


# ─── Main job function (executed by RQ worker) ─────────────────────────────────

def process_job(payload: dict) -> dict:
    """End-to-end pipeline: narration → scenes → clips → rendered video."""
    t0 = time.time()
    job_id = str(uuid.uuid4())
    warnings: list[str] = []

    script: str | None = payload.get("script")
    audio_url: str | None = payload.get("audio_url")
    scenes_input: list | None = payload.get("scenes")
    aspect_ratios: list[str] = payload.get("aspect_ratios") or ["16:9"]
    burn_captions: bool = (payload.get("captions") or {}).get("burn_in", True)
    srt: bool = (payload.get("captions") or {}).get("srt", True)

    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "payload.json").write_text(json.dumps(payload), encoding="utf-8")

    # ── Step 1: Narration audio ────────────────────────────────────────────────
    narration_path: Path
    if audio_url:
        narration_path = _download_audio(audio_url, job_dir / "narration")
        narration_text = script or ""
    elif script:
        from app.tts import synthesise
        narration_path = synthesise(script, job_dir / "narration")
        narration_text = script
    elif scenes_input:
        # Build script from scene texts
        narration_text = " ".join(s.get("text", "") for s in scenes_input)
        from app.tts import synthesise
        narration_path = synthesise(narration_text, job_dir / "narration")
    else:
        raise ValueError("INVALID_INPUT: at least one of audio_url, script or scenes is required")

    # ── Step 2: Get audio duration ─────────────────────────────────────────────
    from app.tts import get_audio_duration
    audio_dur = get_audio_duration(narration_path)
    log.info(f"[{job_id}] narration duration: {audio_dur:.1f}s")

    # ── Step 3: Scene splitting ────────────────────────────────────────────────
    from app.scenes import split_into_scenes
    scenes = split_into_scenes(
        text=narration_text or " ",
        audio_duration=audio_dur,
        pre_split_scenes=scenes_input,
    )
    if not scenes:
        raise RuntimeError("SCENE_SPLIT_FAILED: could not derive any scenes from input")

    # ── Step 4: Fetch clips (no repeats) ──────────────────────────────────────
    from app.footage import fetch_clip
    used_ids: set[str] = set()
    avoid: list[str] = payload.get("avoid") or []

    for sc in scenes:
        clip = fetch_clip(
            query=sc.visual_hint,
            duration=sc.end - sc.start,
            avoid=avoid,
            used_ids=used_ids,
            clip_dir=job_dir / "clips",
        )
        sc.clip_path = str(clip.path)
        sc.clip_meta = clip.meta
        sc.relevance_score = _rate_relevance(sc.visual_hint, clip.meta)
        used_ids.add(clip.meta["id"])

    # ── Step 5: Render ────────────────────────────────────────────────────────
    from app.renderer import render
    result = render(
        scenes=scenes,
        narration_path=narration_path,
        aspect_ratios=aspect_ratios,
        job_id=job_id,
        burn_captions=burn_captions,
        srt=srt,
        warnings=warnings,
    )

    result["elapsed_s"] = round(time.time() - t0, 2)
    result["narration_duration_s"] = audio_dur
    log.info(f"[{job_id}] completed in {result['elapsed_s']}s")
    return result


# ─── helpers ──────────────────────────────────────────────────────────────────

def _download_audio(url: str, dest: Path) -> Path:
    """Download audio from URL; supports mp3, wav, m4a up to 10 min."""
    import urllib.request
    suffix = Path(url.split("?")[0]).suffix or ".mp3"
    path = dest.with_suffix(suffix)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = resp.read(600 * 320_000)   # ≤ 10 min @ 320 kbps
        path.write_bytes(data)
    except Exception as exc:
        raise RuntimeError(f"AUDIO_DOWNLOAD_FAILED: {exc}")
    return path


def _rate_relevance(hint: str, meta: dict) -> float:
    """Assign a heuristic relevance score 1–5 based on source."""
    if meta.get("source") == "mock":
        return 2.0    # mock clips are low-relevance by definition
    return 3.5        # Pexels clips rated conservatively until human review


def swap_scene_clip(job_id: str, scene_index: int, new_query: Optional[str] = None) -> dict:
    """Swap one scene's clip and re-render only the affected parts."""
    job_dir = OUTPUT_DIR / job_id
    tl_path = job_dir / "timeline.json"
    if not tl_path.exists():
        raise FileNotFoundError(f"Job {job_id} timeline not found")

    payload = {}
    if (job_dir / "payload.json").exists():
        payload = json.loads((job_dir / "payload.json").read_text(encoding="utf-8"))

    tl = json.loads(tl_path.read_text(encoding="utf-8"))
    scenes_data = tl.get("scenes", [])
    if not (0 <= scene_index < len(scenes_data)):
        raise IndexError(f"Scene index {scene_index} out of range (0-{len(scenes_data)-1})")

    from app.scenes import Scene
    scenes = []
    used_ids: set[str] = set()
    for item in scenes_data:
        sc = Scene(
            index=item["scene_index"],
            text=item["text"],
            start=item["start_s"],
            end=item["end_s"],
            visual_hint=item.get("visual_hint", item["text"][:30]),
        )
        sc.clip_path = item["clip"]["path"]
        sc.clip_meta = item["clip"]
        sc.relevance_score = item["clip"].get("relevance_score", 3.5)
        scenes.append(sc)
        if sc.clip_meta.get("id"):
            used_ids.add(str(sc.clip_meta["id"]))

    target_scene = scenes[scene_index]
    query = new_query or f"{target_scene.visual_hint} alt"
    from app.footage import fetch_clip
    new_clip = fetch_clip(
        query=query,
        duration=target_scene.end - target_scene.start,
        used_ids=used_ids,
        clip_dir=job_dir / "clips",
    )
    target_scene.visual_hint = query
    target_scene.clip_path = str(new_clip.path)
    target_scene.clip_meta = new_clip.meta
    target_scene.relevance_score = _rate_relevance(query, new_clip.meta)

    narration_path = job_dir / "narration.wav"
    if not narration_path.exists():
        # Search for any narration file in job_dir
        for p in job_dir.glob("narration*"):
            if p.is_file():
                narration_path = p
                break

    aspect_ratios = payload.get("aspect_ratios") or ["16:9"]
    from app.renderer import render
    result = render(
        scenes=scenes,
        narration_path=narration_path,
        aspect_ratios=aspect_ratios,
        job_id=job_id,
        burn_captions=payload.get("captions", {}).get("burn_in", False),
        srt=payload.get("captions", {}).get("srt", True),
    )
    return result

