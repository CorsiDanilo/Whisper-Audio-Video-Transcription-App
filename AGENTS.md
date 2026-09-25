# Instructions: Whisper Utility - Multi-Platform Audio Transcription & LLM Post-Processing Suite

## Scope & Operational Boundaries
- Never commit secrets, credentials, tokens, `.env`, or `secrets/gemini.yaml`.
- Do not bypass path sanitization in `security_utils.py`.
- Preserve existing packaging targets and requirement matrix separation (`requirements_cpu.txt`, `requirements_gpu.txt`, etc.).

## Architecture & Data Flow
- Directory responsibilities:
  - `main.py`: Headless/web entry point launching Gradio web interface on `127.0.0.1:7860`.
  - `app_main.py` & `ui.py`: Standalone desktop GUI built with CustomTkinter.
  - `transcription.py`: Local `faster-whisper` transcription orchestrator with chunking, beam search, and temperature fallback.
  - `remote_transcription.py`: Client for offloading transcription to external remote Whisper services.
  - `audio_processing.py`: Audio format conversion, silence trimming, and FFmpeg wrapper.
  - `llms.py`: Text post-processing and summarization via LLM APIs (Gemini, Ollama, LM Studio).
  - `security_utils.py`: Path traversal validation, safe filename sanitization, and command execution guardrails.
  - `tools/build_release.py`: Packaging pipeline invoking PyInstaller with `whisper.spec`.

```
[Audio Input (File / Microphone)]
                |
                v
+-------------------------------+
|     UI (CustomTkinter / Gradio)|
+---------------+---------------+
                |
                v
+-------------------------------+
|     security_utils.py         | (Validates input file paths & safe temp dirs)
+---------------+---------------+
                |
        +-------+-------+
        | Mode Toggle   |
        v               v
+---------------+ +---------------+
|transcription  | |remote_transcr |
|faster-whisper | |REST / WS API  |
+-------+-------+ +-------+-------+
        |                 |
        +-------+---------+
                v
+-------------------------------+
|     llms.py (Post-Process)    | (Punctuation fix, summarization via LLMs)
+---------------+---------------+
                v
 [Export: TXT, SRT, VTT, JSON] -> outputs/
```

- Invariant: All file paths handled by UI or APIs must be validated through `security_utils.validate_safe_path` before file system reads/writes.

## Interfaces & Contracts
- **Input Media Formats**:
  - Audio/Video: MP3, WAV, M4A, AAC, FLAC, OGG, MP4, MKV.
- **Export Outputs**:
  - Subtitle outputs: `.srt`, `.vtt`.
  - Document outputs: `.txt`, `.json`, `.csv`.
- **Gradio Web Interface**:
  - Default URL: `http://127.0.0.1:7860`. Requires `WHISPER_GRADIO_AUTH_USER` and `WHISPER_GRADIO_AUTH_PASSWORD` when bound to external interfaces.

## Domain States, Enums & Decisions
- **Transcription Engines**:
  - `LOCAL_FASTER_WHISPER`: In-process CPU/CUDA inference.
  - `REMOTE_SERVICE`: HTTP/WebSocket offload.
- **Output Timestamps**: Word-level vs Segment-level timestamps.

## Critical Business Logic & Invariants
- **Configuration Hierarchy**: App loads configuration from OS user AppData first, falling back to repository `settings/` defaults.
- **FFmpeg Requirement**: Host runs require `ffmpeg` on system `PATH`; Docker containers install it internally.
- **Strict Requirement Segregation**: Never combine CPU and GPU packages in the same environment; keep `requirements_cpu.txt` and `requirements_gpu.txt` clean.

## Persistence & Storage
- Output transcripts saved to `outputs/` or user-chosen target folder.
- Downloaded model weights cached in `whisper_models_cache` volume or `HF_HOME`.

## Error Handling
- FFmpeg process failures surface structured stderr messages to the user UI.
- Corrupted audio streams trigger graceful task abort with cleanup of partial temp files in `temp/`.

## Verified Commands
- Install CPU dependencies: `python -m pip install -r requirements_cpu.txt`
- Install GPU dependencies: `python -m pip install -r requirements_gpu.txt`
- Development Run (Gradio): `python main.py`
- Desktop App Run: `python app_main.py`
- Docker CPU: `docker compose --profile cpu up --build`
- Docker GPU: `docker compose --profile gpu up --build`
- Lint & Format Check: `python -m ruff check .` and `python -m ruff format --check .`
- Lint Autofix: `python -m ruff check --fix .` and `python -m ruff format .`
- Release Build: `python tools/build_release.py`
- Single-file Syntax Check: `python -m py_compile audio_processing.py`
- Test Suite: Not configured
- Type Checking: Not configured

## Conventions & Documentation
- Document breaking configuration changes in `CHANGELOG.md`.
- Enforce Ruff style compliance before pushing releases.
