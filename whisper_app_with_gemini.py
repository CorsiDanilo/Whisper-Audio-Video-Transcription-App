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
import yaml

# Load default values
with open("default/default_values.yaml", "r") as ymlfile:
    default_values = yaml.safe_load(ymlfile)
 
# Load default configuration values
with open("configurations/default.yaml", "r") as ymlfile:
    default_config_values = yaml.safe_load(ymlfile)

# Configure logging
log_file = "whisper.log"
if os.path.exists(log_file):
    os.remove(log_file)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

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

def initialize_model(gemini_model):
    def gemini_configurations():
        gemini_config = default_values['gemini']
        generation_config = {
            "temperature": gemini_config["temperature"],
            "top_p": gemini_config["top_p"],
            "top_k": gemini_config["top_k"],
            "max_output_tokens": gemini_config["max_output_tokens"],
            "response_mime_type": gemini_config["response_mime_type"],
        }

        safety_settings = [
            {
            "category": gemini_config['safety_settings']["harm_category_harassment"]['name'],
            "threshold": gemini_config['safety_settings']["harm_category_harassment"]['threshold'],
            },
            {
            "category": gemini_config['safety_settings']["harm_category_hate_speech"]['name'],
            "threshold": gemini_config['safety_settings']["harm_category_hate_speech"]['threshold'],
            },
            {
            "category": gemini_config['safety_settings']["harm_category_sexually_explicit"]['name'],
            "threshold": gemini_config['safety_settings']["harm_category_sexually_explicit"]['threshold'],
            },
            {
            "category": gemini_config['safety_settings']["harm_category_dangerous_content"]['name'],
            "threshold": gemini_config['safety_settings']["harm_category_dangerous_content"]['threshold']
            },
        ]

        return generation_config, safety_settings

    # Set up the API key
    genai.configure(api_key=GEMINI_API_KEY)

    # Gemini model configurations
    generation_config, safety_settings = gemini_configurations()

    model = genai.GenerativeModel(
    model_name=gemini_model,
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
def query_gemini(user_input, transcription, gemini_model):
    try:
        model = initialize_model(gemini_model)
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
        video_extensions = default_values['default_values']['video_extensions']  # Add other video extensions if needed
        file_extension = os.path.splitext(file_path)[1].lower()
        is_video = file_extension in video_extensions
        return is_video
    except Exception as e:
        logging.error(f"Error checking if file is a video: {e}")
        return False

# Function to check if file is an audio file
def is_audio_file(file_path):
    try:
        audio_extensions = default_values['default_values']['audio_extensions']  # Add other audio extensions if needed
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

def load_model(model_size, compute_type, device, cpu_threads, num_workers):
    try:
        logging.info(f"Loading model: {model_size} | Compute type: {compute_type} | Device: {device} | CPU Threads: {cpu_threads} | Number of Workers: {num_workers}...")
        model = WhisperModel(model_size, device=device, compute_type=compute_type, cpu_threads=cpu_threads, num_workers=num_workers)
        logging.info("Model loaded successfully.")
        return model
    except Exception as e:
        logging.error(f"Error loading model: {e}")
        return None

def transcribe_file(file_path,
                    device,   
                    cpu_threads,
                    num_workers, 
                    language, 
                    whisper_model, 
                    compute_type, 
                    temperature,
                    beam_size, 
                    batch_size, 
                    condition_on_previous_text, 
                    word_timestamps, 
                    ):
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

        logging.info(f"Using device: {device}")

        model = load_model(whisper_model, compute_type, device, cpu_threads, num_workers)
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
        batched_model = BatchedInferencePipeline(model=model)
        segments, info = batched_model.transcribe(file_path, batch_size=batch_size, language=language, beam_size=beam_size, condition_on_previous_text=condition_on_previous_text, word_timestamps=word_timestamps, temperature=temperature)

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

# Load configuration button functionality
def load_configuration_file(file_path):
    try:
        config = yaml.safe_load(open(file_path.name, "r"))
        return (
            config["device"],
            config["cpu_threads"],
            config["num_workers"],
            config["language"],
            config["whisper_model"],
            config["compute_type"],
            config["temperature"],
            config["beam_size"],
            config["batch_size"],
            config["condition_on_previous_text"],
            config["word_timestamps"],
        )
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        return (
            default_config_values["device"],
            default_config_values["cpu_threads"],
            default_config_values["num_workers"],
            default_config_values["language"],
            default_config_values["whisper_model"],
            default_config_values["compute_type"],
            default_config_values["temperature"],
            default_config_values["beam_size"],
            default_config_values["batch_size"],
            default_config_values["condition_on_previous_text"],
            default_config_values["word_timestamps"],
        )

def save_config(
        device,
        cpu_threads,
        num_workers,
        language,
        whisper_model,
        compute_type,
        temperature,
        beam_size,
        batch_size,
        condition_on_previous_text,
        word_timestamps,
        gemini_model,
    ):
    try:
        config = {
            "device": device,
            "cpu_threads": cpu_threads,
            "num_workers": num_workers,
            "language": language,
            "whisper_model": whisper_model,
            "compute_type": compute_type,
            "temperature": temperature,
            "beam_size": beam_size,
            "batch_size": batch_size,
            "condition_on_previous_text": condition_on_previous_text,
            "word_timestamps": word_timestamps,
            "gemini_model": gemini_model,
        }
        with open("configurations/myconfig.yaml", "w") as file:
            yaml.dump(config, file)
    except Exception as e:
        logging.error(f"Error saving configuration: {e}")

def reset_fields():
    return (
        default_values['default_values']["input_file"],
        default_config_values["device"],
        default_config_values["cpu_threads"],
        default_config_values["num_workers"],
        default_config_values["language"],
        default_config_values["whisper_model"],
        default_config_values["compute_type"],
        default_config_values["temperature"],
        default_config_values["beam_size"],
        default_config_values["batch_size"],
        default_config_values["condition_on_previous_text"],
        default_values['default_values']["output_text"],
        default_values['default_values']["download_output"],
        default_config_values["word_timestamps"],
        default_config_values["gemini_model"],
        default_values['gemini']["user_query"],
        default_values['gemini']["gemini_response"],
    )

# Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("# 🎤 Audio/Video Transcription using Whisper Model")

    file_input = gr.File(label="Upload an audio or video file")
    
    try:
        with gr.Row():
            gr.Markdown("## Configurations")
        with gr.Row():
            with gr.Accordion(label="Explanation", open=False):
                gr.Markdown(default_values['explanation'])

        load_configuration = gr.File(label="Load Configuration File")
        with gr.Row():
            device = gr.Dropdown(choices=default_values['configurations']['devices'], value=default_config_values["device"], label="Device")
            cpu_threads = gr.Slider(minimum=default_values['configurations']['cpu_threads']['min'], value=default_config_values["cpu_threads"], step=1, label="CPU Threads")
            num_workers = gr.Slider(minimum=default_values['configurations']['num_workers']['min'], value=default_config_values["num_workers"], step=1, label="Number of Workers")
        with gr.Row():
            language = gr.Dropdown(choices=default_values['configurations']['languages'], value=default_config_values["language"], label="Language")
            whisper_model = gr.Dropdown(choices=default_values['configurations']['models'], value=default_config_values["whisper_model"], label="Whisper Model")
            compute_type = gr.Dropdown(choices=default_values['configurations']['compute_types'], value=default_config_values["compute_type"], label="Compute Type")
        with gr.Row():
            temperature = gr.Slider(minimum=default_values['configurations']['temperature']['min'], value=default_config_values["temperature"], step=0.1, label="Temperature")
            beam_size = gr.Slider(minimum=default_values['configurations']['beam_size']['min'], value=default_config_values["beam_size"], step=1, label="Beam Size")
            batch_size = gr.Slider(minimum=default_values['configurations']['batch_size']['min'], value=default_config_values["batch_size"], step=1, label="Batch Size")
        with gr.Row():
            condition_on_previous_text = gr.Checkbox(value=default_config_values["condition_on_previous_text"], label="Condition on Previous Text")
            word_timestamps = gr.Checkbox(value=default_config_values["word_timestamps"], label="Word-level timestamps")
            save_configurations = gr.Button("Save configurations", variant="secondary")
        
        with gr.Row():
            gr.Markdown("## Transcription")
        with gr.Accordion("Transcription"):
            output_text = gr.Markdown("*Your transcription will appear here.*", show_copy_button=True, container=True, line_breaks=True, max_height=400)

        download_output = gr.File(label="Download Transcript")
        transcribe_button = gr.Button("Transcribe", variant="secondary")

        if GEMINI_API_KEY:
            gr.Markdown("## Gemini Interaction")
            gemini_model = gr.Radio(choices=default_values['gemini']['models'], value=default_config_values["gemini_model"], label="Choose Gemini Model")
            user_query = gr.Textbox(label="Enter your query")
            with gr.Accordion("Gemini Response"):
                gemini_response = gr.Markdown("*Gemini response will appear here.*", show_copy_button=True, container=True, line_breaks=True, max_height=400)

            submit_query_button = gr.Button("Submit Query to Gemini", variant="secondary")

            try:
                submit_query_button.click(
                    query_gemini,
                    inputs=[user_query, output_text, gemini_model],
                    outputs=[gemini_response]
                )
            except Exception as e:
                logging.error(f"Error during Gemini query setup: {e}")
                    
        with gr.Row():
            reset_button = gr.Button("Reset fields", variant="secondary")
            clear_button = gr.Button("Clear temp files", variant="primary")
            close_and_clear_button = gr.Button("Clear temp files and quit", variant="stop")

        # Save configuration button functionality
        load_configuration.change(
            load_configuration_file,
            inputs=[load_configuration],
            outputs=[
            device,
            cpu_threads,
            num_workers,
            language,
            whisper_model,
            compute_type,
            temperature,
            beam_size,
            batch_size,
            condition_on_previous_text,
            word_timestamps,
            gemini_model,
            ]
        )

        # Save configuration button functionality
        save_configurations.click(
            save_config,
            inputs=[
                device,
                cpu_threads,
                num_workers,
                language,
                whisper_model,
                compute_type,
                temperature,
                beam_size,
                batch_size,
                condition_on_previous_text,
                word_timestamps,
            ],
            outputs=[]
        )

        # Reset button functionality
        reset_button.click(
            reset_fields,  # Call the reset function
            inputs=[],  # No inputs
            outputs=[
                file_input,
                device,
                cpu_threads,
                num_workers,
                language,
                whisper_model,
                compute_type,
                temperature,
                beam_size,
                batch_size,
                condition_on_previous_text,
                output_text,
                download_output,
                word_timestamps,
                gemini_model,
                user_query,
                gemini_response,
            ] 
        )

        try:
            transcribe_button.click(
                transcribe_file, 
                inputs=[
                    file_input, 
                    device, 
                    cpu_threads, 
                    num_workers, 
                    language, 
                    whisper_model, 
                    compute_type, 
                    temperature, 
                    beam_size, 
                    batch_size, 
                    condition_on_previous_text, 
                    word_timestamps
                ], 
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