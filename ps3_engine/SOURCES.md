# Sources & Licences Disclosure (SOURCES.md)

In accordance with Section "Tools and resources: use anything" (Rule 1 & Rule 2: Commercially usable) of the IncuBrix Engineering Assessment 3 Brief:

## 1. Libraries & Frameworks

| Name | Version | Licence | Purpose | Commercial Use Allowed |
| :--- | :--- | :--- | :--- | :--- |
| **FastAPI** | 0.115.0 | MIT | Asynchronous REST API framework | Yes |
| **Uvicorn** | 0.30.6 | BSD-3-Clause | ASGI web server | Yes |
| **Pydantic** | 2.8.2 | MIT | Request/response data validation and schemas | Yes |
| **Redis** | 5.0.7 | MIT | Redis client for background task queue | Yes |
| **RQ (Redis Queue)** | 1.16.2 | BSD-2-Clause | Lightweight asynchronous task queue | Yes |
| **FFmpeg** | 7.1 Essentials | LGPL 2.1+ / GPL v3 (configured without non-free code) | Video transcoding, normalization, subtitle burning | Yes |
| **imageio-ffmpeg** | 0.6.0 | BSD-2-Clause | Cross-platform binary discovery and packaging | Yes |
| **HTTPX** | 0.27.2 | BSD-3-Clause | Asynchronous and synchronous HTTP client for tests & batch runner | Yes |
| **Pytest** | 8.3.2 | MIT | Unit, integration, and E2E testing framework | Yes |
| **openpyxl** | 3.1.5 | MIT | Excel report automation | Yes |

## 2. Media & Footage Sources

| Source | Licence | Attribution Required | Commercial Use | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Wikimedia Commons (`clip1_fountain.webm`)** | CC BY-SA 4.0 | Yes (Wikimedia Commons Contributor) | Allowed | Real stock video used in genuine E2E verification test. |
| **Wikimedia Commons (`clip2_river.ogv`)** | CC BY 2.0 de | Yes (User:Mattes) | Allowed | Real stock video used in genuine E2E verification test. |
| **Pexels API** | Pexels Free Licence | Recommended (Photographer name + Pexels link stored in `timeline.json`) | Allowed | Stock video footage search by semantic query keywords. |
| **Synthetic Mock Footage** | Generated Asset (Public Domain / MIT) | None | Allowed | Offline fallback producing clean solid-hue video clips matching scene duration. Zero external dependencies. |

## 3. Speech & Narration (TTS)

| Provider | Licence | Commercial Use | Notes |
| :--- | :--- | :--- | :--- |
| **Windows SAPI** | Windows Built-In System Component | Allowed | Local offline text-to-speech engine; zero API costs. |
| **Synthetic Mock TTS** | Generated WAV Audio (Public Domain) | Allowed | Offline silent/tone WAV audio generator scaled precisely to word count and scene timings for deterministic testing. |

## 4. Models & Algorithms
- **Semantic Text Chunking**: Regex-based sentence boundary segmentation respecting punctuation and phrase structure (`[.!?]+`) with minimum scene duration guards (1.5s–7.0s).
- **Aspect Ratio Normalization**: FFmpeg `scale=w:h:force_original_aspect_ratio=decrease,pad=w:h:(ow-iw)/2:(oh-ih)/2:black` filter graph pipeline, ensuring no aspect distortion or black-bar drift across 16:9, 9:16, and 1:1.
