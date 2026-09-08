"""
remote_transcription.py - Remote Whisper STT client for Whisper Utility.

Communicates with a self-hosted Whisper STT service (e.g. at http://192.168.1.32:8088):
- Performs health checks via GET /health
- Retrieves available and active models via GET /api/models
- Hot-swaps the active model in server memory via POST /api/models/load
- Transcribes audio files EXCLUSIVELY using POST /v1/audio/transcriptions (OpenAI standard)
"""

import os
import time
import logging
from typing import Tuple, List, Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_CONNECT = 6
DEFAULT_TIMEOUT_TRANSCRIBE = 1800  # 30 minutes for large audio files


def check_server_health(server_url: str, retries: int = 3, retry_delay: float = 1.0) -> Tuple[bool, Dict[str, Any], str]:
    """Check connectivity and health of the remote Whisper STT server with retries.

    Args:
        server_url: Base URL (e.g. 'http://192.168.1.32:8088')
        retries: Number of retry attempts before reporting failure
        retry_delay: Delay between retries in seconds

    Returns:
        (is_healthy: bool, details: dict, error_message: str)
    """
    clean_url = server_url.rstrip("/")
    target = f"{clean_url}/health"
    last_err = ""

    for attempt in range(max(1, retries)):
        try:
            resp = requests.get(target, timeout=DEFAULT_TIMEOUT_CONNECT)
            if resp.status_code == 200:
                data = resp.json()
                return True, data, ""
            last_err = f"Server returned status {resp.status_code}: {resp.text[:100]}"
        except requests.exceptions.ConnectionError:
            last_err = f"Impossibile connettersi a {clean_url}. Verifica che il server Docker/Portainer sia attivo."
        except requests.exceptions.Timeout:
            last_err = f"Timeout di connessione verso {clean_url}."
        except Exception as e:
            last_err = str(e)

        if attempt < retries - 1:
            time.sleep(retry_delay)

    return False, {}, last_err


def fetch_remote_models(server_url: str, only_downloaded: bool = True, retries: int = 3, retry_delay: float = 1.0) -> Tuple[List[str], str, List[Dict[str, Any]], str]:
    """Retrieve available models and active model from remote server via GET /api/models with retries.
    When only_downloaded is True, returns ONLY models that are cached/downloaded on the NAS.

    Returns:
        (model_choices: list of str, active_model: str, models_data: list of dict, error: str)
    """
    clean_url = server_url.rstrip("/")
    target = f"{clean_url}/api/models"
    last_err = ""

    for attempt in range(max(1, retries)):
        try:
            resp = requests.get(target, timeout=DEFAULT_TIMEOUT_CONNECT)
            if resp.status_code == 200:
                data = resp.json()
                active_model = data.get("active_model", "")
                models_list = data.get("models", [])

                choices = []
                for m in models_list:
                    m_id = m.get("id") or m.get("name")
                    if not m_id:
                        continue
                    if only_downloaded:
                        is_downloaded = m.get("is_downloaded") is True or m.get("status") in ("active", "cached")
                        if is_downloaded:
                            choices.append(m_id)
                    else:
                        choices.append(m_id)

                if not choices and active_model:
                    choices = [active_model]

                return choices, active_model, models_list, ""
            last_err = f"Status {resp.status_code}: {resp.text[:100]}"
        except Exception as e:
            last_err = str(e)

        if attempt < retries - 1:
            time.sleep(retry_delay)

    logger.warning(f"Error fetching remote models from {clean_url} after {retries} retries: {last_err}")
    return [], "", [], last_err


def fetch_remote_settings(server_url: str, retries: int = 3, retry_delay: float = 1.0) -> Tuple[Dict[str, Any], str]:
    """Retrieve runtime settings from remote server via GET /api/settings or GET /health.

    Returns:
        (settings_dict: dict, error_message: str)
    """
    clean_url = server_url.rstrip("/")
    target = f"{clean_url}/api/settings"
    last_err = ""

    for attempt in range(max(1, retries)):
        try:
            resp = requests.get(target, timeout=DEFAULT_TIMEOUT_CONNECT)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("settings", {}), ""
            last_err = f"Status {resp.status_code}: {resp.text[:100]}"
        except Exception as e:
            last_err = str(e)

        if attempt < retries - 1:
            time.sleep(retry_delay)

    # Fallback to /health
    ok, health, h_err = check_server_health(server_url, retries=1)
    if ok:
        fallback = {
            "WHISPER_MODEL": health.get("model", ""),
            "WHISPER_COMPUTE_TYPE": health.get("compute_type", "int8"),
            "WHISPER_LANGUAGE": health.get("default_language", "auto"),
            "WHISPER_DEVICE": health.get("device", "cpu"),
            "CPU_THREADS": health.get("cpu_threads", 4),
        }
        return fallback, ""

    return {}, last_err or h_err


def update_remote_settings(server_url: str, settings_payload: Dict[str, Any], retries: int = 2) -> Tuple[bool, str]:
    """Send updated settings to remote server via POST /api/settings with retries.

    Args:
        server_url: Remote base URL (e.g. 'http://192.168.1.32:8088')
        settings_payload: Dict of settings to update
        retries: Number of retry attempts

    Returns:
        (success: bool, message: str)
    """
    clean_url = server_url.rstrip("/")
    target = f"{clean_url}/api/settings"
    last_err = ""

    for attempt in range(max(1, retries)):
        try:
            resp = requests.post(target, json=settings_payload, timeout=DEFAULT_TIMEOUT_CONNECT)
            if resp.status_code == 200:
                data = resp.json()
                return True, data.get("message", "Impostazioni aggiornate sul server.")
            last_err = f"Errore {resp.status_code}: {resp.text}"
        except Exception as e:
            last_err = str(e)

        if attempt < retries - 1:
            time.sleep(1.0)

    logger.warning(f"Failed to update remote settings: {last_err}")
    return False, last_err


def switch_remote_model(server_url: str, model_name: str, compute_type: Optional[str] = None, retries: int = 2, timeout: int = 90) -> Tuple[bool, str]:
    """Hot-swap the active Whisper model in server memory via POST /api/models/load with retry support.

    Args:
        server_url: Base URL (e.g. 'http://192.168.1.32:8088')
        model_name: Model identifier (e.g. 'large-v3-turbo', 'base', 'small')
        compute_type: Optional compute precision ('int8', 'float16', 'auto')
        retries: Number of retry attempts
        timeout: Timeout in seconds for model loading

    Returns:
        (success: bool, message: str)
    """
    clean_url = server_url.rstrip("/")
    target = f"{clean_url}/api/models/load"
    payload: Dict[str, Any] = {"model": model_name.strip()}
    if compute_type:
        payload["compute_type"] = compute_type.strip()

    last_err = ""
    for attempt in range(max(1, retries)):
        try:
            resp = requests.post(target, json=payload, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                return True, data.get("message", f"Modello '{model_name}' caricato con successo sul server.")
            last_err = f"Errore {resp.status_code}: {resp.text}"
        except Exception as e:
            last_err = str(e)

        if attempt < retries - 1:
            time.sleep(2.0)

    logger.error(f"Error switching remote model after {retries} retries: {last_err}")
    return False, last_err


def transcribe_remote_file(
    file_path: str,
    server_url: str,
    language: Optional[str] = None,
    temperature: float = 0.0,
    prompt: Optional[str] = None,
    beam_size: int = 2,
    condition_on_previous_text: bool = True,
    word_timestamps: bool = False,
    timeout: int = DEFAULT_TIMEOUT_TRANSCRIBE,
) -> Tuple[str, Dict[str, Any]]:
    """Transcribe an audio file using EXCLUSIVELY POST /v1/audio/transcriptions.

    Args:
        file_path: Absolute or local path to audio file (e.g. .mp3, .wav)
        server_url: Remote base URL (e.g. 'http://192.168.1.32:8088')
        language: Language code (e.g. 'it', 'en') or None for auto
        temperature: Sampling temperature
        prompt: Optional initial prompt
        beam_size: Beam search width (1 to 5)
        condition_on_previous_text: Whether to condition next chunk on previous text
        word_timestamps: Whether to extract word-level timestamps
        timeout: Maximum seconds to wait for transcription

    Returns:
        (transcription_text: str, metadata: dict)
    """
    clean_url = server_url.rstrip("/")
    endpoint = f"{clean_url}/v1/audio/transcriptions"

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File audio non trovato: {file_path}")

    filename = os.path.basename(file_path)
    file_ext = os.path.splitext(filename)[1].lower()
    
    # Determine basic mime type
    mime_type = "audio/mpeg" if file_ext == ".mp3" else "audio/wav"

    data: Dict[str, Any] = {
        "model": "whisper-1",
        "response_format": "verbose_json",
        "temperature": str(temperature) if temperature is not None else "0.0",
        "beam_size": str(beam_size) if beam_size is not None else "2",
        "condition_on_previous_text": "true" if condition_on_previous_text else "false",
        "word_timestamps": "true" if word_timestamps else "false",
    }

    if word_timestamps:
        data["timestamp_granularities"] = "word"

    if language and language.strip() and language.strip().lower() != "auto":
        data["language"] = language.strip().lower()

    if prompt and prompt.strip():
        data["prompt"] = prompt.strip()

    logger.info(f"Invio file '{filename}' a {endpoint} (lingua: {data.get('language', 'auto')}, beam: {data['beam_size']}, word_ts: {data['word_timestamps']})...")

    with open(file_path, "rb") as f:
        files = {
            "file": (filename, f, mime_type)
        }
        resp = requests.post(endpoint, files=files, data=data, timeout=timeout)

    if resp.status_code != 200:
        err_detail = resp.text
        try:
            err_json = resp.json()
            err_detail = err_json.get("detail", resp.text)
        except Exception:
            pass
        raise RuntimeError(f"Errore dal server remoto ({resp.status_code}): {err_detail}")

    result_json = resp.json()
    transcribed_text = result_json.get("text", "").strip()
    metadata = {
        "language": result_json.get("language", language or "unknown"),
        "duration": result_json.get("duration", 0.0),
        "task": result_json.get("task", "transcribe"),
        "segments": result_json.get("segments", []),
        "words": result_json.get("words", []),
    }

    return transcribed_text, metadata

