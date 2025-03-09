import os
import logging
import yaml
import subprocess
from dotenv import load_dotenv

def load_default_values():
    """Carica i valori di default da default_values.yaml."""
    with open("default_values.yaml", "r") as ymlfile:
        return yaml.safe_load(ymlfile)

def load_default_config():
    """Carica la configurazione di default da configurations/default.yaml."""
    with open("configurations/default.yaml", "r") as ymlfile:
        return yaml.safe_load(ymlfile)

def setup_logging(log_file="whisper.log"):
    """Configura il logging: elimina il file di log precedente e imposta i gestori."""
    if os.path.exists(log_file):
        os.remove(log_file)
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
