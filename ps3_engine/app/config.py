"""Central configuration via environment variables.
No hard-coded paths, keys or limits.
"""
import os
from pathlib import Path

# ── Storage ──────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Redis / RQ ────────────────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ── TTS ───────────────────────────────────────────────────────────────────────
# Provider: "sapi" (Windows SAPI, offline) | "mock" (silent WAV, for tests)
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "sapi")
TTS_LANGUAGE = os.getenv("TTS_LANGUAGE", "en")

# ── Footage source ────────────────────────────────────────────────────────────
# Provider: "pexels" | "mock"
FOOTAGE_PROVIDER = os.getenv("FOOTAGE_PROVIDER", "mock")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# ── FFmpeg ────────────────────────────────────────────────────────────────────
FFMPEG_BIN = os.getenv("FFMPEG_BIN")
if not FFMPEG_BIN:
    import shutil
    FFMPEG_BIN = shutil.which("ffmpeg")
if not FFMPEG_BIN:
    try:
        import imageio_ffmpeg
        FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
if not FFMPEG_BIN:
    _known = r"C:\Users\kumar\AppData\Local\Programs\Python\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
    if os.path.exists(_known):
        FFMPEG_BIN = _known
    else:
        FFMPEG_BIN = "ffmpeg"

# ── Video encoding ────────────────────────────────────────────────────────────
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "30"))
VIDEO_RESOLUTION_16_9 = os.getenv("VIDEO_RESOLUTION_16_9", "1280x720")
VIDEO_RESOLUTION_9_16 = os.getenv("VIDEO_RESOLUTION_9_16", "720x1280")
VIDEO_RESOLUTION_1_1  = os.getenv("VIDEO_RESOLUTION_1_1",  "720x720")

# ── Limits ────────────────────────────────────────────────────────────────────
MAX_AUDIO_SECONDS = int(os.getenv("MAX_AUDIO_SECONDS", "600"))   # 10 min

RESOLUTION_MAP = {
    "16:9": VIDEO_RESOLUTION_16_9,
    "9:16": VIDEO_RESOLUTION_9_16,
    "1:1":  VIDEO_RESOLUTION_1_1,
}
