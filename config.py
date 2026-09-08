import os
import sys
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

def get_app_config_dir() -> str:
    """Return OS-native system AppData folder for WhisperUtility configurations."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "WhisperUtility")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/WhisperUtility")
    else:
        return os.path.expanduser("~/.config/whisper-utility")

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
    sys_val_path = os.path.join(get_app_config_dir(), "settings", "default_values.yaml")
    if os.path.exists(sys_val_path):
        try:
            with open(sys_val_path, "r", encoding="utf-8") as ymlfile:
                default_values = yaml.safe_load(ymlfile)
        except Exception:
            default_values = None
    else:
        default_values = None

    if not isinstance(default_values, dict):
        with open("settings/default_values.yaml", "r", encoding="utf-8") as ymlfile:
            default_values = yaml.safe_load(ymlfile)
        
    # Inject security limits dynamically into the environment variables
    max_duration = default_values.get("default_values", {}).get("max_media_duration_seconds")
    if max_duration is not None:
        os.environ["WHISPER_MAX_MEDIA_DURATION_SECONDS"] = str(max_duration)

    default_values["configurations"]["models"] = get_whisper_model_choices()
    return default_values

def load_default_config():
    """Carica la configurazione di default dando precedenza alla cartella dati di sistema AppData."""
    data = {}
    sys_config_path = os.path.join(get_app_config_dir(), "settings", "default.yaml")
    if os.path.exists(sys_config_path):
        try:
            with open(sys_config_path, "r", encoding="utf-8") as ymlfile:
                loaded = yaml.safe_load(ymlfile)
                if isinstance(loaded, dict):
                    data = loaded
        except Exception as e:
            logging.warning(f"Error loading system config from {sys_config_path}: {e}")

    if not data:
        local_path = "settings/default.yaml"
        if os.path.exists(local_path):
            with open(local_path, "r", encoding="utf-8") as ymlfile:
                loaded = yaml.safe_load(ymlfile)
                if isinstance(loaded, dict):
                    data = loaded

    data.setdefault("transcription_backend", "local")
    data.setdefault("remote_server_url", "http://192.168.1.32:8088")
    return data
    
def get_gemini_api_key():
    """Retrieve the Gemini API key without logging or exposing the secret."""
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key:
        return env_key

    # Check system AppData secrets/gemini.yaml
    sys_secret_path = os.path.join(get_app_config_dir(), "secrets", "gemini.yaml")
    if os.path.exists(sys_secret_path):
        try:
            with open(sys_secret_path, "r", encoding="utf-8") as ymlfile:
                gemini = yaml.safe_load(ymlfile)
            if isinstance(gemini, dict):
                key = gemini.get("gemini_api_key")
                if key:
                    return key
        except Exception:
            pass

    # Fallback to local secrets/gemini.yaml
    try:
        with open("secrets/gemini.yaml", "r", encoding="utf-8") as ymlfile:
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
        try:
            os.remove(log_file)
        except OSError:
            pass
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

_locales = None
_current_language = None

def get_translation(key):
    """Retrieve a translated string based on ui_language."""
    global _locales, _current_language
    
    if _locales is None:
        try:
            with open("settings/locales.yaml", "r", encoding="utf-8") as f:
                _locales = yaml.safe_load(f) or {}
        except Exception as e:
            logging.error(f"Error loading locales: {e}")
            _locales = {}
            
    if _current_language is None:
        try:
            config = load_default_config()
            _current_language = config.get("ui_language", "english")
        except Exception:
            _current_language = "english"
            
    lang_dict = _locales.get(_current_language, {})
    if key in lang_dict:
        return lang_dict[key]
        
    english_dict = _locales.get("english", {})
    if key in english_dict:
        return english_dict[key]
        
    return key
