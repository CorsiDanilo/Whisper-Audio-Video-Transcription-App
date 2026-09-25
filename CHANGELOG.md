# Changelog

## [3.2.2] - 2026-09-25

### Modifiche
- **Rimozione dropdown modello duplicato nel backend remoto**: Il selettore `remote_model` presente nella riga superiore dell'interfaccia (accanto all'URL del server) è stato eliminato. Il modello attivo viene ora selezionato esclusivamente tramite il dropdown `Whisper Model` all'interno di `⚙️ Configurazioni Avanzate`, rimuovendo ogni ridondanza visiva.
- **Nuovo widget di stato connessione**: Al posto del dropdown rimosso viene ora mostrata una `gr.Textbox` in sola lettura (`remote_status`) che riporta in tempo reale lo stato della connessione con il server remoto:
  - `⚪ In attesa di connessione...` — stato iniziale all'avvio o al passaggio al backend remoto.
  - `🟢 Connessione stabilita con successo ({model} - {device})` — dopo un test di connessione riuscito.
  - `🔴 Errore connessione: {error}` — in caso di fallimento della connessione.
- **Rimozione del blocco di rete all'avvio**: L'inizializzazione della UI non effettua più chiamate HTTP (`fetch_remote_models`, `check_server_health`) al lancio dell'applicazione. L'app si avvia immediatamente senza ritardi di rete, anche se il backend predefinito è quello remoto.
- **Rimozione del badge di stato Markdown** (`remote_status_badge`): sostituito dalla nuova `remote_status` Textbox. Il formato dei messaggi è stato aggiornato da Markdown a testo piano per compatibilità con il widget.
- **Eliminazione di `_on_remote_model_change`**: L'handler dedicato al cambio del dropdown `remote_model` è stato rimosso insieme alla registrazione dell'evento `remote_model.change`. La logica di switch del modello sul server è interamente gestita da `_on_whisper_model_change`.
- **Aggiornamento handler `_on_backend_change`**: Ora emette un solo output per lo stato connessione (`remote_status`) invece di due output separati (`remote_status_badge` + `remote_model`). Al passaggio al backend remoto imposta lo stato su "In attesa di connessione".
- **Aggiornamento handler `_test_remote_conn`**: Passa da 8 a 7 output, eliminando l'aggiornamento ridondante di `remote_model`; popola solo `whisper_model` con i modelli disponibili sul server.
- **Aggiornamento handler `_on_whisper_model_change`**: Restituisce un singolo valore (`remote_status`) invece di una coppia.
- **Aggiornamento handler `_on_compute_type_change`**: L'output punta ora a `remote_status` anziché al precedente `remote_status_badge`.

### Localizzazione
- Aggiunte 4 nuove chiavi in `settings/locales.yaml` (inglese + italiano):
  - `remote_status_label` — etichetta del widget di stato (`Connection Status` / `Stato Connessione`).
  - `remote_status_waiting` — testo di attesa (`⚪ Waiting for connection...` / `⚪ In attesa di connessione...`).
  - `remote_connected_status` — messaggio di connessione riuscita (formato testo piano, senza Markdown).
  - `remote_error_status` — messaggio di errore connessione (formato testo piano, senza Markdown).

## [3.2.1] - 2026-09-10

### Added
- **Interactive Auto-Updater & Reinstall Flow**:
  - Added real-time in-app status updates to the updater panel in `ui.py` so checking or launching setup immediately updates `update_status_md` with clear feedback.
  - Added support for reinstalling or repairing the current version when the application is already up to date, avoiding dead-end UI states.
  - Enhanced detached process spawning in `updater.py` with `subprocess.CREATE_NEW_PROCESS_GROUP`, `close_fds=True`, and `pythonw.exe` preference on Windows to eliminate console pop-up flicker and fix execution failures in virtual environment wrappers.
  - Added frozen standalone detection to find setup executables (`WhisperUtilitySetup_Windows.exe`, `WhisperUtilitySetup.exe`) or seamlessly fallback to the official GitHub releases page in the default web browser.
- **Automatic Model Fallback & Resiliency for Google Gemini**: Implemented sequential cascading fallback in `query_gemini` (`llms.py`). If a requested or default model fails (e.g., HTTP 429 quota exhaustion, HTTP 500 upstream server error, HTTP 404 unsupported model), the system immediately issues a transient alert to the UI and retries with the next best available model in order (`gemini-flash-latest`, `gemini-3.8-flash`, `gemini-3.7-flash`, etc.) without interrupting transcription workflows or crashing the application.
- **In-Memory Models Cache**: Added a 15-minute in-memory cache to `get_sorted_gemini_models` in `llms.py` to eliminate redundant remote Google API roundtrips (`client.models.list()`) on consecutive requests and dropdown interactions.

### Changed
- **Comprehensive English Codebase Localization**: Translated all internal comments, docstrings, and logging messages in `llms.py` and `scripts/list_gemini_models.py` into English for clean, professional consistency.
- **Console Output Safety**: Replaced problematic Unicode alert symbols with standard ASCII tags in terminal notices to ensure complete cross-platform compatibility on Windows consoles without UTF-8 reconfiguration.

## [3.2.0] - 2026-09-08

### Added
- **Remote Whisper STT Service Integration**: Added full client integration with a self-hosted Whisper STT REST server (e.g., Docker container running on a NAS or server). Users can seamlessly choose between local execution (`🖥️ Local (Faster-Whisper)`) and remote execution (`🌐 Remote Server`).
- **Standardized REST Client (`remote_transcription.py`)**: Implemented remote client communicating over standard endpoints:
  - `GET /health` for server health and status monitoring.
  - `GET /api/models` for querying model caches (with support for filtering only cached/downloaded models on the server).
  - `POST /api/models/load` for real-time model and compute precision hot-swapping in server memory.
  - `POST /v1/audio/transcriptions` for standard multipart/form-data audio and video file transcription with segment reconstruction.
- **Dynamic UI Mode Toggling**: The Gradio interface dynamically shifts controls based on the selected backend:
  - When **Local** is selected, local hardware options (`device`, `cpu_threads`, `num_workers`, `batch_size`, `beam_size`, etc.) and the "Save configurations" button are displayed.
  - When **Remote Server** is selected, local hardware controls and the save button are cleanly hidden, and remote controls (Server URL, active remote model dropdown, "Test Connection" button, VAD speech threshold, silence timeout, and initial prompt) are revealed.
- **Initial Prompt & Vocabulary Guidance**: Added support for passing custom vocabulary, jargon, acronyms, and punctuation guidance to Whisper for both local and remote transcriptions.
- **Connection Diagnostics with Retries**: Implemented robust exponential backoff and retry mechanisms for remote health checks and model synchronization with immediate user-friendly feedback badges.

### Changed
- **Configurable Default Configuration File**: Fully documented `settings/default.yaml` with exhaustive English comments, detailed descriptions, and all available options for every parameter.
- **Relocated Output Format Radio**: Moved the output format selection (`.txt`, `.md`) next to the output directory selector for a cleaner, unified file output section.
- **Cleaned Up Server Resource Management**: CPU execution threads are now managed strictly at the Docker environment level on the NAS container, eliminating redundant remote CPU thread controls.

### Fixed
- **UI State and Variable Scoping**: Fixed variable scoping across event handlers (`UnboundLocalError` on translation helper `_`) and ensured smooth dropdown updates when switching active models.
- **Connection Test Button Visibility**: Ensured the "Test Connection" button is strictly visible only when the remote server backend is active.

## [3.1.0] - 2026-08-06

### Changed
- **Tabbed Interface Layout**: Redesigned the main interface into clean "🎙️ Transcription" and "⚙️ Settings" tabs to eliminate layout clutter and prevent double scrollbars.
- **UI Reset & Field Controls**: Moved the "Reset fields" button exclusively inside the Transcription tab for intuitive workflow, and restricted interface language choices strictly to supported locales (`english` and `italian`).

### Fixed
- **Complete UI Localization (i18n)**: Resolved missing and hardcoded translation strings across the application, including update status badges and modal labels.
- **Gemini API & Config Resolution**: Fixed unnecessary remote API calls during field resets and resolved configuration path precedence between local files and system AppData.
- **Process & Log Lock Management**: Prevented `PermissionError` file lock issues on `whisper.log` by ensuring proper background process cleanup on restart.

## [3.0.0] - 2026-08-05

### Added
- **Installer Configuration Customization Page**: Added a new wizard screen (`_show_config`) in `installer/gui.py` allowing users to configure Gemini API Key, UI Language, Whisper Model, Computation Device (CUDA/CPU), and CPU Threads during setup.
- **Non-Destructive Configuration Preservation**: Implemented `installer/config_manager.py` to automatically detect existing `settings/default.yaml` and `secrets/gemini.yaml` files, pre-fill form fields, and merge new user choices while preserving all custom parameters.
- **OS-Native System AppData Storage**: Added `get_app_config_dir()` in `config.py` to store configuration files in native system AppData locations (`%APPDATA%\WhisperUtility` on Windows, `~/Library/Application Support/WhisperUtility` on macOS, and `~/.config/whisper-utility` on Linux), separating user settings completely from application binaries for risk-free updates.
- **In-App Auto-Updater & Version Checker**: Created `updater.py` module and integrated an interactive update control panel into the Gradio UI (`ui.py`). Users can check for new releases against remote GitHub manifests and launch the graphical installer directly from the app.
- **Antivirus False-Positive Protection**: Updated PyInstaller packaging guidelines to `--onedir` directory mode, preventing antivirus engines (like Bitdefender and Windows Defender) from triggering false-positive heuristic blocks.
- **Automated Test Suite**: Added complete test suite (`tests/test_system_config.py`, `tests/test_updater.py`, `tests/test_updater_ui.py`, `tests/test_installer_config_manager.py`, `tests/test_installer_gui.py`, `tests/test_installer_locales.py`).

## [2.1.1] - 2026-07-29

### Fixed
- **AI Models Reset & Fallback Fix**: Fixed `reset_fields()` in `ui.py` to reset AI Provider (`provider`), Brand Radio (`google_brand_radio`), and Gemini Model (`gemini_model`) to their default values (`gemini-flash-latest`). Added guaranteed inclusion of `gemini-flash-latest` and `gemini-flash-lite-latest` in `get_sorted_gemini_models()` in `llms.py` so default options are always present in UI dropdown choices.
- **Rancher Desktop BuildKit Compatibility**: Set `DOCKER_BUILDKIT=0` and `COMPOSE_DOCKER_CLI_BUILD=0` in `run.bat` and `run.sh` to bypass containerized BuildKit cgroup v2 permission errors (`OCI permission denied`) on Rancher Desktop.

### Added
- **`uv` Package Manager Integration**: Integrated `uv` in `Dockerfile.cpu` and `Dockerfile.gpu` (`COPY --from=ghcr.io/astral-sh/uv:latest`) for lightning-fast container builds and added `astral-sh/setup-uv@v5` to GitHub Actions workflow.
- **Python Version Management Documentation**: Added `uv venv --python 3.11` guide in `README.md` for automatic Python version management and ultra-fast local setups.

## [2.1.0] - 2026-07-29

### Added
- **Docker Support & Cross-Platform Launchers**: Added `Dockerfile.cpu`, `Dockerfile.gpu`, `docker-compose.yml`, `run.bat` (Windows), and `run.sh` (Linux/macOS) for containerized deployment.
- **Automated GPU Runtime Detection**: Added hardware (`nvidia-smi`) and Docker GPU runtime (`--gpus all`) verification in `run.bat` and `run.sh`. Automatically runs GPU container (`--profile gpu`) if supported, or gracefully falls back to CPU (`--profile cpu`) with tips for Docker Desktop and Rancher Desktop users.
- **Container Requirements & `uv` Integration**: Created `requirements_docker_cpu.txt` and `requirements_docker_gpu.txt` optimized for docker build layers, and integrated `uv` into Dockerfiles for ultra-fast package resolution and installation.

### Changed
- **Documentation**: Updated `README.md` with complete Docker deployment instructions, Rancher Desktop / Docker Desktop GPU compatibility notes, and `uv` setup guide specifying Python version management (`uv venv --python 3.11`).
- **Installer Manifest**: Updated `installer/manifest.json` component release targets to `v2.1.0`.

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
- Ristrutturato il layout in due tab principali: **🎙️ Trascrizione** e **⚙️ Impostazioni**, rimuovendo il pannello laterale a comparsa.
