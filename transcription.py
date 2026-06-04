import os
import logging
import signal
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

def transcribe_file(file_path, device, cpu_threads, num_workers, language, whisper_model, compute_type, temperature, beam_size, batch_size, condition_on_previous_text, word_timestamps):
    """
    Transcribe the provided file:
      - Convert the file (video/WhatsApp/audio) to MP3 if necessary.
      - Use the Whisper model to transcribe the content.
      - Save the transcript to a file and return the transcription, output file path, and folder.
    """
    try:
        if file_path is None:
            logging.warning("No file path provided for transcription.")
            yield "Please select a file", None, None
            return

        try:
            source_path = validate_local_media_path(file_path)
        except SecurityError as e:
            logging.warning("Rejected transcription input: %s", e)
            yield f"Invalid file: {e}", None, None
            return

        file_path = str(source_path)
        file_name = source_path.name
        folder_path = str(source_path.parent)
        logging.info(f"File name: {file_name}")
        logging.info(f"Using device: {device}")

        model = load_model(whisper_model, compute_type, device, cpu_threads, num_workers)
        if model is None:
            yield "Error loading model", None, None
            return

        # Prepare the audio file in MP3
        audio_file = build_local_output_path(file_path, ".mp3")
        file_ext = source_path.suffix.lower()
        if file_ext != ".mp3":
            if is_video_file(file_path):
                extract_audio_from_video(file_path, str(audio_file))
                file_path = str(audio_file)
            elif is_whatsapp_audio_file(file_path):
                convert_whatsapp_audio_to_mp3(file_path, str(audio_file))
                file_path = str(audio_file)
            elif is_audio_file(file_path):
                convert_audio_to_mp3(file_path, str(audio_file))
                file_path = str(audio_file)
            else:
                yield "Invalid file type", None, None
                return

        logging.info(f"Transcribing {file_path}...")
        batched_model = BatchedInferencePipeline(model=model)
        segments, info = batched_model.transcribe(
            file_path,
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
            yield accumulated_transcription, None, folder_path

        logging.info(f"Transcript generated. Saving transcript to folder: {folder_path}...")
        output_path = build_local_output_path(source_path, "_transcript.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(accumulated_transcription)
        logging.info(f"Transcription saved to: {output_path}")

        # Final yield with output path
        yield accumulated_transcription, str(output_path), folder_path
    except Exception as e:
        logging.error(f"Error transcribing file: {e}")
        yield "Error during transcription", None, None

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
