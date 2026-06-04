import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ALLOWED_MEDIA_EXTENSIONS = {
    ".avi",
    ".flac",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".ogg",
    ".opus",
    ".wav",
    ".webm",
}
ALLOWED_CONFIG_EXTENSIONS = {".yaml", ".yml"}

DEFAULT_MAX_UPLOAD_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_CONFIG_BYTES = 1024 * 1024
DEFAULT_MAX_MEDIA_DURATION_SECONDS = 2 * 60 * 60
DEFAULT_FFMPEG_TIMEOUT_SECONDS = 5 * 60


class SecurityError(ValueError):
    """Raised when user-controlled input violates the local app security policy."""


def _env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise SecurityError(f"{name} must be an integer") from exc
    if parsed <= 0:
        raise SecurityError(f"{name} must be greater than zero")
    return parsed


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_max_upload_bytes():
    return _env_int("WHISPER_MAX_UPLOAD_BYTES", DEFAULT_MAX_UPLOAD_BYTES)


def get_max_config_bytes():
    return _env_int("WHISPER_MAX_CONFIG_BYTES", DEFAULT_MAX_CONFIG_BYTES)


def get_max_media_duration_seconds():
    return _env_int(
        "WHISPER_MAX_MEDIA_DURATION_SECONDS",
        DEFAULT_MAX_MEDIA_DURATION_SECONDS,
    )


def get_ffmpeg_timeout_seconds():
    return _env_int("WHISPER_FFMPEG_TIMEOUT_SECONDS", DEFAULT_FFMPEG_TIMEOUT_SECONDS)


def get_app_temp_root():
    configured = os.getenv("WHISPER_UTILITY_TEMP_DIR")
    root = Path(configured) if configured else Path(tempfile.gettempdir()) / "whisper-utility"
    return root.resolve()


def get_gradio_temp_dir():
    configured = os.getenv("GRADIO_TEMP_DIR")
    root = Path(configured) if configured else get_app_temp_root()
    return root.resolve()


def configure_gradio_temp_dir():
    temp_dir = get_gradio_temp_dir()
    temp_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("GRADIO_TEMP_DIR", str(temp_dir))
    return temp_dir


def _coerce_path(value):
    if value is None:
        raise SecurityError("No file was provided.")
    if isinstance(value, dict):
        value = value.get("path") or value.get("name")
    elif isinstance(value, (str, os.PathLike)):
        pass
    elif hasattr(value, "name"):
        value = value.name
    if not value:
        raise SecurityError("No file was provided.")
    return Path(value).expanduser().resolve()


def _is_within(path, root):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def ensure_within(path, root, message):
    resolved_path = Path(path).resolve()
    resolved_root = Path(root).resolve()
    if not _is_within(resolved_path, resolved_root):
        raise SecurityError(message)
    return resolved_path


def _safe_filename(filename):
    name = Path(filename).name
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(name).stem).strip("._")
    suffix = Path(name).suffix.lower()
    if not stem:
        stem = "upload"
    return f"{stem}{suffix}"


def validate_extension(path, allowed_extensions):
    suffix = Path(path).suffix.lower()
    if suffix not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise SecurityError(f"Unsupported file extension. Allowed extensions: {allowed}.")
    return suffix


def validate_file_size(path, max_bytes):
    size = Path(path).stat().st_size
    if size <= 0:
        raise SecurityError("Uploaded file is empty.")
    if size > max_bytes:
        raise SecurityError("Uploaded file is too large.")
    return size


def get_media_duration_seconds(media_path):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(media_path),
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=get_ffmpeg_timeout_seconds(),
        )
    except FileNotFoundError as exc:
        raise SecurityError("ffprobe is required to inspect uploaded media.") from exc
    except subprocess.TimeoutExpired as exc:
        raise SecurityError("Media duration inspection timed out.") from exc
    except subprocess.CalledProcessError as exc:
        raise SecurityError("Unable to inspect uploaded media duration.") from exc

    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise SecurityError("Unable to inspect uploaded media duration.") from exc
    if duration < 0:
        raise SecurityError("Invalid uploaded media duration.")
    return duration


def validate_media_duration(path):
    duration = get_media_duration_seconds(path)
    if duration > get_max_media_duration_seconds():
        raise SecurityError("Uploaded media duration exceeds the configured limit.")
    return duration


def validate_media_constraints(path, inspect_duration=True):
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise SecurityError("Uploaded file does not exist.")
    validate_extension(resolved, ALLOWED_MEDIA_EXTENSIONS)
    validate_file_size(resolved, get_max_upload_bytes())
    if inspect_duration:
        validate_media_duration(resolved)
    return resolved


def validate_controlled_media_path(path, inspect_duration=True):
    resolved = _coerce_path(path)
    ensure_within(
        resolved,
        get_gradio_temp_dir(),
        "Media input is outside Gradio temporary storage.",
    )
    return validate_media_constraints(resolved, inspect_duration=inspect_duration)


def validate_local_media_path(path, inspect_duration=True):
    resolved = _coerce_path(path)
    return validate_media_constraints(resolved, inspect_duration=inspect_duration)


def validate_controlled_config_path(path):
    resolved = _coerce_path(path)
    ensure_within(
        resolved,
        get_gradio_temp_dir(),
        "Configuration input is outside Gradio temporary storage.",
    )
    validate_extension(resolved, ALLOWED_CONFIG_EXTENSIONS)
    validate_file_size(resolved, get_max_config_bytes())
    return resolved


def validate_local_config_path(path):
    resolved = _coerce_path(path)
    validate_extension(resolved, ALLOWED_CONFIG_EXTENSIONS)
    validate_file_size(resolved, get_max_config_bytes())
    return resolved


def validate_controlled_transcript_path(path):
    resolved = _coerce_path(path)
    if resolved.suffix.lower() != ".txt":
        raise SecurityError("Transcript path must be a text file.")
    if not resolved.is_file():
        raise SecurityError("Transcript file does not exist.")
    return resolved


def build_contained_output_path(input_path, suffix):
    source = validate_controlled_media_path(input_path, inspect_duration=False)
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", source.stem).strip("._") or "upload"
    output = ensure_within(
        source.with_name(f"{safe_stem}{suffix}"),
        source.parent,
        "Output path is outside the uploaded file directory.",
    )
    ensure_within(
        output,
        get_gradio_temp_dir(),
        "Output path is outside Gradio temporary storage.",
    )
    return output


def build_local_output_path(input_path, suffix):
    source = validate_local_media_path(input_path, inspect_duration=False)
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", source.stem).strip("._") or "upload"
    return source.with_name(f"{safe_stem}{suffix}")


def remove_controlled_tree(path):
    resolved = _coerce_path(path)
    ensure_within(
        resolved,
        get_gradio_temp_dir(),
        "Refusing to remove a path outside Gradio temporary storage.",
    )
    if resolved.exists():
        shutil.rmtree(resolved, ignore_errors=True)


def cleanup_temp_storage():
    temp_dir = get_gradio_temp_dir()
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


def _is_loopback_host(server_name):
    normalized = (server_name or "").strip().lower()
    return normalized in {"127.0.0.1", "localhost", "::1"}


def get_gradio_launch_kwargs(**overrides):
    server_name = os.getenv("WHISPER_GRADIO_SERVER_NAME", "127.0.0.1")
    share = _env_bool("WHISPER_GRADIO_SHARE", False)
    kwargs = {
        "server_name": server_name,
        "share": share,
    }
    kwargs.update(overrides)

    requires_auth = bool(kwargs.get("share")) or not _is_loopback_host(
        kwargs.get("server_name")
    )
    if requires_auth:
        username = os.getenv("WHISPER_GRADIO_AUTH_USER")
        password = os.getenv("WHISPER_GRADIO_AUTH_PASSWORD")
        if not username or not password:
            raise RuntimeError(
                "Remote/shared Gradio launch requires "
                "WHISPER_GRADIO_AUTH_USER and WHISPER_GRADIO_AUTH_PASSWORD."
            )
        kwargs["auth"] = (username, password)
    return kwargs
