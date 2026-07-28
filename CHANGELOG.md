# Changelog

## [2.0.0] - 2026-07-28

### Added
- **Smart GUI Installer**: Created a multi-step graphical setup wizard with automatic OS and hardware detection.
- **Automated Dependency Management**: The installer automatically downloads FFmpeg and CUDA runtime libraries on demand based on the user's hardware, eliminating complex manual setups.
- **Standalone Executable Builds**: Added automated PyInstaller build scripts to generate a fully portable `.exe` bundle with embedded dependencies.
- **In-App Config Editor**: Refactored the UI to include a fullscreen "Config Files Editor" modal to seamlessly edit `settings/default.yaml` and `secrets/gemini.yaml` from within the app.

### Changed
- **Increased Default Window Size**: Adjusted the default pywebview window to `1280x850` for better visibility of the transcription UI and configuration panels.


## [1.3.3] - 2026-07-27

### Optimized
- **Fast FFmpeg Audio Extraction & Hardware Acceleration**: Added `-vn`, `-sn`, `-dn`, and `-threads 0` flags to FFmpeg audio extraction commands to skip video/subtitle/data stream decoding completely, speeding up audio extraction from video files (such as `.mkv` or `.mp4`) from minutes to seconds. Added optional GPU hardware acceleration (`-hwaccel auto`) when CUDA is enabled.

### Fixed
- **Gradio Progress Bar Text Overlay**: Set `track_tqdm=False` in `gr.Progress()` and updated CSS to prevent floating progress bar overlays from covering and blocking the transcribed text component during streaming.
- **Duplicate Single-File Transcription Files**: Updated output logic to save the combined session transcript (`<timestamp>_transcription.<ext>`) only when transcribing multiple files in a batch, eliminating duplicate `.txt` files when transcribing a single file.

## [1.3.2] - 2026-07-24

### Added
- **Configurable Local LLM Timeouts**: Added `lmstudio_timeout` and `ollama_timeout` in `settings/default.yaml` and environment variable overrides (`LMSTUDIO_TIMEOUT`, `OLLAMA_TIMEOUT`) with an increased 300s default timeout to prevent read timeouts during cold starts or heavy model processing.
- **Dedicated Status Badge & Live Indicators**: Added a prominent status badge (`status_badge`) at the top of the interface displaying real-time color-coded states (`⚪ Status: Waiting`, `🟡 Status: Audio/video transcription in progress...`, `🟢 Status: Completed successfully`, `🔴 Status: Transcription interrupted`).
- **Phase Progress Tracking (`gr.Progress`)**: Integrated dynamic phase progress bars to track file expansion, audio conversion/extraction, Whisper transcription steps, and AI assistant query generation.
- **Completion Toast Notifications & Audio Chime**: Triggered native popup toast notifications (`gr.Info`) and a 3-tone Web Audio API sound chime upon completion of transcription or assistant queries.
- **Centralized Output Directory for MP3 Files**: All extracted audio, converted `.mp3` files (from WhatsApp `.opus` or video containers), and copied source `.mp3` files are saved directly into the designated timestamped output directory (`output_dir`), preserving folder hierarchy relative to `common_root`.
- **Complete Externalized Localization**: All status messages, progress labels, and completion toasts are fully localized in `settings/locales.yaml` for English and Italian.
- **Full Field Reset**: Updated the Reset button to reset all UI fields, including returning the status badge to `⚪ Status: Waiting`.

## [1.3.1] - 2026-07-24

### Added
- **Custom Output Folder & Hierarchical Saving**: Added output folder selection (`output_dir_display` & `📁 Choose output folder` button). Processed audio/video files are saved in a timestamped folder (`YYYY-MM-DD_HH-MM-SS_transcription`), preserving the original folder hierarchy of input files.
- **Unified File Naming & Combined Session File**: All transcriptions are saved with the suffix `_transcription.<ext>`. A combined transcript file (`YYYY-MM-DD_HH-MM-SS_transcription.<ext>`) containing all session transcriptions is also automatically saved.

## [1.3.0] - 2026-07-10

### Added

- **File/Folder Selection Refactor**: Replaced old selection method with two dedicated buttons: "Sfoglia Audio/Video..." and "Sfoglia Cartella...". Selecting a folder will recursively find all supported audio and video files inside it and add them to the file list.
- **Output Format Selection**: Added options to choose between `.txt` (raw text transcription) and `.md` (retains headers, bold, paragraphs, and markdown syntax).
- **Execution Interruption (Stop Buttons)**: Added dedicated "Stop" buttons next to the transcription and AI assistant query actions, allowing real-time cancellation of ongoing tasks.
- **Gradio Upgrade**: Upgraded Gradio to version `6.20.0` to resolve Starlette/Gradio deprecation warnings and improve robustness.

## [1.2.0] - 2026-06-30

### Added

- **AI Assistant Response Language Selector**: Added a language radio button (`Italiano` / `English`, default: `Italiano`) inside the 🤖 AI Assistant (Post-Processing) section. The selected language controls the language in which the LLM (Gemini, Ollama, LM Studio) is instructed to reply, independently from the UI display language.
- English system prompt variants (`SYSTEM_PROMPT_EN`, `SYSTEM_PROMPT_FIX_TEXT_EN`) added to `llms.py`.
- `response_language` parameter added to `query_gemini`, `query_ollama`, and `query_lmstudio` in `llms.py`.
- Locale key `response_language_label` added (English + Italian) to `settings/locales.yaml`.

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
