import os
import logging
import yaml

WHISPER_MODEL_FALLBACKS = [
    "tiny.en",
    "tiny",
    "base.en",
    "base",
    "small.en",
    "small",
    "medium.en",
    "medium",
    "large-v1",
    "large-v2",
    "large-v3",
    "large",
    "distil-large-v2",
    "distil-medium.en",
    "distil-small.en",
    "distil-large-v3",
    "distil-large-v3.5",
    "large-v3-turbo",
    "turbo",
]

def get_whisper_model_choices():
    """Return faster-whisper model aliases supported by the installed package."""
    try:
        from faster_whisper.utils import available_models
        return available_models()
    except Exception as e:
        logging.debug(f"Could not load faster-whisper model aliases: {e}")
        return WHISPER_MODEL_FALLBACKS

def load_default_values():
    """Carica i valori di default da default_values.yaml."""
    with open("default_values/default_values.yaml", "r") as ymlfile:
        default_values = yaml.safe_load(ymlfile)
    default_values["configurations"]["models"] = get_whisper_model_choices()
    return default_values

def load_default_config():
    """Carica la configurazione di default da settings/default.yaml."""
    with open("settings/default.yaml", "r") as ymlfile:
        return yaml.safe_load(ymlfile)
    
def get_gemini_api_key():
    """Retrieve the Gemini API key without logging or exposing the secret."""
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key:
        return env_key
    try:
        with open("config/gemini.yaml", "r", encoding="utf-8") as ymlfile:
            gemini = yaml.safe_load(ymlfile)
        if isinstance(gemini, dict):
            key = gemini.get("gemini_api_key")
            if key:
                return key
    except (FileNotFoundError, KeyError, yaml.YAMLError):
        return None
    return None

def setup_logging(log_file="whisper.log"):
    """Configura il logging: elimina il file di log precedente e imposta i gestori."""
    if os.path.exists(log_file):
        os.remove(log_file)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
