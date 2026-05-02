import logging
import requests
import json
import os
from config import load_default_values, get_gemini_api_key
from google import genai
from google.genai import types

def _env_int(name, default):
    """Read integer env var with safe fallback."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logging.warning("Invalid %s=%r. Falling back to %s.", name, value, default)
        return default


OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://127.0.0.1:11434")
LMSTUDIO_ENDPOINT = os.getenv("LMSTUDIO_ENDPOINT", "http://127.0.0.1:1234")

# LM Studio can be slow with larger local models. Allow separate connect/read
# timeouts and keep backward compatibility with LMSTUDIO_TIMEOUT.
LMSTUDIO_TIMEOUT = _env_int("LMSTUDIO_TIMEOUT", 120)
LMSTUDIO_CONNECT_TIMEOUT = _env_int("LMSTUDIO_CONNECT_TIMEOUT", 5)
LMSTUDIO_READ_TIMEOUT = _env_int("LMSTUDIO_READ_TIMEOUT", LMSTUDIO_TIMEOUT)

default_values = load_default_values()

SYSTEM_PROMPT = (
    "Rispondi in modo chiaro e utile basandoti sulla trascrizione fornita. \n"
    "NON iniziare la risposta indicando che si tratta di una trascrizione. \n"
    "Limitati solo a rispondere alla richiesta dell'utente."
)



def initialize_client():
    """Initialize the Gemini client."""
    GEMINI_API_KEY = get_gemini_api_key()
    if not GEMINI_API_KEY:
        return None
    return genai.Client(api_key=GEMINI_API_KEY)


def get_gemini_config(system_instruction=None):
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
        safety_settings=safety_settings,
        system_instruction=system_instruction
    )



def query_ollama(user_input, transcription, ollama_model):
    """Query a local Ollama server with streaming.

    Yields the accumulated text progressively as Ollama streams NDJSON
    lines with partial ``response`` fields.
    """
    try:
        prompt = (
            f"System prompt:\n\n{SYSTEM_PROMPT}\n\n"
            f"# Transcription\n{transcription}\n\n"
            f"User prompt: \n{user_input}"
        )

        url = OLLAMA_ENDPOINT.rstrip("/") + "/api/generate"
        payload = {
            "model": ollama_model,
            "prompt": prompt,
        }
        resp = requests.post(url, json=payload, timeout=30, stream=True)
        resp.raise_for_status()
        accumulated = ""
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                accumulated += line
                yield accumulated
                continue
            # Streaming Ollama uses 'response' for incremental chunks
            chunk = ""
            if isinstance(obj, dict):
                if 'response' in obj:
                    chunk = obj['response']
                elif 'text' in obj:
                    chunk = obj['text']
                elif 'output' in obj:
                    chunk = obj['output']
                elif 'results' in obj and isinstance(obj['results'], list):
                    for r in obj['results']:
                        if isinstance(r, dict) and 'text' in r:
                            chunk += r['text']
            if chunk:
                accumulated += chunk
                yield accumulated
    except Exception as e:
        logging.error(f"Error querying Ollama at {OLLAMA_ENDPOINT}: {e}")
        yield f"Error querying Ollama: {e}"


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


def query_lmstudio(user_input, transcription, lmstudio_model):
    """Query a local LM Studio server using the OpenAI-compatible streaming API.

    Yields the accumulated text progressively by parsing SSE delta chunks.
    """
    try:
        if not lmstudio_model:
            yield "Error querying LM Studio: no model selected."
            return

        url = LMSTUDIO_ENDPOINT.rstrip("/") + "/v1/chat/completions"
        payload = {
            "model": lmstudio_model,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": f"# Transcription\n{transcription}\n\nUser prompt: \n{user_input}",
                },
            ],
            "temperature": 0.2,
            "stream": True,
        }
        resp = requests.post(
            url,
            json=payload,
            timeout=(LMSTUDIO_CONNECT_TIMEOUT, LMSTUDIO_READ_TIMEOUT),
            stream=True,
        )
        resp.raise_for_status()
        accumulated = ""
        for line in resp.iter_lines(decode_unicode=True):
            if not line or line.strip() == "data: [DONE]":
                continue
            # SSE lines start with "data: "
            if line.startswith("data: "):
                line = line[6:]
            try:
                obj = json.loads(line)
                choices = obj.get("choices", []) if isinstance(obj, dict) else []
                if choices and isinstance(choices[0], dict):
                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "") if isinstance(delta, dict) else ""
                    if content:
                        accumulated += content
                        yield accumulated
            except Exception:
                continue
    except requests.exceptions.ReadTimeout as e:
        logging.error(f"LM Studio timed out at {LMSTUDIO_ENDPOINT}: {e}")
        yield (
            "Error querying LM Studio: request timed out while waiting for model output. "
            "Increase LMSTUDIO_READ_TIMEOUT (or LMSTUDIO_TIMEOUT) and ensure the model is loaded in LM Studio."
        )
    except Exception as e:
        logging.error(f"Error querying LM Studio at {LMSTUDIO_ENDPOINT}: {e}")
        yield f"Error querying LM Studio: {e}"


def list_lmstudio_models():
    """Return a list of available LM Studio models from the local server."""
    try:
        url = LMSTUDIO_ENDPOINT.rstrip("/") + "/v1/models"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        out = []
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            for item in data["data"]:
                if isinstance(item, dict):
                    model_id = item.get("id")
                    if isinstance(model_id, str) and model_id.strip():
                        out.append(model_id)
        # dedupe while preserving order
        seen = set()
        deduped = []
        for model in out:
            if model not in seen:
                seen.add(model)
                deduped.append(model)
        return deduped
    except Exception as e:
        logging.debug(f"Could not list LM Studio models: {e}")
        return []


def query_gemini(user_input, transcription, gemini_model, provider="Gemini", ollama_model=None, lmstudio_model=None):
    """Dispatch query to the selected provider and stream the response.

    This is a generator: it yields the progressively accumulated text so
    that Gradio can update the UI in real time. Signature is compatible
    with the UI which passes 6 inputs.
    """
    try:
        if provider and str(provider).lower().startswith('olla'):
            model_name = ollama_model or (gemini_model if gemini_model else 'llama2')
            yield from query_ollama(user_input, transcription, model_name)
            return

        if provider and str(provider).lower().startswith('lm'):
            model_name = lmstudio_model or (gemini_model if gemini_model else "local-model")
            yield from query_lmstudio(user_input, transcription, model_name)
            return

        # Use Gemini
        client = initialize_client()
        if not client:
            yield "Error: Gemini API key not found."
            return

        user_prompt = f"# Transcription\n{transcription}\n\nUser prompt: \n{user_input}"
        config = get_gemini_config(system_instruction=SYSTEM_PROMPT)

        accumulated = ""
        for chunk in client.models.generate_content_stream(
            model=gemini_model,
            contents=[user_prompt],
            config=config,
        ):
            if chunk.text:
                accumulated += chunk.text
                yield accumulated
    except Exception as e:
        logging.error(f"Error querying AI provider: {e}")
        yield f"Error querying AI provider: {e}"
