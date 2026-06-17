[⬅ Previous](./04-cli-commands.md) | [🏠 Index](./README.md) | [Next ➡](./06-installation.md)

# Deployment & CI/CD

## Overview

`whisper-utility` is a local desktop application designed for Windows systems. It is distributed as a standalone package built using PyInstaller. As a local utility, the project does not employ web server deployments, cloud hosting providers, containerization (such as Docker), or remote CI/CD automation pipelines.

### Release and Distribution Process
1. **Local Build Compilation**: The application is compiled into a standalone Windows executable using PyInstaller. The packaging process can be run via:
   - `build_windows.sh` (for Git Bash / WSL environments)
   - `installer.bat` (standard Windows command prompt)
2. **Asset Copying**: Custom configuration files and default settings directories (`config/`, `default_values/`, `settings/`) along with internal dependencies (`faster_whisper`, `safehttpx`) are copied to the build destination directory (`dist/Whisper/`).
3. **Distribution**: The contents of the `dist/Whisper/` folder are compressed and distributed directly to users.

## Deployment Map

> No deployment or CI/CD configuration detected.

## Environment Matrix

> No environment variables detected.

[⬅ Previous](./04-cli-commands.md) | [🏠 Index](./README.md) | [Next ➡](./06-installation.md)