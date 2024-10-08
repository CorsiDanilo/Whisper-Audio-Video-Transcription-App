import gradio as gr
from faster_whisper import WhisperModel
import os
import torch
import subprocess  # To run ffmpeg commands
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

# Function to handle the transcription
def transcribe_audio(file_path):
    if file_path is None:
        return "Please upload a file"

    # Save the folder path for later deletion
    global folder_path
    folder_path = os.path.dirname(os.path.dirname(file_path))  # Get the parent folder of the file

    # Check if the file is a video
    if is_video_file(file_path):
        # Extract audio from video
        print(f"Extracting audio from video file: {file_path}...")
        audio_file = os.path.splitext(file_path)[0] + ".mp3"  # Save as an MP3 file
        extract_audio_from_video(file_path, audio_file)
        file_path = audio_file  # Use the extracted audio for transcription
    
    # Perform transcription
    print(f"Transcribing {file_path}...")
    segments, info = model.transcribe(file_path, language=language, beam_size=beam_size, condition_on_previous_text=condition_on_previous_text)
    
    # Compile transcription text
    transcription = ""
    for segment in segments:
        transcription += f"{segment.text}\n"

    return transcription

# Function to clear a folder and close the script
def clear_and_close(folder_path):
    if folder_path:
        shutil.rmtree(folder_path)
        print(f"Deleted folder: {folder_path}")

    # Terminate the script
    os.kill(os.getpid(), signal.SIGINT)  # Send interrupt signal to stop the app

def upload_file(file):
    file_path = file
    return file_path

# Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("### Audio/Video Transcription using Whisper Model")
    
    # Use 'filepath' type for audio input
    file_input = gr.File()
    output_text = gr.Textbox(label="Transcription (to select all the content click the textbox and press the key combination Ctrl+A)")

    transcribe_button = gr.Button("Transcribe")
    close_button = gr.Button("Close and Clear")

    # Link the buttons to their respective functions
    transcribe_button.click(transcribe_audio, inputs=file_input, outputs=output_text)
    close_button.click(lambda: clear_and_close(folder_path), inputs=[], outputs=[])

if __name__ == "__main__":
    # Run this check at the start of your script
    check_ffmpeg_installed()

    # Launch the app
    demo.launch()