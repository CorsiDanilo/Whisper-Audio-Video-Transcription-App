import gradio as gr
from faster_whisper import WhisperModel
import os
import torch
import subprocess
import shutil
import signal

folder_path = None

def check_ffmpeg_installed():
    if shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg or ffprobe not found. Please install FFmpeg and ensure it's in your system's PATH.")

# Model configuration
language = "it" # Change to "en" for English
model_size = "large-v3" # Default: large-v3, change to "small-v3" for a smaller model
compute_type = "float32" # Default: float16, change to "float32" for higher precision
beam_size = 4 # Default 4, change to 1 for faster inference
condition_on_previous_text = False # Change to True to condition on previous text
device = "cuda" if torch.cuda.is_available() else "cpu" 

# Load model
model = WhisperModel(model_size, device=device, compute_type=compute_type)

print(f"Model loaded: {model_size} | Language: {language} | Compute type: {compute_type} | Beam size: {beam_size} | Condition on previous text: {condition_on_previous_text} | Device: {device}")

# Function to check if file is a video
def is_video_file(file_path):
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']  # Add other video extensions if needed
    file_extension = os.path.splitext(file_path)[1].lower()
    return file_extension in video_extensions

# Function to extract audio from video
def extract_audio_from_video(video_file, output_audio_file):
    command = ['ffmpeg', '-i', video_file, '-q:a', '0', '-map', 'a', output_audio_file, '-y']
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def transcribe_file(file_path):
    if file_path is None:
        return "Please upload a file", None

    global folder_path
    folder_path = os.path.dirname(os.path.dirname(file_path))

    if is_video_file(file_path):
        print(f"Extracting audio from video file: {file_path}...")
        audio_file = os.path.splitext(file_path)[0] + ".mp3"
        extract_audio_from_video(file_path, audio_file)
        file_path = audio_file
    
    print(f"Transcribing {file_path}...")
    segments, info = model.transcribe(file_path, language=language, beam_size=beam_size, condition_on_previous_text=condition_on_previous_text)
    
    transcription = ""
    for segment in segments:
        transcription += f"{segment.text}\n"

    # Save the transcript immediately
    output_path = os.path.join(folder_path, "transcript.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcription)

    return transcription, output_path

# Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("### Audio/Video Transcription using Whisper Model")
    
    file_input = gr.File()
    output_text = gr.Textbox(label="Transcription (to select all the content click the textbox and press the key combination Ctrl+A)")
    download_output = gr.File(label="Download Transcript")

    transcribe_button = gr.Button("Transcribe")
    close_button = gr.Button("Close and Clear")

    transcribe_button.click(
        transcribe_file, 
        inputs=file_input, 
        outputs=[output_text, download_output]
    )
    
    close_button.click(lambda: clear_and_close(folder_path), inputs=[], outputs=[])

if __name__ == "__main__":
    check_ffmpeg_installed()
    demo.launch()