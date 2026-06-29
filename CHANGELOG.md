# Changelog

## [1.1.0] - 2026-06-29

### Added

- **Local Model Readiness Polling**: Added readiness verification for Ollama and LM Studio. The system polls the respective local endpoints (`/api/ps` for Ollama and `/v1/models` for LM Studio) every 2s for up to 60s before executing LLM assistant queries.
- **Dynamic LM Studio Model Loading**: Added automatic model loading triggers calling `/api/v1/models/load` (with `/v1/models/load` fallback) to dynamically load LM Studio models on request.
- **Progress Indicators**: Integrated UI status messages (e.g., `⏳ checking model status...`, `⏳ model loading...`, `⏳ sending request...`) to improve visibility of background operations.
- **Ollama Timeout**: Increased Ollama API connection/read timeout to 120s to prevent failures during dynamic loading.
- **Localized Status Strings**: Added new keys for all status indicators to `settings/locales.yaml` in English and Italian.

## [1.0.1] - 2026-06-25

### Added

- **Fix Text** preset button (✏️ Correggi Testo) added to the AI Assistant section in **whisper-utility** and **video-analyzer-utility**, matching the existing feature in text-extractor-utility.
- When Fix Text is selected and a query is submitted to the LLM, a dedicated system prompt instructs the model to use **all available tokens** to maximise output and return the full corrected text without omissions or truncation.
- `SYSTEM_PROMPT_FIX_TEXT` constant added to `llms.py` (whisper-utility), `llm_vision.py` (video-analyzer-utility), and `config.py` (text-extractor-utility).
- `fix_text_mode` Gradio state added to all three UIs; automatically set to `True` when Fix Text preset is clicked and reset to `False` on other presets or field reset.
- Locale keys `preset_fix` and `preset_fix_val` added (English + Italian) to `settings/locales.yaml` in whisper-utility and video-analyzer-utility.

## [1.0.0] - 2026-06-21

### Added

- Initial public release on GitHub.
- GitHub Actions pipeline for multi-platform builds (Windows CPU, Windows GPU, macOS, Linux).
- Standalone executable distribution via PyInstaller — no Python installation required.
- Gradio-based web UI for audio and video transcription.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) integration for fast, local on-device transcription.
- Support for all Whisper model sizes (tiny → large-v3).
- GPU acceleration support (Windows GPU build requires NVIDIA drivers + CUDA toolkit).
- LLM integration with Google Gemini for transcript refinement and post-processing.
- System tray icon for background operation.
- Configurable settings via YAML files (`settings/cpu.yaml`, `settings/gpu.yaml`).
- CPU and GPU build variants for Windows.
