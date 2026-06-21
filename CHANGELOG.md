# Changelog

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
