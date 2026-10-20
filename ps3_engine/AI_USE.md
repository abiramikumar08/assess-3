# AI Usage Disclosure

## 1. Purpose of AI Assistance

AI coding assistants were used during the development of the IncuBrix Engineering Assessment 3 project, **Script-to-B-roll Video Engine**. They helped with project setup, implementation, debugging, testing, and technical documentation.

## 2. Tools Used

| Tool | How it was used |
|---|---|
| Antigravity AI coding agent | Assisted with project scaffolding, FastAPI endpoints, job handling, video-processing logic, FFmpeg commands, automated tests, and documentation. |
| OpenAI ChatGPT | Assisted with reviewing implementation approaches, identifying issues, improving error handling, and preparing development and verification prompts. |


## 3. Human Review and Verification

AI-generated code and documentation were reviewed during development. The project was run locally, automated tests were executed, and a sample video was generated to check the main rendering workflow.

The reported test run completed with 30 tests passing. Some tests use mock components, so this result should not be interpreted as proof that every external integration works in a production environment.

A separate sample run used Windows Speech API (SAPI) for narration, downloaded video footage from Wikimedia Commons, and FFmpeg to render an MP4. The generated video and its associated captions and metadata were inspected.

## 4. Limitations

The implementation has known limitations:

- Automatic speech-to-text transcription for audio-only input is not implemented.
- Docker Compose startup has not been verified because Docker was unavailable in the development environment.
- A publicly accessible live deployment has not been established.

These limitations are documented rather than presented as completed features.

## 5. Responsibility for the Submission

AI tools assisted with development, debugging, testing, and documentation. The submitted implementation and its claims should be evaluated against the actual source code, test results, generated outputs, and documented limitations. I am responsible for reviewing the final submission and for explaining the implementation and the parts that remain incomplete.

