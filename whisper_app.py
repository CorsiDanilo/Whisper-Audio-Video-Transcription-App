import gradio as gr
from faster_whisper import WhisperModel
from pydub import AudioSegment
import os
import torch
import subprocess
import shutil
import signal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the GEMINI_API_KEY from the environment variables
try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    try:
        import google.generativeai as genai
    except ImportError:
        print("Installing the generativeai package...")
        subprocess.run(["pip", "install", "google-generativeai"])
        import google.generativeai as genai
except Exception as e:
    print(f"Error loading environment variables: {e}")
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
    print("Checking if FFmpeg is installed...")
    if shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg or ffprobe not found. Please install FFmpeg and ensure it's in your system's PATH.")
except Exception as e:
    print(f"Error checking FFmpeg installation: {e}")

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
        return f"Error querying Gemini: {e}"

def is_whatsapp_audio_file(file_path):
    whatsapp_audio_extensions = ['.opus']  # Add other WhatsApp audio extensions if needed
    file_extension = os.path.splitext(file_path)[1].lower()
    is_whatsapp_audio = file_extension in whatsapp_audio_extensions
    return is_whatsapp_audio

def convert_whatsapp_audio_to_mp3(file_path, output_audio_file):
    try:
        print(f"Converting WhatsApp audio file to MP3: {file_path}...")
        # Load the WhatsApp audio file (commonly in .opus format)
        audio = AudioSegment.from_file(file_path, codec="libopus")
        
        # Export the audio as an MP3 file
        audio.export(output_audio_file, format="mp3")
        
        print(f"WhatsApp audio file converted to MP3: {output_audio_file}")
    except Exception as e:
        print(f"Error converting WhatsApp audio to MP3: {e}")

# Function to check if file is a video
def is_video_file(file_path):
    try:
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']  # Add other video extensions if needed
        file_extension = os.path.splitext(file_path)[1].lower()
        is_video = file_extension in video_extensions
        return is_video
    except Exception as e:
        print(f"Error checking if file is a video: {e}")
        return False

# Function to extract audio from video
def extract_audio_from_video(video_file, output_audio_file):
    try:
        print(f"Extracting audio from video file: {video_file}...")
        command = ['ffmpeg', '-i', video_file, '-q:a', '0', '-map', 'a', output_audio_file, '-y']
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Audio extracted to: {output_audio_file}")
    except Exception as e:
        print(f"Error extracting audio from video: {e}")

    print(f"Audio extracted from video file: {video_file} and saved at: {output_audio_file}")

def load_model(model_size, compute_type, device):
    try:
        print(f"Loading model: {model_size} | Compute type: {compute_type} | Device: {device}...")
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print(f"Model loaded successfully.")
        return model
    except Exception as e:
        print(f"Error loading model: {e}")
        return None

def transcribe_file(file_path, language, model_size, compute_type, beam_size, condition_on_previous_text, word_timestamps, model=None):
    global folder_path
    try:
        if file_path is None:
            return "Please upload a file", None

        global file_name

        # Replace spaces in file name with underscores
        file_name = os.path.basename(file_path)
        print(f"File name: {file_name}")

        folder_path = os.path.dirname(os.path.dirname(file_path))
        print(f"Folder path: {folder_path}")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")

        model = load_model(model_size, compute_type, device)
        if model is None:
            return "Error loading model", None

        if is_video_file(file_path):
            audio_file = os.path.splitext(file_path)[0] + ".mp3"
            extract_audio_from_video(file_path, audio_file)
            file_path = audio_file

        if is_whatsapp_audio_file(file_path):
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
        output_path = os.path.join(folder_path, f"{os.path.splitext(file_name)[0]}_transcript.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(transcription)
        print(f"Transcription saved to: {output_path}")

        return transcription, output_path
    except Exception as e:
        print(f"Error transcribing file: {e}")
        return "Error during transcription", None

# Function to clear a folder
def clear(folder_path):
    try:
        if folder_path:
            print(f"Clearing folder: {folder_path}...")
            # Check if the folder exists
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                print(f"Deleted folder: {folder_path}")
            else:
                print(f"Folder does not exist: {folder_path}")
                
    except Exception as e:
        print(f"Error clearing folder: {e}")

# Function to clear a folder and close the script
def clear_and_close(folder_path):
    try:
        if folder_path:
            print(f"Clearing folder: {folder_path}...")
            # Check if the folder exists
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                print(f"Deleted folder: {folder_path}")
            else:
                print(f"Folder does not exist: {folder_path}")

        # Terminate the script
        print("Terminating the script...")
        os.kill(os.getpid(), signal.SIGINT)  # Send interrupt signal to stop the app
    except Exception as e:
        print(f"Error clearing folder and closing script: {e}")

# Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("# Audio/Video Transcription using Whisper Model")

    file_input = gr.File()
    
    try:
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
            language = gr.Dropdown(choices=["en", "it", "fr", "de", "es"], value="it", label="Language")
            model_size = gr.Dropdown(choices=["tiny", "base", "small", "medium", "large-v3"], value="large-v3", label="Model Size")
        with gr.Row():
            compute_type = gr.Dropdown(choices=["float16", "float32", "int8"], value="float16", label="Compute Type")
            beam_size = gr.Slider(minimum=1, maximum=10, value=4, step=1, label="Beam Size")
        with gr.Row():
            condition_on_previous_text = gr.Checkbox(label="Condition on Previous Text")
            word_timestamps = gr.Checkbox(label="Word-level timestamps")
            
        with gr.Accordion("Transcription"):
            output_text = gr.Markdown("*Your transcription will appear here.*", show_copy_button=True, container=True, line_breaks=True, max_height=400)

        download_output = gr.File(label="Download Transcript")
        transcribe_button = gr.Button("Transcribe", variant="secondary")

        if GEMINI_API_KEY:
                gr.Markdown("## Gemini Interaction")
                model_choice = gr.Radio(choices=["gemini-1.5-flash", "gemini-1.5-pro"], value="gemini-1.5-pro", label="Choose Gemini Model")
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
                    print(f"Error during Gemini query setup: {e}")
                    
        with gr.Row():
            clear_button = gr.Button("Clear temporary files", variant="primary")
            close_and_clear_button = gr.Button("Clear temporary files and Close", variant="stop")

        try:
            transcribe_button.click(
                transcribe_file, 
                inputs=[file_input, language, model_size, compute_type, beam_size, condition_on_previous_text, word_timestamps], 
                outputs=[output_text, download_output]
            )
        except Exception as e:
            print(f"Error during transcription setup: {e}")

        try:
            clear_button.click(lambda: clear(folder_path), inputs=[], outputs=[])
            close_and_clear_button.click(lambda: clear_and_close(folder_path), inputs=[], outputs=[file_input, output_text])
        except Exception as e:
            print(f"Error during button setup: {e}")

    except Exception as e:
        print(f"Error in interface setup: {e}")

if __name__ == "__main__":
    demo.launch()