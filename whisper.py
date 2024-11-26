import gradio as gr
from faster_whisper import WhisperModel
from pydub import AudioSegment
import os
import torch
import subprocess
import shutil
import signal

folder_path = None

def is_whatsapp_audio_file(file_path):
    return file_path.endswith(".opus")

def convert_whatsapp_audio_to_mp3(file_path, output_audio_file):
    try:
        # Load the WhatsApp audio file (commonly in .opus format)
        audio = AudioSegment.from_file(file_path, codec="libopus")
        
        # Export the audio as an MP3 file
        audio.export(output_audio_file, format="mp3")
        
        print(f"Conversion successful! MP3 file saved at: {output_audio_file}")
    except Exception as e:
        print(f"An error occurred: {e}")

def check_ffmpeg_installed():
    if shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg or ffprobe not found. Please install FFmpeg and ensure it's in your system's PATH.")

# Function to check if file is a video
def is_video_file(file_path):
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']  # Add other video extensions if needed
    file_extension = os.path.splitext(file_path)[1].lower()
    return file_extension in video_extensions

# Function to extract audio from video
def extract_audio_from_video(video_file, output_audio_file):
    command = ['ffmpeg', '-i', video_file, '-q:a', '0', '-map', 'a', output_audio_file, '-y']
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    print(f"Audio extracted from video file: {video_file} and saved at: {output_audio_file}")

def load_model(model_size, compute_type, device):
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    print(f"Model loaded: {model_size} | Compute type: {compute_type} | Device: {device}")

    return model

def transcribe_file(file_path, language, model_size, compute_type, beam_size, condition_on_previous_text, word_timestamps, model=None):
    global folder_path
    if file_path is None:
        return "Please upload a file", None

    folder_path = os.path.dirname(os.path.dirname(file_path))

    device = "cuda" if torch.cuda.is_available() else "cpu"

    model = load_model(model_size, compute_type, device)

    if is_video_file(file_path):
        print(f"Extracting audio from video file: {file_path}...")
        audio_file = os.path.splitext(file_path)[0] + ".mp3"
        extract_audio_from_video(file_path, audio_file)
        file_path = audio_file

    if is_whatsapp_audio_file(file_path):
        print(f"Converting WhatsApp audio file to MP3: {file_path}...")
        audio_file = os.path.splitext(file_path)[0] + ".mp3"
        convert_whatsapp_audio_to_mp3(file_path, audio_file)
        file_path = audio_file
    
    print(f"Transcribing {file_path}...")
    segments, info = model.transcribe(file_path, language=language, beam_size=beam_size, condition_on_previous_text=condition_on_previous_text, word_timestamps=word_timestamps)
    
    transcription = ""
    for segment in segments:
        if word_timestamps:
            for word in segment.words:
                transcription += f"{word.start:.2f} -> {word.end:.2f} {word.word}\n"	
        else:
            transcription += f"{segment.text}\n"     

    # Save the transcript immediately
    output_path = os.path.join(folder_path, "transcript.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcription)

    return transcription, output_path

# Function to clear a folder
def clear(folder_path):
    if folder_path:
        # Check if the folder exists
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            print(f"Deleted folder: {folder_path}")
        else:
            print(f"Folder does not exist: {folder_path}")

# Function to clear a folder and close the script
def clear_and_close(folder_path):
    if folder_path:
        # Check if the folder exists
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            print(f"Deleted folder: {folder_path}")
        else:
            print(f"Folder does not exist: {folder_path}")

    # Terminate the script
    os.kill(os.getpid(), signal.SIGINT)  # Send interrupt signal to stop the app

# Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("# Audio/Video Transcription using Whisper Model")

    file_input = gr.File()
    
    with gr.Row():
        gr.Markdown("""
        ## Configuration
        ### Legend:
        - **Model Size**: Larger models are more accurate but slower and require more memory.
        - **Compute Type**: float16 is faster, float32 is more precise, int8 is fastest but less accurate.
        - **Beam Size**: Higher values may improve accuracy but increase processing time.
        - **Condition on Previous Text**: If checked, uses previous text to improve transcription continuity.
        - **Word-level timestamps**: If checked, provides timestamps for individual words instead of sentences.
        """)
        
    with gr.Row():
        language = gr.Dropdown(choices=["en", "it", "fr", "de", "es"], value="en", label="Language")
        model_size = gr.Dropdown(choices=["tiny", "base", "small", "medium", "large-v3"], value="large-v3", label="Model Size")
    with gr.Row():
        compute_type = gr.Dropdown(choices=["float16", "float32", "int8"], value="float16", label="Compute Type")
        beam_size = gr.Slider(minimum=1, maximum=10, value=4, step=1, label="Beam Size")
    with gr.Row():
        condition_on_previous_text = gr.Checkbox(label="Condition on Previous Text")
        word_timestamps = gr.Checkbox(label="Word-level timestamps")

    output_text = gr.Textbox(label="Transcription (to select all the content click the textbox and press the key combination Ctrl+A)")
    download_output = gr.File(label="Download Transcript")
    transcribe_button = gr.Button("Transcribe")

    with gr.Row():
        clear_button = gr.Button("Clear")
        close_and_clear_button = gr.Button("Clear and Close")

    transcribe_button.click(
        transcribe_file, 
        inputs=[file_input, language, model_size, compute_type, beam_size, condition_on_previous_text, word_timestamps], 
        outputs=[output_text, download_output]
    )
    
    clear_button.click(lambda: clear(folder_path), inputs=[], outputs=[])
    close_and_clear_button.click(lambda: clear_and_close(folder_path), inputs=[], outputs=[file_input, output_text])

if __name__ == "__main__":
    check_ffmpeg_installed()
    demo.launch()