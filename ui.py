import logging
import os
import signal
import yaml
from security_utils import (
    SecurityError,
    cleanup_temp_storage,
    configure_gradio_temp_dir,
    validate_controlled_transcript_path,
    validate_local_config_path,
    validate_local_media_path,
)

configure_gradio_temp_dir()
import gradio as gr  # noqa: E402
from transcription import transcribe_file  # noqa: E402
from config import load_default_values, load_default_config, get_gemini_api_key, get_translation as _  # noqa: E402
from llms import query_gemini, list_ollama_models, list_lmstudio_models  # noqa: E402
from config import setup_logging  # noqa: E402

default_values = load_default_values()
NO_MODELS_FOUND = "No models found"
default_config_values = load_default_config()


def _default_config_tuple():
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
        default_config_values["gemini_model"],
    )


def load_config_file(file_path):
    try:
        if not file_path:
            return _default_config_tuple()

        config_path = validate_local_config_path(file_path)
        with open(config_path, "r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file) or {}
        if not isinstance(config, dict):
            raise ValueError("Configuration file must contain a mapping.")
        return (
            config.get("device", default_config_values["device"]),
            config.get("cpu_threads", default_config_values["cpu_threads"]),
            config.get("num_workers", default_config_values["num_workers"]),
            config.get("language", default_config_values["language"]),
            config.get("whisper_model", default_config_values["whisper_model"]),
            config.get("compute_type", default_config_values["compute_type"]),
            config.get("temperature", default_config_values["temperature"]),
            config.get("beam_size", default_config_values["beam_size"]),
            config.get("batch_size", default_config_values["batch_size"]),
            config.get(
                "condition_on_previous_text",
                default_config_values["condition_on_previous_text"],
            ),
            config.get("word_timestamps", default_config_values["word_timestamps"]),
            config.get("gemini_model", default_config_values["gemini_model"]),
        )
    except SecurityError as e:
        logging.warning("Rejected configuration path: %s", e)
        return _default_config_tuple()
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        return _default_config_tuple()

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
        with open("settings/default.yaml", "w") as file:
            yaml.dump(config, file)
    except Exception as e:
        logging.error(f"Error saving settings: {e}")

def reset_fields():
    """Reset fields to default values."""
    return (
        None,
        None,
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
        _("transcription_placeholder"),
        default_values['default_values']["download_output"],
        default_config_values["word_timestamps"],
        default_config_values["gemini_model"],
        "",
        _("response_placeholder"),
        gr.update(visible=False), # save_transcript_button
        gr.update(visible=False), # submit_query_button
    )


def preset_query_summary():
    return _("preset_summary_val")


def preset_query_todo():
    return _("preset_todo_val")


def notify_copy():
    gr.Info(_("text_copied"))


def browse_local_media_file():
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected_paths = filedialog.askopenfilenames(
            title=_("select_media_title"),
            filetypes=[
                (_("media_files_filter"), "*.avi *.flac *.m4a *.mkv *.mov *.mp3 *.mp4 *.ogg *.opus *.wav *.webm"),
                (_("all_files_filter"), "*.*"),
            ],
            parent=root,
        )
        root.destroy()
        if selected_paths:
            return "\n".join(selected_paths)
        return gr.update()
    except Exception as e:
        logging.error(f"Error selecting media file: {e}")
        gr.Error(_("error_selecting_media").format(str(e)))
        return gr.update()


def browse_local_config_file():
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected_path = filedialog.askopenfilename(
            title=_("select_config_title"),
            filetypes=[
                (_("yaml_files_filter"), "*.yaml *.yml"),
                (_("all_files_filter"), "*.*"),
            ],
            parent=root,
        )
        root.destroy()
        return selected_path or gr.update()
    except Exception as e:
        logging.error(f"Error selecting configuration file: {e}")
        gr.Error(_("error_selecting_config").format(str(e)))
        return gr.update()


def quit_app():
    try:
        logging.info(_("quitting_app"))
        cleanup_temp_storage()
        os.kill(os.getpid(), signal.SIGINT)
    except Exception as e:
        logging.error(f"Error quitting application: {e}")
        raise


custom_css = """
.scrollable-markdown {
    max-height: 400px !important;
    overflow-y: auto !important;
}
.scrollable-markdown * {
    overflow: visible !important;
    max-height: none !important;
}
* {
    user-select: text !important;
    -webkit-user-select: text !important;
    -ms-user-select: text !important;
    -moz-user-select: text !important;
}
"""

with gr.Blocks(title="Whisper Utility") as demo:
    setup_logging()
    gr.Markdown(_("title"))

    with gr.Row():
        file_path_input = gr.Textbox(
            label=_("media_file_path_label"),
            placeholder=_("media_file_path_placeholder"),
            lines=3,
        )
    browse_file_button = gr.Button(_("browse"), variant="secondary")
    
    with gr.Row():
        gr.Markdown(_("configurations_title"))
    with gr.Row():
        with gr.Accordion(label=_("explanation_accordion"), open=False):
            gr.Markdown(_("explanation_text"))

    with gr.Row():
        config_path_input = gr.Textbox(
            label=_("config_file_path_label"),
            placeholder=_("config_file_path_placeholder"),
            lines=1,
        )
    browse_config_button = gr.Button(_("browse"), variant="secondary")
    with gr.Row():
        device = gr.Dropdown(choices=default_values['configurations']['devices'], value=default_config_values["device"], label=_("device_label"))
        cpu_threads = gr.Slider(minimum=default_values['configurations']['cpu_threads']['min'], value=default_config_values["cpu_threads"], step=1, label=_("cpu_threads_label"))
        num_workers = gr.Slider(minimum=default_values['configurations']['num_workers']['min'], value=default_config_values["num_workers"], step=1, label=_("num_workers_label"))
    with gr.Row():
        language = gr.Dropdown(choices=default_values['configurations']['languages'], value=default_config_values["language"], label=_("language_label"))
        whisper_model = gr.Dropdown(choices=default_values['configurations']['models'], value=default_config_values["whisper_model"], label=_("whisper_model_label"))
        compute_type = gr.Dropdown(choices=default_values['configurations']['compute_types'], value=default_config_values["compute_type"], label=_("compute_type_label"))
    with gr.Row():
        temperature = gr.Slider(minimum=default_values['configurations']['temperature']['min'], value=default_config_values["temperature"], step=0.1, label=_("temperature_label"))
        beam_size = gr.Slider(minimum=default_values['configurations']['beam_size']['min'], value=default_config_values["beam_size"], step=1, label=_("beam_size_label"))
        batch_size = gr.Slider(minimum=default_values['configurations']['batch_size']['min'], value=default_config_values["batch_size"], step=1, label=_("batch_size_label"))
    with gr.Row():
        condition_on_previous_text = gr.Checkbox(value=default_config_values["condition_on_previous_text"], label=_("condition_on_previous_text_label"))
        word_timestamps = gr.Checkbox(value=default_config_values["word_timestamps"], label=_("word_timestamps_label"))
        save_configurations = gr.Button(_("save_configurations"), variant="secondary")
    
    with gr.Row():
        gr.Markdown(_("transcription_title"))
    with gr.Accordion(_("transcription_accordion")):
        copy_transcription_button = gr.Button(_("copy_transcription"), variant="secondary", size="sm")
        output_text = gr.Markdown(_("transcription_placeholder"), container=True, line_breaks=True, elem_classes="scrollable-markdown")

    transcript_file_path = gr.State()
    save_transcript_button = gr.Button(_("save_transcript_as"), variant="primary", visible=False)
    transcribe_button = gr.Button(_("transcribe_btn"), variant="secondary")

    # Ensure UI elements exist for AI querying
    gemini_model = None
    user_query = None
    gemini_response = None

    has_gemini = get_gemini_api_key() is not None

    with gr.Accordion(_("ai_provider_accordion"), open=True):
        # Provider selection: if Gemini API key present, allow all providers; otherwise only local providers
        if has_gemini:
            provider = gr.Radio(choices=["Gemini", "Ollama", "LM Studio"], value="Gemini", label=_("provider_label"))
        else:
            provider = gr.Radio(choices=["Ollama", "LM Studio"], value="Ollama", label=_("provider_label"))

        # Gemini model selector (only meaningful when using Gemini)
        gemini_model = gr.Radio(
            choices=default_values['gemini']['models'],
            value=default_config_values["gemini_model"],
            label=_("choose_gemini_model"),
            visible=has_gemini,
        )

        # Ollama-specific model selector (populated from local Ollama)
        # allow_custom_value=True prevents Gradio warning when choices are empty at init
        try:
            _initial_ollama_models = list_ollama_models() if not has_gemini else []
        except Exception:
            _initial_ollama_models = []
        _initial_ollama_value = _initial_ollama_models[0] if _initial_ollama_models else ""

        ollama_model = gr.Dropdown(
            choices=_initial_ollama_models,
            value=_initial_ollama_value,
            allow_custom_value=True,
            label=_("choose_ollama_model"),
            visible=not has_gemini,
        )

        try:
            _initial_lmstudio_models = []
        except Exception:
            _initial_lmstudio_models = []
        _initial_lmstudio_value = _initial_lmstudio_models[0] if _initial_lmstudio_models else ""

        lmstudio_model = gr.Dropdown(
            choices=_initial_lmstudio_models,
            value=_initial_lmstudio_value,
            allow_custom_value=True,
            label=_("choose_lmstudio_model"),
            visible=False,
        )

        with gr.Row():
            preset_summary_button = gr.Button(_("preset_summary"), variant="secondary")
            preset_todo_button = gr.Button(_("preset_todo"), variant="secondary")

        user_query = gr.Textbox(label=_("enter_query_label"))

        submit_query_button = gr.Button(_("submit_query_btn"), variant="primary", visible=False)

    preset_summary_button.click(
        fn=preset_query_summary,
        inputs=[],
        outputs=[user_query],
    )

    preset_todo_button.click(
        fn=preset_query_todo,
        inputs=[],
        outputs=[user_query],
    )

    with gr.Accordion(_("ai_response_accordion")):
        copy_response_button = gr.Button(_("copy_response"), variant="secondary", size="sm")
        gemini_response = gr.Markdown(_("response_placeholder"), container=True, line_breaks=True, elem_classes="scrollable-markdown")

    browse_file_button.click(
        fn=browse_local_media_file,
        inputs=[],
        outputs=[file_path_input],
    )

    browse_config_button.click(
        fn=browse_local_config_file,
        inputs=[],
        outputs=[config_path_input],
    )

    def _provider_change(p):
        # show Gemini model choices only when Gemini selected
        if str(p).lower().startswith('g'):
            return (
                gr.update(visible=True),
                gr.update(visible=False, choices=[], value=""),
                gr.update(visible=False, choices=[], value=""),
            )
        # when Ollama selected, fetch models and show dropdown
        if str(p).lower().startswith('olla'):
            models = list_ollama_models() or [NO_MODELS_FOUND]
            value = models[0] if models and models[0] != NO_MODELS_FOUND else ""
            return (
                gr.update(visible=False),
                gr.update(visible=True, choices=models, value=value),
                gr.update(visible=False, choices=[], value=""),
            )

        # when LM Studio selected, fetch models and show dropdown
        lm_models = list_lmstudio_models() or [NO_MODELS_FOUND]
        lm_value = lm_models[0] if lm_models and lm_models[0] != NO_MODELS_FOUND else ""
        return (
            gr.update(visible=False),
            gr.update(visible=False, choices=[], value=""),
            gr.update(visible=True, choices=lm_models, value=lm_value),
        )

    provider.change(fn=_provider_change, inputs=[provider], outputs=[gemini_model, ollama_model, lmstudio_model])

    submit_query_button.click(
        fn=query_gemini,
        inputs=[user_query, output_text, gemini_model, provider, ollama_model, lmstudio_model],
        outputs=[gemini_response],
        stream_every=0.05,  # flush UI at most every 50 ms
    )
    with gr.Row():
        reset_button = gr.Button(_("reset_fields"), variant="secondary")
        quit_button = gr.Button(_("quit"), variant="stop")

    config_path_input.change(
        fn=load_config_file,
        inputs=[config_path_input],
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
        outputs=[file_path_input, config_path_input, device, cpu_threads, num_workers, language, whisper_model, compute_type, temperature, beam_size, batch_size, condition_on_previous_text, output_text, transcript_file_path, word_timestamps, gemini_model, user_query, gemini_response, save_transcript_button, submit_query_button]
    )

    def transcribe_wrapper(file_paths_text, device, cpu_threads, num_workers, language, whisper_model, compute_type, temperature, beam_size, batch_size, condition_on_previous_text, word_timestamps):
        if not file_paths_text or not file_paths_text.strip():
            yield _("invalid_file").format("No file selected"), None, gr.update(visible=False), gr.update(visible=False)
            return

        raw_paths = [p.strip() for p in file_paths_text.strip().split('\n') if p.strip()]
        
        valid_paths = []
        for path in raw_paths:
            try:
                valid_paths.append(str(validate_local_media_path(path)))
            except SecurityError as e:
                logging.warning("Rejected media path: %s", e)
                yield _("invalid_file").format(f"{path}: {e}"), None, gr.update(visible=False), gr.update(visible=False)
                return

        for transcription, output_path, _folder_path in transcribe_file(
            valid_paths, device, cpu_threads, num_workers, language,
            whisper_model, compute_type, temperature, beam_size,
            batch_size, condition_on_previous_text, word_timestamps
        ):
            if output_path:
                 yield transcription, output_path, gr.update(visible=True), gr.update(visible=True)
            else:
                 yield transcription, output_path, gr.update(visible=False), gr.update(visible=False)

    transcribe_button.click( # Updated outputs to use transcript_file_path and button visibility
        fn=transcribe_wrapper,
        inputs=[file_path_input, device, cpu_threads, num_workers, language, whisper_model, compute_type, temperature, beam_size, batch_size, condition_on_previous_text, word_timestamps],
        outputs=[output_text, transcript_file_path, save_transcript_button, submit_query_button],
        stream_every=0.1
    )

    quit_button.click(
        fn=quit_app,
        inputs=[],
        outputs=[]
    )

    def save_transcript_wrapper(file_path):
        if not file_path:
            gr.Warning(_("no_transcript_to_save"))
            return
        try:
            source_path = validate_controlled_transcript_path(file_path)
        except SecurityError as e:
            logging.warning("Rejected transcript save source: %s", e)
            gr.Warning(_("transcript_not_available"))
            return
        
        # Only import tkinter when needed to avoid issues if not installed or headless
        try:
            import tkinter as tk
            from tkinter import filedialog
            import shutil
            import os
            
            # Create a hidden root window
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            
            initial_file = os.path.basename(source_path)
            
            target_path = filedialog.asksaveasfilename(
                title=_("save_transcript_title"),
                initialfile=initial_file,
                defaultextension=".txt",
                filetypes=[(_("text_files_filter"), "*.txt"), (_("all_files_filter"), "*.*")],
                parent=root
            )
            
            root.destroy()
            
            if target_path:
                shutil.copy2(source_path, target_path)
                gr.Info(_("successfully_saved").format(target_path))
            else:
                gr.Info(_("save_cancelled"))
        except Exception as e:
            logging.error(f"Error saving file: {e}")
            gr.Error(_("error_saving_file").format(str(e)))

    save_transcript_button.click(
        fn=save_transcript_wrapper,
        inputs=[transcript_file_path], 
        outputs=[]
    )

    # JavaScript for copying text
    js_copy_text = "(text) => { navigator.clipboard.writeText(text); }"

    copy_transcription_button.click(
        fn=notify_copy,
        inputs=[],
        outputs=[]
    ).then(
        fn=None,
        inputs=[output_text],
        js=js_copy_text
    )

    copy_response_button.click(
        fn=notify_copy,
        inputs=[],
        outputs=[]
    ).then(
        fn=None,
        inputs=[gemini_response],
        js=js_copy_text
    )
