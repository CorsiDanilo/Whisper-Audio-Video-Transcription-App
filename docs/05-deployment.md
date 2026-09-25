[⬅ Previous](./04-cli-commands.md) | [🏠 Index](./README.md) | [Next ➡](./06-installation.md)

# Deployment & CI/CD

## Overview

`whisper-utility` is a local desktop application distributed as a standalone package built using PyInstaller. Releases are published to GitHub via an automated CI/CD pipeline that builds executables for all supported platforms.

## GitHub Actions Release Pipeline

The release workflow (`.github/workflows/build_installers.yml`) is triggered by pushing a version tag matching `v*` (e.g., `v1.0.0`). It runs three parallel jobs — one per target platform — using a matrix strategy.

### Trigger

```bash
git tag v1.0.0
git push origin v1.0.0
```

### Build Matrix

| Job | Runner | Requirements | Output |
| :--- | :--- | :--- | :--- |
| Windows | `windows-latest` | `requirements_cpu.txt` | `whisper_app_win.zip` |
| macOS | `macos-latest` | `requirements_macos.txt` | `whisper_app_mac.zip` |
| Linux | `ubuntu-latest` | `requirements_linux.txt` | `whisper_app_linux.zip` |

Each job uploads the platform installer and core application archive. The Linux job also uploads `installer/manifest.json` once; all artefacts are attached to the GitHub Release automatically.

### Pipeline Steps (per job)

1. **Checkout** the repository
2. **Set up Python 3.11**
3. **Validate release metadata**: `version.py`, `installer/manifest.json`, and package URLs must match the pushed tag.
4. **Install system dependencies** — `ffmpeg` on all platforms; GTK/WebKit headers on Linux
5. **Install Python dependencies** from the platform-specific requirements file
6. **Build** the core application with `tools/build_release.py`
7. **Build** the platform installer with PyInstaller
8. **Archive** the core application and prepare the installer artefact
9. **Upload** artefacts and `installer/manifest.json` to the GitHub Release (release body sourced from `CHANGELOG.md`)

### GPU Build Note

The Windows GPU build installs `torch`/`torchaudio`/`torchvision` from standard PyPI alongside `ctranslate2`. No CUDA DLLs are bundled — GPU acceleration relies on the user's system CUDA installation at runtime.

## Requirements Files

| File | Platform | Notes |
| :--- | :--- | :--- |
| `requirements_cpu.txt` | Windows (CPU) | No torch |
| `requirements_gpu.txt` | Windows (GPU) | Adds torch, torchaudio, torchvision |
| `requirements_macos.txt` | macOS | No Windows-only packages; adds pyobjc-framework-Cocoa |
| `requirements_linux.txt` | Linux | No Windows-only packages |

## Local Build

For local builds outside of CI, use the existing scripts:

- `build_windows.sh` — Git Bash / WSL environment
- `installer.bat` — native Windows command prompt

Both scripts invoke `pyinstaller --noconfirm whisper.spec` and copy the required runtime assets into `dist/Whisper/`.

## CHANGELOG

The file `CHANGELOG.md` at the repository root tracks all releases in [Keep a Changelog](https://keepachangelog.com/) format. Its content is used as the GitHub Release body automatically.

When preparing a new release:
1. Update `version.py`, `installer/manifest.json`, and `CHANGELOG.md` with the release version.
2. Commit the release metadata and documentation update.
3. Push the version tag: `git tag vx.y.z && git push origin vx.y.z`.

The workflow stops before building if the tag and release metadata do not match. A corrective rebuild may reuse an existing version tag only when the tag is deliberately moved to the corrected commit.

## Environment Matrix

| Variable | Source | Used by |
| :--- | :--- | :--- |
| `GITHUB_TOKEN` | GitHub Actions secret (automatic) | Release upload |

[⬅ Previous](./04-cli-commands.md) | [🏠 Index](./README.md) | [Next ➡](./06-installation.md)
