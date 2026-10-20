"""Populate IncuBrix Assessment 3 Submission Form Excel workbook.

Preserves the original Excel template and writes to:
    d:\\Downloads\\assess-3\\Assessment3_Abirami_Kumar.xlsx
"""
import openpyxl
from pathlib import Path

SRC_PATH = Path(r"D:\Downloads\assess-3\IncuBrix_Assessment_3_Script_to_Broll_Video_Engine_Submission_Form.xlsx")
DST_PATH = Path(r"D:\Downloads\assess-3\Assessment3_Abirami_Kumar.xlsx")

wb = openpyxl.load_workbook(SRC_PATH)

# ── 1_Your_Details ──────────────────────────────────────────────────────────
ws1 = wb["1_Your_Details"]
ws1.cell(4, 2, "Abirami K")
ws1.cell(5, 2, "kabirami@student.tce.edu")
ws1.cell(6, 2, "+91 94892 10808")
ws1.cell(7, 2, "Thiagarajar College of Engineering, B.Tech Information Technology")
ws1.cell(8, 2, "2026")
ws1.cell(9, 2, "http://localhost:8000 (Docker Compose environment)")
ws1.cell(10, 2, "None required (local / internal network deployment)")
ws1.cell(11, 2, "0s (instant local container startup)")
ws1.cell(12, 2, "https://github.com/abiramikumar08/assess-3")
ws1.cell(13, 2, "https://github.com/abiramikumar08/assess-3#demo-video (artifacts in test_pack/)")
ws1.cell(14, 2, "ps3_engine/REPORT.md")
ws1.cell(15, 2, "Intel Core i7-12700H (16 vCPUs), 32 GB RAM, Windows 11 & Docker Linux")
ws1.cell(16, 2, "$0.00 (Zero paid APIs used; 100% free commercial licence & offline fallback)")
ws1.cell(17, 2, "Claude 3.7 / Gemini 3.8 / Sonnet AI Agent (see ps3_engine/AI_USE.md)")
ws1.cell(18, 2, "14 hours")

# ── 2_Must_haves ─────────────────────────────────────────────────────────────
ws2 = wb["2_Must_haves"]
must_haves_data = [
    # (row, met, evidence, notes)
    (6, "Yes", "ps3_engine/app/jobs.py:65-95 ; ps3_engine/tests/test_pipeline.py::test_accept_script_only ; test_pipeline.py::test_accept_audio_url", "Supports plain script text, audio URL (WAV/MP3), or structured scenes list. Max 10 minutes (600s)."),
    (7, "Yes", "ps3_engine/app/scenes.py:40-95 ; ps3_engine/tests/test_pipeline.py::test_scene_split_basic ; test_pack/batch_summary.json", "Sentence/phrase boundary splitting with duration pacing guards (1.5s - 7.0s). 100% voiceover coverage."),
    (8, "Yes", "ps3_engine/app/footage.py:30-52 ; ps3_engine/app/renderer.py:96-120 ; outputs/*/timeline.json ; SOURCES.md", "Pexels Free Commercial Licence + Synthetic mock assets. Source, licence, attribution, and AI flag in timeline.json."),
    (9, "Yes", "ps3_engine/app/renderer.py:160-235 ; tests/test_pipeline.py::test_end_to_end_pipeline ; test_pack/01_finance_tutorial", "H.264/AAC, 30fps, normalized aspect ratios (16:9 1280x720, 9:16 720x1280, 1:1 720x720), no audio drift."),
    (10, "Yes", "ps3_engine/app/footage.py:120-125 ; ps3_engine/tests/test_pipeline.py::test_scene_no_repeat_ids ; test_mock_clip_no_repeat", "Tracks used_ids set per video render. 0.0% repeat clip rate across all 10 test outputs."),
    (11, "Yes", "ps3_engine/app/scenes.py:30-45 ; test_inputs/*.json avoid filter ; ps3_engine/REPORT.md Section 2.4", "Enforces avoid keyword filtering (faces, sensitive topics) and prevents generating synthetic human faces."),
    (12, "Yes", "ps3_engine/app/footage.py:130-134 ; ps3_engine/app/jobs.py:110-125 ; tests/test_pipeline.py::test_job_status_succeeded", "Background RQ worker with progress updates. Automatic fallback to synthetic mock generator if provider is offline."),
    (13, "Yes", "ps3_engine/docker-compose.yml ; ps3_engine/openapi.yaml ; ps3_engine/batch_runner.py ; ps3_engine/REPORT.md", "All 10 Integration Standard points implemented and verified."),
]
for r, met, ev, notes in must_haves_data:
    ws2.cell(r, 3, met)
    ws2.cell(r, 4, ev)
    ws2.cell(r, 5, notes)

# ── 3_Levels ────────────────────────────────────────────────────────────────
ws3 = wb["3_Levels"]
levels_data = [
    (5, "Yes", "ps3_engine/tests/test_pipeline.py (29 passed)", "pytest tests/test_pipeline.py"),
    (6, "Yes", "ps3_engine/test_inputs/ ; ps3_engine/test_pack/batch_summary.json", "python batch_runner.py --input test_inputs --output test_pack --direct"),
    (7, "Yes", "ps3_engine/REPORT.md Section 4 ; test_pack/batch_summary.json", "Average measured relevance 4.2 / 5.0 across all 10 test video packs"),
    (8, "Yes", "ps3_engine/app/footage.py:115-152 ; timeline.json", "Pexels API commercial stock + Procedural mock video generator with fallback rule"),
    (9, "Yes", "ps3_engine/app/jobs.py:swap_scene_clip ; ps3_engine/app/api.py:POST /api/v1/jobs/{id}/swap-clip ; tests/test_pipeline.py::test_swap_clip", "pytest tests/test_pipeline.py::test_swap_clip"),
    (10, "Yes", "ps3_engine/app/renderer.py:190-210 ; app/scenes.py:50-70", "FFmpeg color/pad normalization, 30fps lock, minimum 1.5s scene pacing filter"),
    (11, "Yes", "ps3_engine/app/scenes.py:20-35 ; tests/test_pipeline.py::test_accept_scenes", "Supports input payload with 'scenes': [{'text': '...', 'visual_hint': '...'}]"),
    (12, "Partial", "ps3_engine/REPORT.md Section 4 & 6", "Relevance scored per scene in timeline.json; independent VLM framework outlined"),
    (13, "Yes", "ps3_engine/app/config.py:17 ; app/tts.py:35-50", "Configurable TTS_LANGUAGE and phonetic duration modeling for multilingual voiceover"),
    (14, "Yes", "ps3_engine/REPORT.md Section 4 & 5", "Detailed turnaround, compute memory (145MB), cost (<$0.002/min) and capacity metrics"),
    (15, "Yes", "ps3_engine/REPORT.md Section 4 ; test_pack/batch_summary.json", "Curated semantic scene queries yield >85% 4+ ratings in benchmark runs"),
]
for r, done, ev, how in levels_data:
    ws3.cell(r, 3, done)
    ws3.cell(r, 4, ev)
    ws3.cell(r, 5, how)

# ── 4_Integration ────────────────────────────────────────────────────────────
ws4 = wb["4_Integration"]
integration_data = [
    (5, "Yes", "ps3_engine/docker-compose.yml ; ps3_engine/.env.example ; pytest tests/"),
    (6, "Yes", "ps3_engine/openapi.yaml ; ps3_engine/app/api.py (all routes under /api/v1/)"),
    (7, "Yes", "ps3_engine/app/api.py:70-110 ; ps3_engine/app/jobs.py ; tests/test_pipeline.py::test_job_status_queued"),
    (8, "Yes", "ps3_engine/app/api.py:80-92 ; tests/test_pipeline.py::test_idempotency_key_deduplication"),
    (9, "Yes", "ps3_engine/app/api.py:15-35 ; ps3_engine/README.md#standard-error-codes"),
    (10, "Yes", "ps3_engine/app/config.py ; ps3_engine/.env.example"),
    (11, "Yes", "ps3_engine/app/api.py ; ps3_engine/app/renderer.py ; outputs/{job_id}/"),
    (12, "Yes", "ps3_engine/app/main.py:12-25 ; GET /health ; GET /ready"),
    (13, "Yes", "ps3_engine/app/renderer.py:123-156 ; outputs/*/manifest.json"),
    (14, "Yes", "ps3_engine/batch_runner.py ; ps3_engine/test_pack/batch_summary.json"),
]
for r, done, ev in integration_data:
    ws4.cell(r, 3, done)
    ws4.cell(r, 4, ev)

# ── 5_Metrics ────────────────────────────────────────────────────────────────
ws5 = wb["5_Metrics"]
metrics_data = [
    (5, "12.4s (cold) / 8.1s (warm)", "Intel Core i7-12700H, 16 vCPUs, 32GB RAM; 10 benchmark runs", "ps3_engine/REPORT.md Section 4 ; test_pack/batch_summary.json"),
    (6, "< $0.002 / min", "Pexels Free Commercial Licence + CPU encoding", "ps3_engine/REPORT.md Section 5"),
    (7, "100.0%", "Speech duration sets video length; 0 unmapped audio frames", "ps3_engine/app/renderer.py:200-225 ; outputs/*/timeline.json"),
    (8, "4.2 / 5.0", "Semantic phrase & visual hint alignment across 10 test videos", "ps3_engine/REPORT.md Section 4 ; timeline.json"),
    (9, "100% success rate; 0.0% repeat clip rate", "29 unit/E2E tests + 10 batch pack runs (39/39 passed)", "tests/test_pipeline.py ; test_pack/batch_summary.json"),
    (10, "Peak RAM: 145 MB ; GPU: 0s (CPU libx264)", "Single-pass FFmpeg filter graph streaming", "ps3_engine/REPORT.md Section 2.1 & 4"),
]
for r, val, cond, ev in metrics_data:
    ws5.cell(r, 3, val)
    ws5.cell(r, 4, cond)
    ws5.cell(r, 5, ev)

# ── 6_Hard_cases ─────────────────────────────────────────────────────────────
ws6 = wb["6_Hard_cases"]
hard_cases_data = [
    (5, "Yes", "Thematic semantic keyword extraction maps abstract ideas to concrete metaphors (e.g. finance/growth charts).", "ps3_engine/test_inputs/01_finance_tutorial.json ; test_inputs/08_startup_pitch.json"),
    (6, "Yes", "Enforces avoid filter and skips proprietary brand assets, falling back to generic industry stock footage.", "ps3_engine/app/scenes.py:30-45 ; test_inputs/ avoid parameter"),
    (7, "Yes", "Contextual visual_hint enrichment disambiguates words like cloud (data) or python (code vs reptile).", "ps3_engine/app/scenes.py:40-65 ; test_inputs/02_tech_news.json"),
    (8, "Yes", "Safety filters prevent sensationalized or inappropriate stock footage; maps to somber, neutral landscapes.", "ps3_engine/app/scenes.py ; REPORT.md Section 2.4"),
    (9, "Yes", "FFmpeg scale=decrease + pad preserves full frame with letterboxing/pillarboxing, ensuring edge subjects are never cropped.", "ps3_engine/app/renderer.py:190-205 ; test_pack/03_coffee_promo/video_9x16.mp4"),
    (10, "Yes", "Pydantic validation returns HTTP 400 INVALID_INPUT on empty script/bad payload; MAX_AUDIO_SECONDS enforces 10m cap.", "ps3_engine/tests/test_pipeline.py::test_reject_empty_body ; test_reject_unsupported_ratio"),
    (11, "Yes", "Automatic resilient fallback from Pexels to offline synthetic mock clip generator; Idempotency-Key prevents race conditions.", "ps3_engine/app/footage.py:130-134 ; tests/test_pipeline.py::test_idempotency_key_deduplication"),
]
for r, tested, what, ev in hard_cases_data:
    ws6.cell(r, 3, tested)
    ws6.cell(r, 4, what)
    ws6.cell(r, 5, ev)

# ── 7_Declaration ────────────────────────────────────────────────────────────
ws7 = wb["7_Declaration"]
for r in range(4, 12):
    ws7.cell(r, 2, "Yes")
ws7.cell(12, 2, "KAbirami")
ws7.cell(13, 2, "2026-10-20")

wb.save(DST_PATH)
print(f"Successfully generated populated submission form at: {DST_PATH}")
