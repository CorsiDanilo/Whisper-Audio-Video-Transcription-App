import os
import shutil
import subprocess
import sys
import logging
from pathlib import Path
from config import load_default_values
from security_utils import get_ffmpeg_timeout_seconds

DEFAULT_VALUES = load_default_values()


def bundled_runtime_roots(runtime_dir: Path, system: str) -> tuple[Path, ...]:
    """Return directories that may contain installer-managed runtime files."""
    roots = [runtime_dir]
    if system == "darwin" and runtime_dir.name == "MacOS" and runtime_dir.parent.name == "Contents":
        roots.append(runtime_dir.parent.parent)
        roots.append(runtime_dir.parent.parent.parent)
    return tuple(roots)


def _get_ffmpeg_executable() -> str:
    """Locate system FFmpeg or the bundled copy installed beside the app."""
    configured = os.environ.get("WHISPER_FFMPEG_PATH")
    if configured:
        return configured

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    runtime_dir = (
        Path(sys.executable).resolve().parent
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parent
    )
    for root in bundled_runtime_roots(runtime_dir, sys.platform):
        candidates = [
            root / "ffmpeg" / "ffmpeg",
            root / "ffmpeg" / "ffmpeg.exe",
            root / "ffmpeg" / "bin" / "ffmpeg",
            root / "ffmpeg" / "bin" / "ffmpeg.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)

        # Static FFmpeg archives contain a versioned directory. Search only below
        # the installer-managed ffmpeg directory to avoid scanning the whole disk.
        bundled_root = root / "ffmpeg"
        if bundled_root.is_dir():
            for candidate in bundled_root.rglob("ffmpeg"):
                if candidate.is_file():
                    return str(candidate)
            for candidate in bundled_root.rglob("ffmpeg.exe"):
                if candidate.is_file():
                    return str(candidate)

    return "ffmpeg"


def _run_ffmpeg(command, action):
    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "check": True,
        "timeout": get_ffmpeg_timeout_seconds(),
    }
    import sys
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    try:
        subprocess.run(command, **kwargs)
    except FileNotFoundError:
        logging.error("ffmpeg is not installed or not available on PATH.")
        raise
    except subprocess.TimeoutExpired:
        logging.error("%s timed out.", action)
        raise
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        if len(stderr) > 500:
            stderr = stderr[-500:]
        logging.error("%s failed: %s", action, stderr)
        raise


def is_whatsapp_audio_file(file_path):
    """Checks if the audio file is in WhatsApp format (e.g., .opus)."""
    whatsapp_audio_extensions = ['.opus']
    file_extension = os.path.splitext(file_path)[1].lower()
    return file_extension in whatsapp_audio_extensions

def convert_whatsapp_audio_to_mp3(file_path, output_audio_file, device=None):
    """Converts a WhatsApp audio file to MP3 format."""
    logging.info(f"Converting WhatsApp audio file to MP3: {file_path}...")
    command = [_get_ffmpeg_executable(), "-hide_banner", "-nostdin"]
    if device and str(device).lower() == "cuda":
        command.extend(["-hwaccel", "auto"])
    command.extend([
        "-y",
        "-i",
        file_path,
        "-vn",
        "-sn",
        "-dn",
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "2",
        "-threads",
        "0",
        output_audio_file,
    ])
    _run_ffmpeg(command, "WhatsApp audio conversion")
    logging.info(f"Converted file saved as: {output_audio_file}")

def is_video_file(file_path):
    """Checks if the file is a video based on its extension."""
    try:
        video_extensions = DEFAULT_VALUES['default_values']['video_extensions']
        file_extension = os.path.splitext(file_path)[1].lower()
        return file_extension in video_extensions
    except Exception as e:
        logging.error(f"Error checking if file is a video: {e}")
        return False

def extract_audio_from_video(video_file, output_audio_file, device=None):
    """Extracts audio from a video file using ffmpeg.

    Uses '-vn' to skip video stream processing, '-sn'/'-dn' to skip subtitles/data,
    '-threads 0' for multithreading, and '-hwaccel auto' when CUDA is enabled for
    fast container demuxing. Uses '-map a?' so that ffmpeg does not abort when
    the video has no audio track.
    """
    try:
        logging.info(f"Extracting audio from video file: {video_file}...")
        command = [_get_ffmpeg_executable(), "-hide_banner", "-nostdin"]
        if device and str(device).lower() == "cuda":
            command.extend(["-hwaccel", "auto"])
        command.extend([
            "-y",
            "-i",
            video_file,
            "-vn",          # Skip video decoding/processing completely
            "-sn",          # Skip subtitles
            "-dn",          # Skip data streams
            "-map",
            "a?",           # Skip mapping silently if no audio stream exists
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            "-threads",
            "0",
            output_audio_file,
        ])
        _run_ffmpeg(command, "Video audio extraction")

        # If ffmpeg exited cleanly but produced no file (or an empty one),
        # the video simply had no audio track.
        if not os.path.exists(output_audio_file) or os.path.getsize(output_audio_file) == 0:
            raise RuntimeError(
                f"Video has no audio track, skipping: {video_file}"
            )

        logging.info(f"Audio extracted to: {output_audio_file}")
    except Exception as e:
        logging.error(f"Error extracting audio from video: {e}")
        raise

def is_audio_file(file_path):
    """Checks if the file is an audio based on its extension."""
    try:
        audio_extensions = DEFAULT_VALUES['default_values']['audio_extensions']
        file_extension = os.path.splitext(file_path)[1].lower()
        return file_extension in audio_extensions
    except Exception as e:
        logging.error(f"Error checking if file is an audio file: {e}")
        return False

def convert_audio_to_mp3(audio_file, output_audio_file, device=None):
    """Converts an audio file to MP3 format."""
    try:
        logging.info(f"Converting audio file to MP3: {audio_file}...")
        command = [_get_ffmpeg_executable(), "-hide_banner", "-nostdin"]
        if device and str(device).lower() == "cuda":
            command.extend(["-hwaccel", "auto"])
        command.extend([
            "-y",
            "-i",
            audio_file,
            "-vn",
            "-sn",
            "-dn",
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            "-threads",
            "0",
            output_audio_file,
        ])
        _run_ffmpeg(command, "Audio conversion")
        logging.info(f"Audio file converted to MP3: {output_audio_file}")
    except Exception as e:
        logging.error(f"Error converting audio to MP3: {e}")
        raise
