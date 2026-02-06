import logging
import requests
import json
from config import load_default_values, get_gemini_api_key
from google import genai
from google.genai import types

OLLAMA_ENDPOINT = "http://127.0.0.1:11434"

default_values = load_default_values()


def initialize_client():
    """Initialize the Gemini client."""
    GEMINI_API_KEY = get_gemini_api_key()
    if not GEMINI_API_KEY:
        return None
    return genai.Client(api_key=GEMINI_API_KEY)


def get_gemini_config():
    """Get the configuration for Gemini generation."""
    gemini_config = default_values['gemini']
    
    # Map old safety settings to new SDK format if necessary, 
    # but the new SDK often uses a list of SafetySetting objects.
    # We will construct the config dictionary compatible with types.GenerateContentConfig
    
    safety_settings = [
        types.SafetySetting(
            category=gemini_config['safety_settings']["harm_category_harassment"]['name'],
            threshold=gemini_config['safety_settings']["harm_category_harassment"]['threshold'],
        ),
        types.SafetySetting(
            category=gemini_config['safety_settings']["harm_category_hate_speech"]['name'],
            threshold=gemini_config['safety_settings']["harm_category_hate_speech"]['threshold'],
        ),
        types.SafetySetting(
            category=gemini_config['safety_settings']["harm_category_sexually_explicit"]['name'],
            threshold=gemini_config['safety_settings']["harm_category_sexually_explicit"]['threshold'],
        ),
        types.SafetySetting(
            category=gemini_config['safety_settings']["harm_category_dangerous_content"]['name'],
            threshold=gemini_config['safety_settings']["harm_category_dangerous_content"]['threshold']
        ),
    ]

    return types.GenerateContentConfig(
        temperature=gemini_config["temperature"],
        top_p=gemini_config["top_p"],
        top_k=gemini_config["top_k"],
        max_output_tokens=gemini_config["max_output_tokens"],
        response_mime_type=gemini_config["response_mime_type"],
        safety_settings=safety_settings
    )


def query_ollama(user_input, transcription, ollama_model):
    """Query a local Ollama server (stream-aware).

    Ollama may stream NDJSON lines with partial `response` fields. This
    function collects those fragments and returns the concatenated text.
    """
    try:
        prompt = f"Transcription: {transcription}\n\nUser Input: {user_input}"
        url = OLLAMA_ENDPOINT.rstrip("/") + "/api/generate"
        payload = {
            "model": ollama_model,
            "prompt": prompt,
        }
        resp = requests.post(url, json=payload, timeout=30, stream=True)
        resp.raise_for_status()
        parts = []
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                parts.append(line)
                continue
            # Streaming Ollama uses 'response' for incremental chunks
            if isinstance(obj, dict):
                if 'response' in obj:
                    parts.append(obj['response'])
                    continue
                if 'text' in obj:
                    parts.append(obj['text'])
                    continue
                if 'output' in obj:
                    parts.append(obj['output'])
                    continue
                if 'results' in obj and isinstance(obj['results'], list):
                    for r in obj['results']:
                        if isinstance(r, dict) and 'text' in r:
                            parts.append(r['text'])
        return ''.join(parts)
    except Exception as e:
        logging.error(f"Error querying Ollama at {OLLAMA_ENDPOINT}: {e}")
        return f"Error querying Ollama: {e}"


def list_ollama_models():
    """Return a list of available Ollama models from the local Ollama daemon.

    Returns a list of strings (model names). On error returns an empty list.
    """
    try:
        # Try the newer /models endpoint which returns {'models': [...]}
        for path in ("/models", "/api/tags"):
            url = OLLAMA_ENDPOINT.rstrip("/") + path
            try:
                resp = requests.get(url, timeout=5)
                resp.raise_for_status()
            except Exception:
                continue
            data = resp.json()
            models = []
            # Response may be {'models': [...]}
            if isinstance(data, dict) and 'models' in data and isinstance(data['models'], list):
                data_list = data['models']
            else:
                data_list = data if isinstance(data, list) else []

            for item in data_list:
                if isinstance(item, str):
                    models.append(item)
                elif isinstance(item, dict):
                    # Normalize common keys
                    if 'name' in item:
                        models.append(item['name'])
                    elif 'model' in item:
                        models.append(item['model'])
                    elif 'model_name' in item:
                        models.append(item['model_name'])
            # dedupe while preserving order
            seen = set()
            out = []
            for m in models:
                if m not in seen:
                    seen.add(m)
                    out.append(m)
            return out
    except Exception as e:
        logging.debug(f"Could not list Ollama models: {e}")
        return []


def query_gemini(user_input, transcription, gemini_model, provider="Gemini", ollama_model=None):
    """Dispatch query to Gemini or Ollama based on `provider`.

    Signature is compatible with the UI which passes 6 inputs.
    """
    try:
        if provider and str(provider).lower().startswith('olla'):
            model_name = ollama_model or (gemini_model if gemini_model else 'llama2')
            return query_ollama(user_input, transcription, model_name)

        # Use Gemini
        client = initialize_client()
        if not client:
             return "Error: Gemini API key not found."

        query = f"Transcription: {transcription}\n\nUser Input: {user_input}"
        
        config = get_gemini_config()
        
        response = client.models.generate_content(
            model=gemini_model,
            contents=[query],
            config=config
        )
        return response.text
    except Exception as e:
        logging.error(f"Error querying AI provider: {e}")
        return f"Error querying AI provider: {e}"
