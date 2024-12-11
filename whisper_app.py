import gradio as gr
from faster_whisper import WhisperModel, BatchedInferencePipeline
from pydub import AudioSegment
import os
import torch
import subprocess
import shutil
import signal
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("application.log"),
        logging.StreamHandler()
    ]
)

default_values = {
    "input_file": None,
    "language": "it",
    "model_size": "large-v3",
    "compute_type": "float16",
    "beam_size": 4,
    "batch_size": 8,
    "condition_on_previous_text": False,
    "word_timestamps": False,
    "output_text": "*Your transcription will appear here.*",
    "download_output": None,
    "model_choice": "gemini-1.5-pro",
    "user_query": "",
    "gemini_response": "*Gemini response will appear here.*"
}

# Load environment variables
load_dotenv()

# Add the GEMINI_API_KEY from the environment variables
try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    try:
        import google.generativeai as genai
    except ImportError:
        logging.info("Installing the generativeai package...")
        subprocess.run(["pip", "install", "google-generativeai"])
        import google.generativeai as genai
except Exception as e:
    logging.error(f"Error loading environment variables: {e}")
    GEMINI_API_KEY = None

def initialize_model(model_choice):
    # API parameters
    REQUESTS_PER_MINUTE = 15	
    REQUESTS_PER_DAY = 1500
    TOKENS_PER_MINUTE = 1048576
    INPUT_TOKENS = TOKENS_PER_MINUTE

    # Model parameters
    TEMPERATURE = 1
    TOP_P = 0.95
    TOP_K = 40
    MAX_OUTPUT_TOKENS = 8192
    RESPONSE_MIME_TYPE = "text/plain"

    def gemini_configurations():
        generation_config = {
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "top_k": TOP_K,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "response_mime_type": RESPONSE_MIME_TYPE,
        }

        safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE",
        },
        ]

        return generation_config, safety_settings

    # Set up the API key
    genai.configure(api_key=GEMINI_API_KEY)

    # Gemini model configurations
    generation_config, safety_settings = gemini_configurations()

    model = genai.GenerativeModel(
    model_name=model_choice,
    safety_settings=safety_settings,
    generation_config=generation_config,
    )

    return model

try:
    logging.info("Checking if FFmpeg is installed...")
    if shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg or ffprobe not found. Please install FFmpeg and ensure it's in your system's PATH.")
except Exception as e:
    logging.error(f"Error checking FFmpeg installation: {e}")

folder_path = None
file_name = None

# Function to query Gemini API
def query_gemini(user_input, transcription, model_choice):
    try:
        model = initialize_model(model_choice)
        query = f"""
        Transcription: {transcription}\n\n
        User Input: {user_input}
        """

        response = model.generate_content(query).text
        return response
    except Exception as e:
        logging.error(f"Error querying Gemini: {e}")
        return f"Error querying Gemini: {e}"

def is_whatsapp_audio_file(file_path):
    whatsapp_audio_extensions = ['.opus']  # Add other WhatsApp audio extensions if needed
    file_extension = os.path.splitext(file_path)[1].lower()
    is_whatsapp_audio = file_extension in whatsapp_audio_extensions
    return is_whatsapp_audio

def convert_whatsapp_audio_to_mp3(file_path, output_audio_file):
    try:
        logging.info(f"Converting WhatsApp audio file to MP3: {file_path}...")
        # Load the WhatsApp audio file (commonly in .opus format)
        audio = AudioSegment.from_file(file_path, codec="libopus")
        
        # Export the audio as an MP3 file
        audio.export(output_audio_file, format="mp3")
        
        logging.info(f"WhatsApp audio file converted to MP3: {output_audio_file}")
    except Exception as e:
        logging.error(f"Error converting WhatsApp audio to MP3: {e}")

# Function to check if file is a video
def is_video_file(file_path):
    try:
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']  # Add other video extensions if needed
        file_extension = os.path.splitext(file_path)[1].lower()
        is_video = file_extension in video_extensions
        return is_video
    except Exception as e:
        logging.error(f"Error checking if file is a video: {e}")
        return False

# Function to check if file is an audio file
def is_audio_file(file_path):
    try:
        audio_extensions = ['.mp3', '.wav', '.flac', '.ogg', '.m4a']  # Add other audio extensions if needed
        file_extension = os.path.splitext(file_path)[1].lower()
        is_audio = file_extension in audio_extensions
        return is_audio
    except Exception as e:
        logging.error(f"Error checking if file is an audio file: {e}")
        return False

# Function to extract audio from video
def extract_audio_from_video(video_file, output_audio_file):
    try:
        logging.info(f"Extracting audio from video file: {video_file}...")
        command = ['ffmpeg', '-i', video_file, '-q:a', '0', '-map', 'a', output_audio_file, '-y']
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"Audio extracted to: {output_audio_file}")
    except Exception as e:
        logging.error(f"Error extracting audio from video: {e}")

# Function to convert audio file to MP3
def convert_audio_to_mp3(audio_file, output_audio_file):
    try:
        logging.info(f"Converting audio file to MP3: {audio_file}...")
        # Load the audio file
        audio = AudioSegment.from_file(audio_file)
        
        # Export the audio as an MP3 file
        audio.export(output_audio_file, format="mp3")
        
        logging.info(f"Audio file converted to MP3: {output_audio_file}")
    except Exception as e:
        logging.error(f"Error converting audio to MP3: {e}")

def load_model(model_size, compute_type, device):
    try:
        logging.info(f"Loading model: {model_size} | Compute type: {compute_type} | Device: {device}...")
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logging.info("Model loaded successfully.")
        return model
    except Exception as e:
        logging.error(f"Error loading model: {e}")
        return None

def transcribe_file(file_path, language, model_size, compute_type, beam_size, batch_size, condition_on_previous_text, word_timestamps, model=None):
    global folder_path
    try:
        if file_path is None:
            logging.warning("No file uploaded for transcription.")
            return "Please upload a file", None

        global file_name

        # Replace spaces in file name with underscores
        file_name = os.path.basename(file_path)
        logging.info(f"File name: {file_name}")

        folder_path = os.path.dirname(os.path.dirname(file_path))
        logging.info(f"Folder path: {folder_path}")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logging.info(f"Using device: {device}")

        model = load_model(model_size, compute_type, device)
        if model is None:
            return "Error loading model", None

        audio_file = os.path.splitext(file_path)[0] + ".mp3"
        if is_video_file(file_path):
            extract_audio_from_video(file_path, audio_file)
            file_path = audio_file
        if is_whatsapp_audio_file(file_path):
            convert_whatsapp_audio_to_mp3(file_path, audio_file)
            file_path = audio_file
        if is_audio_file(file_path):
            convert_audio_to_mp3(file_path, audio_file)
            file_path = audio_file

        logging.info(f"Transcribing {file_path}...")
        # segments, info = model.transcribe(file_path, language=language, beam_size=beam_size, condition_on_previous_text=condition_on_previous_text, word_timestamps=word_timestamps)
        batched_model = BatchedInferencePipeline(model=model)
        segments, info = batched_model.transcribe(file_path, batch_size=batch_size, language=language, beam_size=beam_size, condition_on_previous_text=condition_on_previous_text, word_timestamps=word_timestamps)

        logging.info("File transcribed successfully, generating transcript...")
        
        transcription = ""
        if word_timestamps:
            transcription = "\n".join(
                f"{word.start:.2f} -> {word.end:.2f} {word.word}"
                for segment in segments for word in segment.words
            )
        else:
            transcription = "\n".join(segment.text for segment in segments)

        logging.info(f"Transcript generated. Saving transcript to: {folder_path}...")

        # Save the transcript and replace spaces with underscores
        filename = os.path.splitext(file_name)[0].replace(" ", "_")
        output_path = os.path.join(folder_path, f"{filename}_transcript.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(transcription)
        logging.info(f"Transcription saved to: {output_path}")

        return transcription, output_path
    except Exception as e:
        logging.error(f"Error transcribing file: {e}")
        return "Error during transcription", None

# Function to clear a folder
def clear(folder_path):
    try:
        if folder_path:
            logging.info(f"Clearing folder: {folder_path}...")
            # Check if the folder exists
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                logging.info(f"Deleted folder: {folder_path}")
            else:
                logging.warning(f"Folder does not exist: {folder_path}")
                
    except Exception as e:
        logging.error(f"Error clearing folder: {e}")

# Function to clear a folder and close the script
def clear_and_close(folder_path):
    try:
        if folder_path:
            logging.info(f"Clearing folder: {folder_path}...")
            # Check if the folder exists
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                logging.info(f"Deleted folder: {folder_path}")
            else:
                logging.warning(f"Folder does not exist: {folder_path}")

        # Terminate the script
        logging.info("Terminating the script...")
        os.kill(os.getpid(), signal.SIGINT)  # Send interrupt signal to stop the app
    except Exception as e:
        logging.error(f"Error clearing folder and closing script: {e}")

def reset_fields():
    return (
        default_values["input_file"],
        default_values["language"],
        default_values["model_size"],
        default_values["compute_type"],
        default_values["beam_size"],
        default_values["batch_size"],
        default_values["condition_on_previous_text"],
        default_values["word_timestamps"],
        default_values["output_text"],
        default_values["download_output"],
        default_values["model_choice"],
        default_values["user_query"],
        default_values["gemini_response"]
    )

# Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("# 🎤 Audio/Video Transcription using Whisper Model")

    file_input = gr.File()
    
    try:
        with gr.Row():
            gr.Markdown("""
            ## Configuration
            ### Legend:
            - **Model Size**: Larger models are more accurate but slower and require more memory.
            - **Compute Type**: float16 is faster, float32 is more precise, int8 is fastest but less accurate.
            - **Beam Size**: Higher values may improve accuracy but increase processing time.
            - **Batch Size**: Higher values may improve processing time but require more memory.
            - **Condition on Previous Text**: If checked, uses previous text to improve transcription continuity.
            - **Word-level timestamps**: If checked, provides timestamps for individual words instead of sentences.
            """)

        with gr.Row():
            language = gr.Dropdown(choices=["en", "it", "fr", "de", "es"], value=default_values["language"], label="Language")
            model_size = gr.Dropdown(choices=["tiny", "base", "small", "medium", "large-v3"], value=default_values["model_size"], label="Model Size")
        with gr.Row():
            compute_type = gr.Dropdown(choices=["float16", "float32", "int8"], value=default_values["compute_type"], label="Compute Type")
            beam_size = gr.Slider(minimum=1, maximum=10, value=default_values["beam_size"], step=1, label="Beam Size")
            batch_size = gr.Slider(minimum=1, maximum=16, value=default_values["batch_size"], step=1, label="Batch Size")
        with gr.Row():
            condition_on_previous_text = gr.Checkbox(label="Condition on Previous Text")
            word_timestamps = gr.Checkbox(label="Word-level timestamps")
            
        with gr.Accordion("Transcription"):
            output_text = gr.Markdown("*Your transcription will appear here.*", show_copy_button=True, container=True, line_breaks=True, max_height=400)

        download_output = gr.File(label="Download Transcript")
        transcribe_button = gr.Button("Transcribe", variant="secondary")

        if GEMINI_API_KEY:
            gr.Markdown("## Gemini Interaction")
            model_choice = gr.Radio(choices=["gemini-1.5-flash", "gemini-1.5-pro"], value=default_values["model_choice"], label="Choose Gemini Model")
            user_query = gr.Textbox(label="Enter your query")
            with gr.Accordion("Gemini Response"):
                gemini_response = gr.Markdown("*Gemini response will appear here.*", show_copy_button=True, container=True, line_breaks=True, max_height=400)

            submit_query_button = gr.Button("Submit Query to Gemini", variant="secondary")

            try:
                submit_query_button.click(
                    query_gemini,
                    inputs=[user_query, output_text, model_choice],
                    outputs=[gemini_response]
                )
            except Exception as e:
                logging.error(f"Error during Gemini query setup: {e}")
                    
        with gr.Row():
            reset_button = gr.Button("Reset fields", variant="secondary")  # Add reset button
            clear_button = gr.Button("Clear temp files", variant="primary")
            close_and_clear_button = gr.Button("Clear temp files and quit", variant="stop")

        # Reset button functionality
        reset_button.click(
            reset_fields,  # Call the reset function
            inputs=[],  # No inputs
            outputs=[file_input, language, model_size, compute_type, beam_size, batch_size, condition_on_previous_text, word_timestamps, output_text, download_output, model_choice, user_query, gemini_response]  # Reset all fields
        )

        try:
            transcribe_button.click(
                transcribe_file, 
                inputs=[file_input, language, model_size, compute_type, beam_size, batch_size, condition_on_previous_text, word_timestamps], 
                outputs=[output_text, download_output]
            )
        except Exception as e:
            logging.error(f"Error during transcription setup: {e}")

        try:
            clear_button.click(lambda: clear(folder_path), inputs=[], outputs=[])
            close_and_clear_button.click(lambda: clear_and_close(folder_path), inputs=[], outputs=[file_input, output_text])
        except Exception as e:
            logging.error(f"Error during button setup: {e}")

    except Exception as e:
        logging.error(f"Error in interface setup: {e}")

if __name__ == "__main__":
    demo.launch(debug=True)