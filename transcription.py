import os
import sys
import logging
import signal

# Windows DLL directory loading helper for Python >= 3.8
if sys.platform == "win32":
    added_paths = set()
    # 1. Search PATH for CUDA/cuDNN/NVIDIA directories and add them
    path_env = os.environ.get("PATH", "")
    for directory in path_env.split(os.path.pathsep):
        if not directory:
            continue
        dir_upper = directory.upper()
        if "NVIDIA" in dir_upper or "CUDA" in dir_upper or "CUDNN" in dir_upper:
            if os.path.isdir(directory) and directory not in added_paths:
                try:
                    os.add_dll_directory(directory)
                    added_paths.add(directory)
                except Exception:
                    pass
    # 2. Check environment variables starting with CUDA_PATH
    for k, v in os.environ.items():
        if k.startswith("CUDA_PATH") and os.path.isdir(v):
            bin_dir = os.path.join(v, "bin")
            if os.path.isdir(bin_dir) and bin_dir not in added_paths:
                try:
                    os.add_dll_directory(bin_dir)
                    added_paths.add(bin_dir)
                except Exception:
                    pass

try:
    import torch
except ImportError:
    pass

from faster_whisper import WhisperModel, BatchedInferencePipeline
from audio_processing import is_video_file, extract_audio_from_video, is_whatsapp_audio_file, convert_whatsapp_audio_to_mp3, is_audio_file, convert_audio_to_mp3
from security_utils import (
    SecurityError,
    build_local_output_path,
    remove_controlled_tree,
    validate_local_media_path,
)

def load_model(model_size, compute_type, device, cpu_threads, num_workers):
    """Load the Whisper model with the specified parameters."""
    try:
        logging.info(f"Loading model: {model_size} | Compute type: {compute_type} | Device: {device} | CPU Threads: {cpu_threads} | Number of Workers: {num_workers}...")
        model = WhisperModel(model_size, device=device, compute_type=compute_type, cpu_threads=cpu_threads, num_workers=num_workers)
        logging.info("Model loaded successfully.")
        return model
    except Exception as e:
        logging.error(f"Error loading model: {e}")
        return None

def transcribe_file(file_paths, device, cpu_threads, num_workers, language, whisper_model, compute_type, temperature, beam_size, batch_size, condition_on_previous_text, word_timestamps):
    """
    Transcribe the provided files:
      - Convert the file (video/WhatsApp/audio) to MP3 if necessary.
      - Use the Whisper model to transcribe the content.
      - Save the transcript to a file and return the transcription, output file path, and folder.
    """
    try:
        if not file_paths:
            logging.warning("No file paths provided for transcription.")
            yield "Please select a file", None, None
            return

        if isinstance(file_paths, str):
            file_paths = [file_paths]

        logging.info(f"Using device: {device}")
        model = load_model(whisper_model, compute_type, device, cpu_threads, num_workers)
        if model is None:
            yield "Error loading model", None, None
            return

        batched_model = BatchedInferencePipeline(model=model)
        
        session_transcription = ""
        total_files = len(file_paths)
        for index, file_path_str in enumerate(file_paths, 1):
            try:
                source_path = validate_local_media_path(file_path_str)
            except SecurityError as e:
                logging.warning("Rejected transcription input: %s", e)
                yield f"Invalid file: {e}", None, None
                continue
                
            current_file_path = str(source_path)
            file_name = source_path.name
            folder_path = str(source_path.parent)
            logging.info(f"Processing file {index}/{total_files}: {file_name}")
            
            header = f"### File {index}/{total_files}: {file_name}\n\n"
            yield session_transcription + header + "Converting/Preparing audio...", None, folder_path
            
            # Prepare the audio file in MP3
            audio_file = build_local_output_path(current_file_path, ".mp3")
            file_ext = source_path.suffix.lower()
            if file_ext != ".mp3":
                if is_video_file(current_file_path):
                    extract_audio_from_video(current_file_path, str(audio_file))
                    current_file_path = str(audio_file)
                elif is_whatsapp_audio_file(current_file_path):
                    convert_whatsapp_audio_to_mp3(current_file_path, str(audio_file))
                    current_file_path = str(audio_file)
                elif is_audio_file(current_file_path):
                    convert_audio_to_mp3(current_file_path, str(audio_file))
                    current_file_path = str(audio_file)
                else:
                    yield session_transcription + header + "Invalid file type", None, folder_path
                    session_transcription += header + "Invalid file type\n\n---\n\n"
                    continue

            logging.info(f"Transcribing {current_file_path}...")
            yield session_transcription + header + "Transcribing...", None, folder_path
            
            segments, info = batched_model.transcribe(
                current_file_path,
                batch_size=batch_size,
                language=language,
                beam_size=beam_size,
                condition_on_previous_text=condition_on_previous_text,
                word_timestamps=word_timestamps,
                temperature=temperature
            )

            logging.info("File transcribed successfully, generating transcript...")
            accumulated_transcription = ""

            # Iterate over segments and yield progressively
            for segment in segments:
                if word_timestamps:
                    chunk = "\n".join(f"{word.start:.2f} -> {word.end:.2f} {word.word}" for word in segment.words) + "\n"
                else:
                    chunk = segment.text + "\n"
                
                accumulated_transcription += chunk
                # Yield partial result. Output path is None until transcription is complete.
                yield session_transcription + header + accumulated_transcription, None, folder_path

            logging.info(f"Transcript generated. Saving transcript to folder: {folder_path}...")
            output_path = build_local_output_path(source_path, "_transcript.txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(accumulated_transcription)
            logging.info(f"Transcription saved to: {output_path}")

            # Final yield with output path for the current file
            yield session_transcription + header + accumulated_transcription, str(output_path), folder_path
            
            session_transcription += header + accumulated_transcription + "\n\n---\n\n"
            
    except Exception as e:
        logging.error(f"Error transcribing file: {e}")
        yield f"Error during transcription: {e}", None, None

def clear(folder_path):
    """Delete the specified folder (if it exists)."""
    try:
        if folder_path and os.path.exists(folder_path):
            logging.info(f"Clearing folder: {folder_path}...")
            remove_controlled_tree(folder_path)
            logging.info(f"Deleted folder: {folder_path}")
        else:
            logging.warning(f"Folder does not exist: {folder_path}")
    except Exception as e:
        logging.error(f"Error clearing folder: {e}")

def clear_and_close(folder_path):
    """Delete the folder and terminate the script."""
    try:
        if folder_path and os.path.exists(folder_path):
            logging.info(f"Clearing folder: {folder_path}...")
            remove_controlled_tree(folder_path)
            logging.info(f"Deleted folder: {folder_path}")
        else:
            logging.warning(f"Folder does not exist: {folder_path}")

        logging.info("Terminating the script...")
        os.kill(os.getpid(), signal.SIGINT)
    except Exception as e:
        logging.error(f"Error clearing folder and closing script: {e}")
