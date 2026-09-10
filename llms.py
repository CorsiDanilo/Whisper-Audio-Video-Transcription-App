import logging
import requests
import json
import os
import time
from config import load_default_values, load_default_config, get_gemini_api_key, get_translation as _
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


def _get_timeout_setting(cfg_key, env_keys, default_sec=300):
    try:
        cfg = load_default_config()
        if cfg and cfg_key in cfg:
            return int(cfg[cfg_key])
    except Exception:
        pass
    for env in env_keys:
        val = os.getenv(env)
        if val:
            try:
                return int(val)
            except ValueError:
                pass
    return default_sec


OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://127.0.0.1:11434")
LMSTUDIO_ENDPOINT = os.getenv("LMSTUDIO_ENDPOINT", "http://127.0.0.1:1234")

# LM Studio & Ollama timeouts. Allow separate connect/read timeouts or default config.
LMSTUDIO_TIMEOUT = _get_timeout_setting("lmstudio_timeout", ["LMSTUDIO_TIMEOUT", "LMSTUDIO_READ_TIMEOUT"], 300)
LMSTUDIO_CONNECT_TIMEOUT = _env_int("LMSTUDIO_CONNECT_TIMEOUT", 5)
LMSTUDIO_READ_TIMEOUT = _get_timeout_setting("lmstudio_timeout", ["LMSTUDIO_READ_TIMEOUT", "LMSTUDIO_TIMEOUT"], LMSTUDIO_TIMEOUT)
OLLAMA_READ_TIMEOUT = _get_timeout_setting("ollama_timeout", ["OLLAMA_READ_TIMEOUT", "OLLAMA_TIMEOUT"], 300)

default_values = load_default_values()

def _is_model_loaded_ollama(model_name: str) -> bool:
    try:
        url = OLLAMA_ENDPOINT.rstrip("/") + "/api/ps"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            loaded = [m.get("name", "") for m in data.get("models", [])]
            return any(model_name in name for name in loaded)
    except Exception:
        pass
    return False

def _is_model_loaded_lmstudio(model_name: str) -> bool:
    try:
        url = LMSTUDIO_ENDPOINT.rstrip("/") + "/v1/models"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            ids = [m.get("id", "") for m in data.get("data", [])]
            return any(model_name in mid for mid in ids)
    except Exception:
        pass
    return False

def _trigger_lmstudio_load(model_name: str) -> None:
    try:
        url = LMSTUDIO_ENDPOINT.rstrip("/") + "/api/v1/models/load"
        payload = {"model": model_name}
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            logging.info(f"Triggered load for model {model_name} on LM Studio (/api/v1/models/load)")
            return
    except Exception:
        pass
    try:
        url = LMSTUDIO_ENDPOINT.rstrip("/") + "/v1/models/load"
        payload = {"model": model_name}
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            logging.info(f"Triggered load for model {model_name} on LM Studio (/v1/models/load)")
            return
    except Exception:
        pass

SYSTEM_PROMPT = (
    "Rispondi in modo chiaro e utile basandoti sulla trascrizione fornita. \n"
    "NON iniziare la risposta indicando che si tratta di una trascrizione. \n"
    "Limitati solo a rispondere alla richiesta dell'utente."
)

SYSTEM_PROMPT_EN = (
    "Respond clearly and helpfully based on the provided transcription. \n"
    "DO NOT start your response by stating that it is a transcription. \n"
    "Limit yourself to answering only the user's request."
)

SYSTEM_PROMPT_FIX_TEXT = (
    "Sei un assistente specializzato nella correzione e formattazione del testo. "
    "Usa TUTTI i token a tua disposizione per massimizzare l'output e restituire il testo nella sua completezza. "
    "Correggi tutti gli errori di battitura, grammatica, punteggiatura e formattazione. "
    "NON omettere, tagliare o riassumere nessuna parte del testo originale: ogni parola deve essere presente nell'output. "
    "Restituisci esclusivamente il testo corretto, senza commenti, prefazioni o spiegazioni."
)

SYSTEM_PROMPT_FIX_TEXT_EN = (
    "You are a specialist assistant for text correction and formatting. "
    "Use ALL available tokens to maximize your output and return the text in its entirety. "
    "Correct all typos, grammar, punctuation, and formatting errors. "
    "Do NOT omit, truncate, or summarize any part of the original text: every word must be present in the output. "
    "Return exclusively the corrected text, with no comments, preambles, or explanations."
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



def query_ollama(user_input, transcription, ollama_model, fix_text=False, response_language="Italiano"):
    """Query a local Ollama server with streaming.

    Yields the accumulated text progressively as Ollama streams NDJSON
    lines with partial ``response`` fields.

    response_language: "Italiano" (default) or "English".
    """
    try:
        yield _("llm_checking_model")
        
        ready = False
        elapsed = 0
        while elapsed < 60:
            if _is_model_loaded_ollama(ollama_model):
                ready = True
                break
            yield _("llm_model_loading").format(elapsed=elapsed)
            time.sleep(2)
            elapsed += 2
            
        if not ready:
            yield _("llm_model_sending")
        else:
            yield _("llm_model_ready")

        is_english = str(response_language).strip().lower() == "english"
        if fix_text:
            sys_prompt = SYSTEM_PROMPT_FIX_TEXT_EN if is_english else SYSTEM_PROMPT_FIX_TEXT
        else:
            sys_prompt = SYSTEM_PROMPT_EN if is_english else SYSTEM_PROMPT

        if is_english:
            prompt = (
                f"# Transcription\n{transcription}\n\n"
                f"User prompt: \n{user_input}"
            )
        else:
            prompt = (
                f"# Trascrizione\n{transcription}\n\n"
                f"User prompt: \n{user_input}"
            )
        url = OLLAMA_ENDPOINT.rstrip("/") + "/api/generate"
        payload = {
            "model": ollama_model,
            "prompt": prompt,
            "system": sys_prompt,
        }
        resp = requests.post(url, json=payload, timeout=(5, OLLAMA_READ_TIMEOUT), stream=True)
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


def query_lmstudio(user_input, transcription, lmstudio_model, fix_text=False, response_language="Italiano"):
    """Query a local LM Studio server using the OpenAI-compatible streaming API.

    Yields the accumulated text progressively by parsing SSE delta chunks.

    response_language: "Italiano" (default) or "English".
    """
    try:
        if not lmstudio_model:
            yield "Error querying LM Studio: no model selected."
            return

        yield _("llm_checking_model")
        
        _trigger_lmstudio_load(lmstudio_model)
        
        ready = False
        elapsed = 0
        while elapsed < 60:
            if _is_model_loaded_lmstudio(lmstudio_model):
                ready = True
                break
            yield _("llm_model_loading").format(elapsed=elapsed)
            time.sleep(2)
            elapsed += 2
            
        if not ready:
            yield _("llm_model_timeout_lmstudio")
            return

        yield _("llm_model_ready")

        is_english = str(response_language).strip().lower() == "english"
        if fix_text:
            sys_prompt = SYSTEM_PROMPT_FIX_TEXT_EN if is_english else SYSTEM_PROMPT_FIX_TEXT
        else:
            sys_prompt = SYSTEM_PROMPT_EN if is_english else SYSTEM_PROMPT

        if is_english:
            user_content = f"# Transcription\n{transcription}\n\nUser prompt: \n{user_input}"
        else:
            user_content = f"# Trascrizione\n{transcription}\n\nUser prompt: \n{user_input}"
        url = LMSTUDIO_ENDPOINT.rstrip("/") + "/v1/chat/completions"
        payload = {
            "model": lmstudio_model,
            "messages": [
                {
                    "role": "system",
                    "content": sys_prompt,
                },
                {
                    "role": "user",
                    "content": user_content,
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


def query_gemini(user_input, transcription, gemini_model, provider="Gemini", ollama_model=None, lmstudio_model=None, fix_text=False, response_language="Italiano"):
    """Dispatch query to the selected provider and stream the response.

    This is a generator: it yields the progressively accumulated text so
    that Gradio can update the UI in real time. Signature is compatible
    with the UI which passes inputs.

    response_language: "Italiano" (default) or "English" — controls the
    language the LLM is instructed to reply in.
    """
    try:
        if provider and str(provider).lower().startswith('olla'):
            model_name = ollama_model or (gemini_model if gemini_model else 'llama2')
            yield from query_ollama(user_input, transcription, model_name, fix_text=fix_text, response_language=response_language)
            return

        if provider and str(provider).lower().startswith('lm'):
            model_name = lmstudio_model or (gemini_model if gemini_model else "local-model")
            yield from query_lmstudio(user_input, transcription, model_name, fix_text=fix_text, response_language=response_language)
            return

        # Use Gemini
        api_key = get_gemini_api_key()
        client = initialize_client()
        if not client or not api_key:
            yield "Error: Gemini API key not found."
            return

        yield _("llm_waiting_gemini")

        is_english = str(response_language).strip().lower() == "english"
        if fix_text:
            sys_prompt = SYSTEM_PROMPT_FIX_TEXT_EN if is_english else SYSTEM_PROMPT_FIX_TEXT
        else:
            sys_prompt = SYSTEM_PROMPT_EN if is_english else SYSTEM_PROMPT

        if is_english:
            user_prompt = f"# Transcription\n{transcription}\n\nUser prompt: \n{user_input}"
        else:
            user_prompt = f"# Trascrizione\n{transcription}\n\nUser prompt: \n{user_input}"

        config = get_gemini_config(system_instruction=sys_prompt)

        # Build candidate models sequence for fallback:
        # 1. User-selected model (if specified)
        # 2. All other valid models ordered from newest/best downwards
        available_models = get_sorted_gemini_models(api_key)
        candidate_models = []
        if gemini_model and str(gemini_model).strip():
            candidate_models.append(str(gemini_model).strip())
        for m in available_models:
            if m not in candidate_models:
                candidate_models.append(m)

        if not candidate_models:
            candidate_models = ["gemini-flash-latest", "gemini-3.8-flash", "gemini-2.5-flash"]

        last_error = None
        for i, current_model in enumerate(candidate_models):
            accumulated = ""
            received_any_chunk = False
            try:
                logging.info(f"Attempting query to Gemini with model: '{current_model}' ({i+1}/{len(candidate_models)})")
                stream = client.models.generate_content_stream(
                    model=current_model,
                    contents=[user_prompt],
                    config=config,
                )
                for chunk in stream:
                    if chunk.text:
                        received_any_chunk = True
                        accumulated += chunk.text
                        yield accumulated

                # If text was successfully generated, request is complete
                if received_any_chunk and accumulated.strip():
                    return

            except Exception as e:
                last_error = e
                logging.warning(f"Gemini query error with model '{current_model}': {e}")

                # If there are other models in the fallback chain, try the next one
                if i + 1 < len(candidate_models):
                    next_model = candidate_models[i + 1]
                    err_str = str(e)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        err_summary = "Quota esaurita / Rate limit (429)"
                    elif "500" in err_str or "INTERNAL" in err_str:
                        err_summary = "Errore server Google (500)"
                    elif "404" in err_str or "NOT_FOUND" in err_str:
                        err_summary = "Modello non supportato (404)"
                    else:
                        err_summary = err_str.split("\n")[0][:45]

                    if is_english:
                        notice = f"[!] Model '{current_model}' unavailable ({err_summary}). Retrying with '{next_model}'...\n\n"
                    else:
                        notice = f"[!] Modello '{current_model}' non disponibile ({err_summary}). Tentativo con '{next_model}' in corso...\n\n"

                    yield notice
                    time.sleep(0.3)
                    continue
                else:
                    break

        err_detail = str(last_error) if last_error else "All candidate models failed."
        logging.error(f"All candidate Gemini models failed: {err_detail}")
        if is_english:
            yield f"Error querying AI provider: All candidate Gemini models failed. Last error: {err_detail}"
        else:
            yield f"Errore durante la richiesta a Gemini: tutti i modelli disponibili hanno fallito. Ultimo errore: {err_detail}"
    except Exception as e:
        logging.error(f"Error querying AI provider: {e}")
        yield f"Error querying AI provider: {e}"


_GEMINI_MODELS_CACHE = {"key": None, "models": [], "timestamp": 0}


def get_sorted_gemini_models(api_key: str, force_refresh: bool = False) -> list[str]:
    """
    Retrieve all available Gemini and Gemma models via API
    and sort them placing the most recent/best first.
    Includes a 15-minute cache to avoid repeated client.models.list() calls.
    """
    if not api_key:
        return []

    global _GEMINI_MODELS_CACHE
    now = time.time()
    if not force_refresh and _GEMINI_MODELS_CACHE["key"] == api_key and _GEMINI_MODELS_CACHE["models"]:
        if (now - _GEMINI_MODELS_CACHE["timestamp"]) < 900:
            return list(_GEMINI_MODELS_CACHE["models"])

    try:
        import re
        client = genai.Client(api_key=api_key)
        retrieved_models = []

        # 1. Retrieve models from API
        for model in client.models.list():
            name_lower = model.name.lower()
            # Include only generative text/vision models matching Gemini or Gemma
            if model.supported_actions and "generateContent" in model.supported_actions:
                if "gemini" in name_lower or "gemma" in name_lower:
                    # Explicitly exclude embeddings, audio, image, tts, video, tool, robotics, and computer models
                    exclude_keywords = ["embed", "audio", "image", "tts", "video", "tool", "robotics", "computer"]
                    if any(kw in name_lower for kw in exclude_keywords):
                        continue
                    clean_name = model.name.replace("models/", "")
                    retrieved_models.append(clean_name)

        always_present = ["gemini-flash-latest", "gemini-flash-lite-latest"]
        for dm in always_present:
            if dm not in retrieved_models:
                retrieved_models.append(dm)

        if not retrieved_models:
            retrieved_models = always_present.copy()

        # 2. Semantic sorting algorithm (Latest-First)
        def get_sort_key(name):
            name_lower = name.lower()

            # Priority for 'latest' models (0 = first, 1 = after)
            is_latest = 0 if "latest" in name_lower else 1

            # Brand priority (Gemini before Gemma)
            brand_priority = 1 if "gemini" in name_lower else 2

            # Extract main numeric version
            version = 1.0
            brand_match = re.search(r'(?:gemini|gemma)-?(\d+(?:\.\d+)?)', name_lower)
            if brand_match:
                val_str = brand_match.group(1)
                match_str = brand_match.group(0)
                idx = name_lower.find(match_str) + len(match_str)
                if idx < len(name_lower) and name_lower[idx] == 'b':
                    version = 1.0
                else:
                    version = float(val_str)

            # Flavor priority (prefer 'flash' as default, then 'pro', then others)
            flavor_priority = 3
            if "flash" in name_lower:
                flavor_priority = 1
            elif "pro" in name_lower:
                flavor_priority = 2

            # Return a sort key tuple:
            # - is_latest (latest on top)
            # - descending version (-version)
            # - ascending brand_priority (Gemini before Gemma)
            # - ascending flavor_priority (Flash before Pro)
            # - descending alphabetical name for tie-breaking
            return (is_latest, -version, brand_priority, flavor_priority, name_lower)

        sorted_models = sorted(retrieved_models, key=get_sort_key)
        _GEMINI_MODELS_CACHE = {"key": api_key, "models": sorted_models, "timestamp": now}
        return list(sorted_models)

    except Exception as e:
        logging.error(f"Failed to connect to Gemini API or retrieve models: {e}")
        return ["gemini-flash-latest", "gemini-flash-lite-latest"]
