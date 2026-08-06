"""
model_manager.py - Whisper model cache management for Whisper Utility.

Scans the Hugging Face hub cache for downloaded faster-whisper models,
reports their disk size, supports downloading via faster_whisper.WhisperModel,
and deletes cached model directories to free disk space.

Supported model identifiers match those used by faster-whisper / Systran:
    tiny, tiny.en, base, base.en, small, small.en, medium, medium.en,
    large-v1, large-v2, large-v3, large-v3-turbo, turbo,
    distil-large-v2, distil-large-v3, distil-large-v3.5,
    distil-medium.en, distil-small.en
"""

from __future__ import annotations

import logging
import os
import shutil
import threading
from typing import Callable, List, Optional

# ── Constants ─────────────────────────────────────────────────────────────────

# Hugging Face hub organisation for faster-whisper models
_HF_REPO_OWNER = "Systran"
_HF_MODEL_PREFIX = "faster-whisper"

# All model names supported by faster-whisper
SUPPORTED_MODELS: List[str] = [
    "tiny",
    "tiny.en",
    "base",
    "base.en",
    "small",
    "small.en",
    "medium",
    "medium.en",
    "large-v1",
    "large-v2",
    "large-v3",
    "large-v3-turbo",
    "turbo",
    "distil-large-v2",
    "distil-large-v3",
    "distil-large-v3.5",
    "distil-medium.en",
    "distil-small.en",
]


# ── Cache path helpers ────────────────────────────────────────────────────────

def get_hf_cache_dir() -> str:
    """Return the Hugging Face hub cache root directory."""
    # HF_HOME or HF_HUB_CACHE override; otherwise default ~/.cache/huggingface/hub
    hf_home = os.environ.get("HF_HOME") or os.environ.get("HF_HUB_CACHE")
    if hf_home:
        return hf_home
    return os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")


def _model_cache_path(model_name: str) -> str:
    """Return expected Hugging Face cache directory for the given model."""
    # HF stores models as: models--{owner}--{repo_name}
    safe_name = model_name.replace(".", "_")  # HF replaces dots with underscores in dir
    # Try both dot and underscore variants (HF behaviour varies)
    cache_root = get_hf_cache_dir()
    # Primary: Systran/faster-whisper-{model_name}  (dots → underscores in dir name)
    # HF hub stores as: models--Systran--faster-whisper-{model}
    # where the model part uses the original name but dots become underscores in the folder
    candidates = [
        os.path.join(cache_root, f"models--{_HF_REPO_OWNER}--{_HF_MODEL_PREFIX}-{model_name}"),
        os.path.join(cache_root, f"models--{_HF_REPO_OWNER}--{_HF_MODEL_PREFIX}-{safe_name}"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    # Return the primary path even if it doesn't exist yet
    return candidates[0]


def _dir_size_mb(path: str) -> float:
    """Return total size of a directory in megabytes."""
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    return total / (1024 * 1024)


# ── Public API ────────────────────────────────────────────────────────────────

def list_whisper_models_status() -> List[dict]:
    """Return status info for all supported Whisper models.

    Returns:
        List of dicts with keys:
            name (str): Model identifier (e.g. 'large-v3').
            is_downloaded (bool): Whether the model exists in HF cache.
            size_mb (float): Disk size in MB (0 if not downloaded).
            cache_path (str): Absolute path to the cache directory.
    """
    results = []
    for model_name in SUPPORTED_MODELS:
        path = _model_cache_path(model_name)
        is_downloaded = os.path.isdir(path)
        size_mb = _dir_size_mb(path) if is_downloaded else 0.0
        results.append({
            "name": model_name,
            "is_downloaded": is_downloaded,
            "size_mb": round(size_mb, 1),
            "cache_path": path,
        })
    return results


def download_model(
    model_name: str,
    device: str = "cpu",
    compute_type: str = "int8",
    progress_callback: Optional[Callable[[str], None]] = None,
) -> bool:
    """Download a Whisper model into the HF cache by instantiating WhisperModel.

    Args:
        model_name: Model identifier (e.g. 'large-v3').
        device: 'cpu' or 'cuda'.
        compute_type: Quantisation type ('int8', 'float16', 'auto').
        progress_callback: Called with status strings during download.

    Returns:
        True on success, False on error.
    """
    try:
        if progress_callback:
            progress_callback(f"Downloading {model_name}...")
        from faster_whisper import WhisperModel
        # Instantiating WhisperModel triggers the HF download automatically
        _ = WhisperModel(model_name, device=device, compute_type=compute_type)
        if progress_callback:
            progress_callback(f"Model '{model_name}' downloaded successfully.")
        return True
    except Exception as exc:
        logging.error("Error downloading model '%s': %s", model_name, exc)
        if progress_callback:
            progress_callback(f"Error downloading {model_name}: {exc}")
        return False


def download_model_async(
    model_name: str,
    device: str = "cpu",
    compute_type: str = "int8",
    progress_callback: Optional[Callable[[str], None]] = None,
    done_callback: Optional[Callable[[bool], None]] = None,
) -> threading.Thread:
    """Like download_model() but runs in a background thread.

    Args:
        model_name: Model identifier.
        device: 'cpu' or 'cuda'.
        compute_type: Quantisation type.
        progress_callback: Called with status strings (from background thread).
        done_callback: Called with True/False on completion.

    Returns:
        The started Thread object.
    """
    def _worker():
        ok = download_model(model_name, device, compute_type, progress_callback)
        if done_callback:
            done_callback(ok)

    t = threading.Thread(target=_worker, daemon=True, name=f"download-{model_name}")
    t.start()
    return t


def delete_model_cache(model_name: str) -> bool:
    """Delete the HF cache directory for the specified model.

    Args:
        model_name: Model identifier (e.g. 'large-v3').

    Returns:
        True if deleted (or already absent), False on error.
    """
    path = _model_cache_path(model_name)
    if not os.path.isdir(path):
        logging.info("Model '%s' cache not found at %s – nothing to delete.", model_name, path)
        return True
    try:
        shutil.rmtree(path, ignore_errors=False)
        logging.info("Deleted model cache: %s", path)
        return True
    except Exception as exc:
        logging.error("Error deleting model cache '%s' at %s: %s", model_name, path, exc)
        return False
