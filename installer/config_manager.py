import os
import yaml
from typing import Dict, Any
from config import get_app_config_dir

DEFAULT_SETTINGS: Dict[str, Any] = {
    "ui_language": "italian",
    "whisper_model": "large-v3",
    "device": "cuda",
    "cpu_threads": 6,
    "num_workers": 1,
    "language": "it",
    "compute_type": "auto",
    "temperature": 0.0,
    "beam_size": 5,
    "batch_size": 8,
    "condition_on_previous_text": True,
    "word_timestamps": False,
    "gemini_model": "gemini-flash-latest",
    "lmstudio_timeout": 300,
    "ollama_timeout": 300,
}


def load_existing_configs(install_dir: str) -> Dict[str, Any]:
    """
    Check install_dir and system AppData for pre-existing secrets/gemini.yaml and settings/default.yaml.
    Return a dict containing:
      - has_existing: bool
      - gemini_api_key: str
      - settings: dict of configuration options merged with defaults
    """
    sys_dir = get_app_config_dir()
    search_dirs = [install_dir, sys_dir]

    has_existing = False
    gemini_key = ""
    settings = dict(DEFAULT_SETTINGS)

    for target_dir in search_dirs:
        settings_path = os.path.join(target_dir, "settings", "default.yaml")
        secrets_path = os.path.join(target_dir, "secrets", "gemini.yaml")

        if os.path.exists(secrets_path):
            try:
                with open(secrets_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict) and "gemini_api_key" in data and data.get("gemini_api_key"):
                        gemini_key = str(data.get("gemini_api_key"))
                        has_existing = True
            except Exception:
                pass

        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        settings.update(data)
                        has_existing = True
            except Exception:
                pass

    return {
        "has_existing": has_existing,
        "gemini_api_key": gemini_key,
        "settings": settings,
    }


def save_merged_configs(
    install_dir: str,
    gemini_api_key: str,
    ui_language: str,
    whisper_model: str,
    device: str,
    cpu_threads: int,
) -> None:
    """
    Save or merge user configuration choices into install_dir AND system AppData directory.
    Preserves all existing keys in settings/default.yaml and secrets/gemini.yaml.
    """
    target_dirs = [install_dir, get_app_config_dir()]

    for target_dir in target_dirs:
        try:
            settings_dir = os.path.join(target_dir, "settings")
            secrets_dir = os.path.join(target_dir, "secrets")

            os.makedirs(settings_dir, exist_ok=True)
            os.makedirs(secrets_dir, exist_ok=True)

            settings_path = os.path.join(settings_dir, "default.yaml")
            secrets_path = os.path.join(secrets_dir, "gemini.yaml")

            # 1. Update settings/default.yaml
            current_settings = dict(DEFAULT_SETTINGS)
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, "r", encoding="utf-8") as f:
                        existing = yaml.safe_load(f)
                        if isinstance(existing, dict):
                            current_settings.update(existing)
                except Exception:
                    pass

            current_settings["ui_language"] = ui_language
            current_settings["whisper_model"] = whisper_model
            current_settings["device"] = device
            current_settings["cpu_threads"] = int(cpu_threads)

            with open(settings_path, "w", encoding="utf-8") as f:
                yaml.dump(current_settings, f, sort_keys=False, allow_unicode=True)

            # 2. Update secrets/gemini.yaml
            current_secrets: Dict[str, Any] = {}
            if os.path.exists(secrets_path):
                try:
                    with open(secrets_path, "r", encoding="utf-8") as f:
                        existing_sec = yaml.safe_load(f)
                        if isinstance(existing_sec, dict):
                            current_secrets.update(existing_sec)
                except Exception:
                    pass

            if gemini_api_key or current_secrets or not os.path.exists(secrets_path):
                current_secrets["gemini_api_key"] = gemini_api_key.strip()
                with open(secrets_path, "w", encoding="utf-8") as f:
                    yaml.dump(current_secrets, f, sort_keys=False, allow_unicode=True)
        except Exception as exc:
            pass
