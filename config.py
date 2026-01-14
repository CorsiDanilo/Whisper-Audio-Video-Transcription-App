import os
import logging
import yaml

def load_default_values():
    """Carica i valori di default da default_values.yaml."""
    with open("default_values/default_values.yaml", "r") as ymlfile:
        return yaml.safe_load(ymlfile)

def load_default_config():
    """Carica la configurazione di default da settings/default.yaml."""
    with open("settings/default.yaml", "r") as ymlfile:
        return yaml.safe_load(ymlfile)
    
def get_gemini_api_key():
    """Retrieve the Gemini API key from the environment variables."""
    try:
        with open("config/gemini.yaml", "r") as ymlfile:
            gemini = yaml.safe_load(ymlfile)
        return gemini["gemini_api_key"]
    except:
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
