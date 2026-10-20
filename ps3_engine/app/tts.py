"""TTS adapter — produces a WAV audio file from plain text.

Providers (selected by TTS_PROVIDER env var):
  sapi  — Windows SAPI via PowerShell (offline, default on Windows)
  mock  — writes a properly-timed silent WAV; used in unit tests

No internet connection required for any default provider.
"""
from __future__ import annotations
import os, struct, wave, subprocess, tempfile, shutil
from pathlib import Path
from app.config import TTS_PROVIDER, TTS_LANGUAGE


FFMPEG_BIN = os.getenv(
    "FFMPEG_BIN",
    r"C:\Users\kumar\AppData\Local\Programs\Python\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe",
)


def get_audio_duration(path: Path) -> float:
    """Return duration in seconds using ffprobe."""
    ffprobe = Path(FFMPEG_BIN).parent / "ffprobe.exe"
    if not ffprobe.exists():
        # fall back: parse WAV header
        try:
            with wave.open(str(path), "r") as wf:
                return wf.getnframes() / wf.getframerate()
        except Exception:
            return 5.0
    result = subprocess.run(
        [str(ffprobe), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, timeout=10,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 5.0


def synthesise(text: str, output_path: Path) -> Path:
    """Convert *text* to speech and write to *output_path*.

    Returns the path of the generated audio file (.wav).
    Raises RuntimeError on failure so the caller can surface a clear error.
    """
    provider = TTS_PROVIDER
    if provider == "sapi":
        return _sapi(text, output_path)
    if provider == "mock":
        return _mock_silent(text, output_path)
    raise RuntimeError(
        f"Unknown TTS_PROVIDER: {provider!r}. Set TTS_PROVIDER=sapi|mock"
    )


def _sapi(text: str, output_path: Path) -> Path:
    """Use Windows Speech API via a PowerShell one-liner."""
    path = output_path.with_suffix(".wav")
    # Escape single quotes in the text
    safe_text = text.replace("'", "''")
    ps_script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.SetOutputToWaveFile('{path}'); "
        f"$s.Speak('{safe_text}'); "
        "$s.Dispose()"
    )
    result = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0 or not path.exists():
        raise RuntimeError(
            f"SAPI TTS failed: {result.stderr[:300]}"
        )
    return path


def _mock_silent(text: str, output_path: Path) -> Path:
    """Write a properly-timed silent WAV (approx speech rate ~3 words/sec)."""
    path = output_path.with_suffix(".wav")
    sample_rate = 22050
    word_count = max(1, len(text.split()))
    duration_s = max(1, round(word_count / 3))
    n_frames = sample_rate * duration_s
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_frames)
    return path
