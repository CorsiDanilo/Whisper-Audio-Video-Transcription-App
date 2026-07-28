# Changelog

## [2.0.0] - 2026-07-28

### Added
- **Smart GUI Installer**: Created a multi-step graphical setup wizard with automatic OS and hardware detection.
- **Automated Dependency Management**: The installer automatically downloads FFmpeg and CUDA runtime libraries on demand based on the user's hardware, eliminating complex manual setups.
- **Standalone Executable Builds**: Added automated PyInstaller build scripts to generate a fully portable .exe bundle with embedded dependencies.
- **In-App Config Editor**: Refactored the UI to include a fullscreen "Config Files Editor" modal to seamlessly edit `settings/default.yaml` and `secrets/gemini.yaml` from within the app.

### Changed
- **Increased Default Window Size**: Adjusted the default pywebview window to 1280x850 for better visibility of the transcription UI and configuration panels.
