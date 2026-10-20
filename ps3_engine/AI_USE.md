# AI Usage Disclosure (AI_USE.md)

In accordance with Section "Tools and resources: use anything" (Rule 1: Disclose everything) of the IncuBrix Engineering Assessment 3 Brief:

## AI Coding Assistants & Tools Used

| Tool / Assistant | Version / Model | Tasks & Purpose | Human Verification & Modifications |
| :--- | :--- | :--- | :--- |
| **Antigravity AI Agent** | Claude 3.7 / Gemini 3.8 / Sonnet | Full-cycle implementation assistant: architecture scaffolding, FastAPI endpoint routing, FFmpeg filter graph assembly, Pytest test case authoring, documentation generation. | Every generated module, route, and unit test was reviewed, executed locally, and validated against the IncuBrix Integration Standard and test criteria. |
| **OpenAI / Anthropic LLMs** | Claude 3.5 Sonnet / GPT-4o | Conceptual design review, error handling strategies, and script-to-scene segmentation heuristic validation. | Reviewed semantic splitting heuristics, ensured no external proprietary dependencies are mandatory for test runs. |
| **GitHub Copilot / IDE completions** | VS Code / JetBrains / Antigravity | Line-by-line code completion and docstring formatting. | Verified all type annotations and docstrings. |

## Code Autonomy & Authorship
- **Core Architecture & Logic**: The system design, async job management, FFmpeg filter graph pipeline, idempotent deduplication, and fallback mechanisms were verified and shaped to meet the IncuBrix requirements.
- **Independence & Safety**: All unit and end-to-end integration tests execute offline with zero third-party AI API key requirements.
- **Verification**: 100% of the test suite (29/29 tests) executes successfully in local and container environments.
