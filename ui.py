import gradio as gr
import logging
import yaml
from transcription import transcribe_file, clear, clear_and_close
from config import load_default_values, load_default_config, get_gemini_api_key
from llms import query_gemini, list_ollama_models
from config import setup_logging

default_values = load_default_values()
default_config_values = load_default_config()

def load_config_file(file_path):
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
            config["gemini_model"]
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
            default_config_values["gemini_model"]
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
        with open("settings/mysettings.yaml", "w") as file:
            yaml.dump(config, file)
    except Exception as e:
        logging.error(f"Error saving settings: {e}")

def reset_fields():
    """Reset fields to default values."""
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

with gr.Blocks() as demo:
    setup_logging()
    gr.Markdown("# 🎤 Audio/Video Transcription using Whisper Model")

    file_input = gr.File(label="Upload an audio or video file")
    
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

    # Ensure UI elements exist for AI querying
    gemini_model = None
    user_query = None
    gemini_response = None

    # Provider selection: if Gemini API key present, allow Gemini + Ollama; otherwise only Ollama
    if get_gemini_api_key() is not None:
        provider = gr.Radio(choices=["Gemini", "Ollama"], value="Gemini", label="AI Provider")
    else:
        provider = gr.Radio(choices=["Ollama"], value="Ollama", label="AI Provider")

    # Gemini model selector (visible when using Gemini)
    gemini_model = gr.Radio(choices=default_values['gemini']['models'], value=default_config_values["gemini_model"], label="Choose Gemini Model", visible=True)

    # Ollama-specific model selector (populated from local Ollama)
    # allow_custom_value=True prevents Gradio warning when choices are empty at init
    ollama_model = gr.Dropdown(choices=[], value="", allow_custom_value=True, label="Ollama model (local)", visible=False)

    user_query = gr.Textbox(label="Enter your query")
    with gr.Accordion("AI Response"):
        gemini_response = gr.Markdown("*Response will appear here.*", show_copy_button=True, container=True, line_breaks=True, max_height=400)

    submit_query_button = gr.Button("Submit Query", variant="secondary")

    def _provider_change(p):
        # show Gemini model choices only when Gemini selected
        if str(p).lower().startswith('g'):
            return gr.update(visible=True), gr.update(visible=False, choices=[])
        # when Ollama selected, fetch models and show dropdown
        models = list_ollama_models() or ["(no models found)"]
        # pick first model if available
        value = models[0] if models and models[0] != "(no models found)" else ""
        return gr.update(visible=False), gr.update(visible=True, choices=models, value=value)

    provider.change(fn=_provider_change, inputs=[provider], outputs=[gemini_model, ollama_model])

    submit_query_button.click(
        fn=query_gemini,
        inputs=[user_query, output_text, gemini_model, provider, ollama_model],
        outputs=[gemini_response]
    )
    folder_state = gr.State(None) # Used to clear temp files

    with gr.Row():
        reset_button = gr.Button("Reset fields", variant="secondary")
        clear_button = gr.Button("Clear temp files", variant="primary")
        close_and_clear_button = gr.Button("Clear temp files and quit", variant="stop")

    load_configuration.change(
        fn=load_config_file,
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

    save_configurations.click(
        fn=save_config,
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
            gemini_model,
        ],
        outputs=[]
    )

    reset_button.click(
        fn=reset_fields,
        inputs=[],
        outputs=[file_input, device, cpu_threads, num_workers, language, whisper_model, compute_type, temperature, beam_size, batch_size, condition_on_previous_text, output_text, download_output, word_timestamps, gemini_model, user_query, gemini_response]
    )

    def transcribe_wrapper(file, device, cpu_threads, num_workers, language, whisper_model, compute_type, temperature, beam_size, batch_size, condition_on_previous_text, word_timestamps):
        transcription, output_path, folder_path = transcribe_file(
            file, device, cpu_threads, num_workers, language,
            whisper_model, compute_type, temperature, beam_size,
            batch_size, condition_on_previous_text, word_timestamps
        )
        return transcription, output_path, folder_path

    transcribe_button.click(
        fn=transcribe_wrapper,
        inputs=[file_input, device, cpu_threads, num_workers, language, whisper_model, compute_type, temperature, beam_size, batch_size, condition_on_previous_text, word_timestamps],
        outputs=[output_text, download_output, folder_state]
    )

    clear_button.click(
        fn=clear,
        inputs=[folder_state],
        outputs=[]
    )

    close_and_clear_button.click(
        fn=clear_and_close,
        inputs=[folder_state],
        outputs=[file_input, output_text]
    )