import os
import subprocess
import logging
from pydub import AudioSegment
from config import load_default_values

DEFAULT_VALUES = load_default_values()

def is_whatsapp_audio_file(file_path):
    """Checks if the audio file is in WhatsApp format (e.g., .opus)."""
    whatsapp_audio_extensions = ['.opus']
    file_extension = os.path.splitext(file_path)[1].lower()
    return file_extension in whatsapp_audio_extensions

def convert_whatsapp_audio_to_mp3(file_path, output_audio_file):
    """Converts a WhatsApp audio file to MP3 format."""
    logging.info(f"Converting WhatsApp audio file to MP3: {file_path}...")
    audio = AudioSegment.from_file(file_path, codec="libopus")
    audio.export(output_audio_file, format="mp3")
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

def extract_audio_from_video(video_file, output_audio_file):
    """Extracts audio from a video file using ffmpeg."""
    try:
        logging.info(f"Extracting audio from video file: {video_file}...")
        command = ['ffmpeg', '-i', video_file, '-q:a', '0', '-map', 'a', output_audio_file, '-y']
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"Audio extracted to: {output_audio_file}")
    except Exception as e:
        logging.error(f"Error extracting audio from video: {e}")

def is_audio_file(file_path):
    """Checks if the file is an audio based on its extension."""
    try:
        audio_extensions = DEFAULT_VALUES['default_values']['audio_extensions']
        file_extension = os.path.splitext(file_path)[1].lower()
        return file_extension in audio_extensions
    except Exception as e:
        logging.error(f"Error checking if file is an audio file: {e}")
        return False

def convert_audio_to_mp3(audio_file, output_audio_file):
    """Converts an audio file to MP3 format."""
    try:
        logging.info(f"Converting audio file to MP3: {audio_file}...")
        audio = AudioSegment.from_file(audio_file)
        audio.export(output_audio_file, format="mp3")
        logging.info(f"Audio file converted to MP3: {output_audio_file}")
    except Exception as e:
        logging.error(f"Error converting audio to MP3: {e}")
