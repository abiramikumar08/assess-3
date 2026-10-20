"""Footage adapter — returns licence-clean video clips for a query.

Providers (selected by FOOTAGE_PROVIDER env var):
  pexels — Pexels API (free, requires PEXELS_API_KEY, commercial licence)
  mock   — returns a local test clip (solid-colour MP4); no internet needed

The Pexels Free licence allows commercial use.
See: https://www.pexels.com/license/
"""
from __future__ import annotations
import os, subprocess, json, hashlib
from pathlib import Path
from typing import Optional
from app.config import FOOTAGE_PROVIDER, PEXELS_API_KEY, FFMPEG_BIN, OUTPUT_DIR


# ─── helpers ─────────────────────────────────────────────────────────────────

def _pexels_search(query: str, per_page: int = 5) -> list[dict]:
    """Search Pexels for videos matching *query*; returns metadata list."""
    import urllib.request
    url = (
        f"https://api.pexels.com/videos/search"
        f"?query={urllib.parse.quote(query)}&per_page={per_page}&size=medium"
    )
    req = urllib.request.Request(url, headers={"Authorization": PEXELS_API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        raise RuntimeError(f"Pexels search failed for query {query!r}: {exc}")
    videos = []
    for v in data.get("videos", []):
        # pick the smallest file ≥480p to keep downloads fast
        files = sorted(v.get("video_files", []), key=lambda f: f.get("height", 0))
        file_ = next((f for f in files if f.get("height", 0) >= 480), files[0] if files else None)
        if not file_:
            continue
        videos.append({
            "id": str(v["id"]),
            "url": file_["link"],
            "width": file_.get("width"),
            "height": file_.get("height"),
            "duration": v.get("duration"),
            "photographer": v.get("user", {}).get("name", "Pexels contributor"),
            "pexels_url": v.get("url", ""),
            "licence": "Pexels Free Licence (commercial use allowed)",
            "licence_url": "https://www.pexels.com/license/",
            "is_ai_generated": False,
            "source": "pexels",
        })
    return videos


def _download_clip(url: str, dest: Path) -> Path:
    """Download a video URL to *dest* (streams to avoid memory spike)."""
    import urllib.request
    with urllib.request.urlopen(url, timeout=60) as resp, open(dest, "wb") as f:
        while chunk := resp.read(1 << 16):
            f.write(chunk)
    return dest


def _make_mock_clip(query: str, duration: float, dest: Path) -> Path:
    """Generate a solid-colour MP4 as a deterministic offline mock clip."""
    # Pick a hue based on query hash so different queries get different colours
    hue = int(hashlib.md5(query.encode()).hexdigest(), 16) % 360
    # HSV→RGB: use a simple fixed S/V for legibility
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(hue / 360, 0.7, 0.8)
    hex_color = f"0x{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    dur = max(1.0, duration)
    cmd = [
        FFMPEG_BIN, "-y",
        "-f", "lavfi", "-i", f"color={hex_color}:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
        "-t", str(dur),
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"Mock clip generation failed: {result.stderr.decode()[:300]}")
    return dest


# ─── public API ──────────────────────────────────────────────────────────────

class ClipResult:
    __slots__ = ("path", "meta")
    def __init__(self, path: Path, meta: dict):
        self.path = path
        self.meta = meta   # id, licence, attribution, source, …


def fetch_clip(
    query: str,
    duration: float,
    avoid: Optional[list[str]] = None,
    used_ids: Optional[set] = None,
    clip_dir: Optional[Path] = None,
) -> ClipResult:
    """Fetch a licence-clean clip that matches *query* for *duration* seconds.

    - Never returns a clip whose ID is in *used_ids*.
    - Falls back to mock if the provider is unavailable.
    - Raises RuntimeError only when even the fallback fails.
    """
    if clip_dir is None:
        clip_dir = OUTPUT_DIR / "clips"
    clip_dir.mkdir(parents=True, exist_ok=True)
    used_ids = used_ids or set()

    provider = FOOTAGE_PROVIDER

    if provider == "pexels":
        try:
            candidates = _pexels_search(query, per_page=10)
            # Filter out already-used clips
            candidates = [c for c in candidates if c["id"] not in used_ids]
            if not candidates:
                raise RuntimeError("No unused Pexels results")
            chosen = candidates[0]
            dest = clip_dir / f"pexels_{chosen['id']}.mp4"
            if not dest.exists():
                _download_clip(chosen["url"], dest)
            return ClipResult(path=dest, meta=chosen)
        except Exception as exc:
            # Resilient jobs: fall through to mock on provider failure
            import logging
            logging.warning(f"Pexels provider failed ({exc}), using mock clip")
            provider = "mock"

    # Mock provider
    safe_query = query[:40].replace(" ", "_").replace("/", "-")
    dest = clip_dir / f"mock_{safe_query}_{int(duration)}s.mp4"
    if not dest.exists():
        _make_mock_clip(query, duration, dest)
    mock_meta = {
        "id": f"mock_{hashlib.md5(query.encode()).hexdigest()[:8]}",
        "source": "mock",
        "licence": "Synthetic test asset — not for distribution",
        "licence_url": "N/A",
        "photographer": "Generated offline mock",
        "pexels_url": "N/A",
        "is_ai_generated": True,
        "width": 1280,
        "height": 720,
        "duration": duration,
    }
    return ClipResult(path=dest, meta=mock_meta)
