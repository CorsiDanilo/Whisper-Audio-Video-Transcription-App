[🏠 Index](./README.md) | [Next ➡](./02-structure.md)

# Project Overview

`whisper-utility` is a desktop-based application designed to streamline the transcription of audio and video files into text, followed by intelligent processing using Large Language Models (LLMs). The project leverages `faster-whisper` for high-performance speech-to-text inference and provides a user-friendly interface built with Gradio and `pywebview`.

The utility is engineered to handle diverse input formats, including WhatsApp audio exports and various video containers, by automatically normalizing them into MP3 format before processing.

## Key Features and Capabilities

*   **High-Performance Dual Engine:** Seamlessly switch between local `faster-whisper` execution (with CPU/CUDA acceleration) and offloading transcription to a self-hosted Whisper STT REST server (e.g., Docker container on NAS/homelab).
*   **Automated Preprocessing:** The `audio_processing.py` module detects file types and automatically converts WhatsApp `.opus` files and video formats into compatible MP3 audio.
*   **LLM Integration:** Seamlessly integrates with Google Gemini, local Ollama, and LM Studio instances via `llms.py`.
*   **Desktop-Native Experience:** Uses `pywebview` to wrap the Gradio interface, providing a standalone application feel.
*   **Configurable Environment:** Supports granular control over transcription parameters (temperature, beam size, word timestamps, VAD thresholds, initial prompt) via YAML configuration files located in `settings/`.
*   **Portable Deployment:** Packaged as a standalone executable using `PyInstaller` with custom hooks for Gradio and multiprocessing support.

## Technology Stack

| Category | Technology |
| :--- | :--- |
| **Language** | Python 3.x |
| **UI Framework** | Gradio |
| **Desktop Wrapper** | pywebview |
| **Transcription Engine** | faster-whisper (Local) / FastAPI REST (Remote) |
| **LLM Clients** | Google GenAI SDK, Requests (for Ollama/LM Studio) |
| **Packaging** | PyInstaller |
| **Configuration** | PyYAML |

## High-Level Architecture

The application follows a modular architecture where the UI layer orchestrates data flow between the audio processing pipeline, the local/remote transcription engines, and the LLM service layer.

```mermaid
graph TD
    UI[ui.py - Gradio/pywebview] -->|Local Engine| Trans[transcription.py]
    UI -->|Remote Engine| RemoteTrans[remote_transcription.py]
    UI -->|Query/Prompt| LLM[llms.py]
    
    subgraph "Local Processing Pipeline"
        Trans -->|Convert| Audio[audio_processing.py]
        Trans -->|Inference| Whisper[faster-whisper]
    end

    subgraph "Remote Processing Service"
        RemoteTrans -->|REST API /v1/audio/transcriptions| RemoteServer[Whisper STT Server]
    end
    
    subgraph "LLM Services"
        LLM -->|API| Gemini[Google Gemini]
        LLM -->|Local API| Ollama[Ollama]
        LLM -->|Local API| LMStudio[LM Studio]
    end
    
    Config[config.py] -.->|Load Settings| UI
    Config -.->|Load Settings| Trans
```

## Component Reference

| File | Primary Responsibility |
| :--- | :--- |
| `app_main.py` | Entry point for the PyInstaller executable. |
| `ui.py` | Gradio interface definition, backend toggling, and event handling. |
| `transcription.py` | Local Faster-Whisper model loading and inference execution. |
| `remote_transcription.py` | Remote Whisper STT REST client (model switching, health, transcription). |
| `audio_processing.py` | File conversion logic (FFmpeg wrappers). |
| `llms.py` | API communication with Gemini, Ollama, and LM Studio. |
| `config.py` | YAML configuration loading and logging setup. |

## Quick Links

*   **Configuration:** See `settings/default.yaml` for default transcription parameters.
*   **Build Instructions:** Refer to `build_windows.sh` or `installer.bat` for packaging the application.
*   **Dependencies:** See `requirements_cpu.txt` or `requirements_gpu.txt` for environment setup.
*   **Hooks:** Custom PyInstaller hooks are located in `hooks/hook-gradio.py`.

[🏠 Index](./README.md) | [Next ➡](./02-structure.md)