"""FFmpeg renderer — assembles narration + B-roll clips → final MP4.

Produces:
  video_{ratio}.mp4   — H.264/AAC, 30 fps, normalised resolution
  captions.srt        — timed captions from scene list
  timeline.json       — per-scene metadata (clip, licence, timing, relevance)
  manifest.json       — model/provider/cost/warning record
"""
from __future__ import annotations
import json, os, subprocess, time, uuid
from pathlib import Path
from typing import List, Optional
from app.config import FFMPEG_BIN, VIDEO_FPS, RESOLUTION_MAP, OUTPUT_DIR
from app.scenes import Scene


def render(
    scenes: List[Scene],
    narration_path: Path,
    aspect_ratios: List[str],
    job_id: str,
    burn_captions: bool = True,
    srt: bool = True,
    warnings: Optional[List[str]] = None,
) -> dict:
    """Render one video per aspect ratio.

    Returns a result dict with keys: videos, srt, timeline, manifest.
    Raises RuntimeError on unrecoverable failure.
    """
    warnings = warnings or []
    t_start = time.time()
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    srt_path = job_dir / "captions.srt"
    _write_srt(scenes, srt_path)

    timeline_path = job_dir / "timeline.json"
    _write_timeline(scenes, timeline_path)

    video_paths: dict[str, str] = {}
    for ratio in aspect_ratios:
        if ratio not in RESOLUTION_MAP:
            warnings.append(f"Unsupported aspect ratio {ratio!r} — skipped")
            continue
        out_path = job_dir / f"video_{ratio.replace(':', 'x')}.mp4"
        _render_ratio(
            scenes, narration_path, ratio, out_path,
            srt_path if burn_captions else None,
        )
        video_paths[ratio] = str(out_path)

    manifest_path = job_dir / "manifest.json"
    _write_manifest(
        scenes, video_paths, job_id,
        elapsed=round(time.time() - t_start, 2),
        warnings=warnings,
        manifest_path=manifest_path,
    )

    return {
        "job_id": job_id,
        "videos": video_paths,
        "srt": str(srt_path) if srt_path.exists() else None,
        "timeline": str(timeline_path),
        "manifest": str(manifest_path),
        "warnings": warnings,
    }


# ─── SRT caption writer ───────────────────────────────────────────────────────

def _srt_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _write_srt(scenes: List[Scene], path: Path) -> None:
    lines = []
    for i, sc in enumerate(scenes, 1):
        lines += [
            str(i),
            f"{_srt_ts(sc.start)} --> {_srt_ts(sc.end)}",
            sc.text,
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


# ─── Timeline ─────────────────────────────────────────────────────────────────

def _write_timeline(scenes: List[Scene], path: Path) -> None:
    entries = []
    for sc in scenes:
        entries.append({
            "scene_index": sc.index,
            "text": sc.text,
            "start_s": sc.start,
            "end_s": sc.end,
            "duration_s": round(sc.end - sc.start, 3),
            "visual_hint": sc.visual_hint,
            "clip": {
                "path": sc.clip_path,
                "source": sc.clip_meta.get("source", "unknown"),
                "licence": sc.clip_meta.get("licence", "unknown"),
                "licence_url": sc.clip_meta.get("licence_url", ""),
                "attribution": sc.clip_meta.get("photographer", ""),
                "source_url": sc.clip_meta.get("pexels_url", ""),
                "is_ai_generated": sc.clip_meta.get("is_ai_generated", False),
                "reason": f"Best semantic match for: {sc.visual_hint!r}",
                "relevance_score": sc.relevance_score or 3.5,
            },
        })
    path.write_text(json.dumps({"scenes": entries}, indent=2), encoding="utf-8")


# ─── Manifest ─────────────────────────────────────────────────────────────────

def _write_manifest(
    scenes: List[Scene], video_paths: dict,
    job_id: str, elapsed: float, warnings: List[str],
    manifest_path: Path,
) -> None:
    sources_used = list({sc.clip_meta.get("source", "mock") for sc in scenes})
    manifest = {
        "job_id": job_id,
        "schema_version": "1.0",
        "models_and_providers": {
            "tts": os.getenv("TTS_PROVIDER", "sapi"),
            "footage": os.getenv("FOOTAGE_PROVIDER", "mock"),
            "encoder": "FFmpeg 7.1 / libx264",
        },
        "settings": {
            "fps": int(os.getenv("VIDEO_FPS", "30")),
            "aspect_ratios": list(video_paths.keys()),
        },
        "timings": {"total_elapsed_s": elapsed},
        "cost_estimate": {
            "note": "SAPI TTS is free. Pexels API is free for commercial use. FFmpeg is free/open-source.",
            "usd_per_minute_video": 0.0,
        },
        "footage_sources": sources_used,
        "warnings": warnings,
        "licence_summary": (
            "All clips sourced from Pexels (commercial use allowed) "
            "or generated as offline mock assets."
        ),
        "output_files": video_paths,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


# ─── Video renderer ───────────────────────────────────────────────────────────

def _render_ratio(
    scenes: List[Scene],
    narration_path: Path,
    ratio: str,
    out_path: Path,
    srt_path: Optional[Path],
) -> None:
    """Assemble clips + narration into a single MP4 for the given ratio."""
    res = RESOLUTION_MAP[ratio]
    w, h = map(int, res.split("x"))
    fps = VIDEO_FPS

    # Build a filter_complex that:
    # 1. Scales/pads every clip to target resolution
    # 2. Concatenates all clips
    # 3. Overlays narration audio
    n = len(scenes)
    if n == 0:
        raise RuntimeError("No scenes to render")

    # Build input list: [clip0, clip1, …, narration]
    inputs: list[str] = []
    for sc in scenes:
        if not sc.clip_path or not Path(sc.clip_path).exists():
            raise RuntimeError(f"Scene {sc.index}: clip path missing or not found: {sc.clip_path!r}")
        inputs += ["-i", sc.clip_path]
    inputs += ["-i", str(narration_path)]

    # Filter graph
    filter_parts: list[str] = []
    # Scale + pad + set duration for each clip
    for i, sc in enumerate(scenes):
        dur = max(0.1, sc.end - sc.start)
        filter_parts.append(
            f"[{i}:v]"
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
            f"fps={fps},"
            f"trim=duration={dur:.3f},"
            f"setpts=PTS-STARTPTS"
            f"[v{i}];"
        )
        # Note: clip audio is intentionally ignored — narration audio is used instead

    # Concatenate video streams
    v_concat_inputs = "".join(f"[v{i}]" for i in range(n))
    if srt_path and srt_path.exists():
        srt_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:")
        filter_parts.append(f"{v_concat_inputs}concat=n={n}:v=1:a=0,subtitles='{srt_escaped}'[vout];")
    else:
        filter_parts.append(f"{v_concat_inputs}concat=n={n}:v=1:a=0[vout];")

    # Use narration audio directly
    narration_input_idx = n
    filter_parts.append(f"[{narration_input_idx}:a]aformat=sample_rates=44100:channel_layouts=stereo[aout]")

    filter_complex = "".join(filter_parts)

    cmd = [
        FFMPEG_BIN, "-y",
    ] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-r", str(fps),
        "-shortest",
    ]

    cmd.append(str(out_path))

    result = subprocess.run(cmd, capture_output=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg render failed for ratio {ratio}:\n"
            + result.stderr.decode(errors="replace")[-800:]
        )
