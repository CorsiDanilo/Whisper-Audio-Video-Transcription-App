[⬅ Previous](./04-cli-commands.md) | [🏠 Index](./README.md) | [Next ➡](./06-installation.md)

# Deployment & CI/CD

## Overview

`whisper-utility` is a local desktop application distributed as a standalone package built using PyInstaller. Releases are published to GitHub via an automated CI/CD pipeline that builds executables for all supported platforms.

## GitHub Actions Release Pipeline

The release workflow (`.github/workflows/release.yml`) is triggered by pushing a version tag matching `v*` (e.g., `v1.0.0`). It runs four parallel jobs — one per target platform — using a matrix strategy.

### Trigger

```bash
git tag v1.0.0
git push origin v1.0.0
```

### Build Matrix

| Job | Runner | Requirements | Output |
| :--- | :--- | :--- | :--- |
| `windows-cpu` | `windows-latest` | `requirements_cpu.txt` | `Whisper-windows-cpu-<tag>.zip` |
| `windows-gpu` | `windows-latest` | `requirements_gpu.txt` | `Whisper-windows-gpu-<tag>.zip` |
| `macos` | `macos-latest` | `requirements_macos.txt` | `Whisper-macos-<tag>.zip` |
| `linux` | `ubuntu-latest` | `requirements_linux.txt` | `Whisper-linux-<tag>.tar.gz` |

Each job also produces a `.sha256` checksum file. All eight artefacts are attached to the GitHub Release automatically.

### Pipeline Steps (per job)

1. **Checkout** the repository
2. **Set up Python 3.11**
3. **Install system dependencies** — `ffmpeg` on all platforms; GTK/WebKit headers on Linux
4. **Install Python dependencies** from the platform-specific requirements file
5. **Build** the executable with `pyinstaller --noconfirm whisper.spec`
6. **Copy runtime assets** (`default_values/`, `settings/`, `faster_whisper/`, `safehttpx/`) into `dist/Whisper/`
7. **Archive** `dist/Whisper/` into a versioned zip or tar.gz
8. **Generate SHA256** checksum
9. **Upload** artefact + checksum to the GitHub Release (release body sourced from `CHANGELOG.md`)

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
1. Add a new entry to `CHANGELOG.md` under `## [x.y.z] - YYYY-MM-DD`
2. Commit the changelog update
3. Push the version tag: `git tag vx.y.z && git push origin vx.y.z`

## Environment Matrix

| Variable | Source | Used by |
| :--- | :--- | :--- |
| `GITHUB_TOKEN` | GitHub Actions secret (automatic) | Release upload |

[⬅ Previous](./04-cli-commands.md) | [🏠 Index](./README.md) | [Next ➡](./06-installation.md)
