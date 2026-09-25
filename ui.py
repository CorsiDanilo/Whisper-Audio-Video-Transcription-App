import logging
import os
import signal
import yaml
from security_utils import (
    SecurityError,
    build_output_path_in_dir,
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
from llms import query_gemini, list_ollama_models, list_lmstudio_models, get_sorted_gemini_models  # noqa: E402
from config import setup_logging  # noqa: E402
from updater import check_for_updates, launch_installer_update, CURRENT_VERSION  # noqa: E402
from remote_transcription import (  # noqa: E402
    check_server_health,
    fetch_remote_models,
    fetch_remote_settings,
    switch_remote_model,
    update_remote_settings,
)

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
        ui_language="italian",
        transcription_backend="local",
        remote_server_url="http://192.168.1.32:8088",
        vad_threshold=0.5,
        silence_threshold=0.6,
        initial_prompt="",
    ):
    """Save configuration to both local settings/default.yaml and system AppData."""
    from config import get_app_config_dir
    try:
        backend_val = "remote" if (str(transcription_backend) == _("backend_remote") or str(transcription_backend) == "remote") else "local"
        config = {
            "ui_language": ui_language,
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
            "transcription_backend": backend_val,
            "remote_server_url": remote_server_url,
            "vad_threshold": float(vad_threshold) if vad_threshold is not None else 0.5,
            "silence_threshold": float(silence_threshold) if silence_threshold is not None else 0.6,
            "initial_prompt": str(initial_prompt or ""),
        }

        # 1. Write local copy
        os.makedirs("settings", exist_ok=True)
        with open("settings/default.yaml", "w", encoding="utf-8") as file:
            yaml.dump(config, file, sort_keys=False, allow_unicode=True)

        # 2. Write system AppData copy
        sys_settings_dir = os.path.join(get_app_config_dir(), "settings")
        os.makedirs(sys_settings_dir, exist_ok=True)
        sys_path = os.path.join(sys_settings_dir, "default.yaml")
        existing: dict = {}
        if os.path.exists(sys_path):
            try:
                with open(sys_path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
                    if isinstance(loaded, dict):
                        existing = loaded
            except Exception:
                pass
        existing.update(config)
        with open(sys_path, "w", encoding="utf-8") as file:
            yaml.dump(existing, file, sort_keys=False, allow_unicode=True)

        if backend_val == "remote" and remote_server_url:
            rem_payload = {
                "WHISPER_LANGUAGE": language,
                "WHISPER_COMPUTE_TYPE": compute_type,
                "VAD_THRESHOLD": float(vad_threshold) if vad_threshold is not None else 0.5,
                "SILENCE_DURATION_THRESHOLD": float(silence_threshold) if silence_threshold is not None else 0.6,
                "INITIAL_PROMPT": str(initial_prompt or ""),
            }
            ok_rem, rem_msg = update_remote_settings(remote_server_url, rem_payload)
            if ok_rem:
                gr.Info(_("remote_settings_saved"))
                return
            else:
                gr.Warning(f"Avviso salvataggio NAS: {rem_msg}")

        gr.Info(_("settings_saved_toast") if _("settings_saved_toast") != "settings_saved_toast" else "✅ Settings saved successfully!")
    except Exception as e:
        logging.error(f"Error saving settings: {e}")
        gr.Warning(f"Error saving settings: {e}")
    except Exception as e:
        logging.error(f"Error saving settings: {e}")
        gr.Warning(f"Error saving settings: {e}")

def reset_fields():
    """Reset fields to default values."""
    gemini_api_key = get_gemini_api_key()
    has_gemini = bool(gemini_api_key)
    default_provider = "Google" if has_gemini else "Ollama"
    default_brand = "Gemini"
    default_gemini = default_config_values.get("gemini_model", "gemini-flash-latest")

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
        default_gemini,
        "",
        _("response_placeholder"),
        gr.update(visible=False), # save_transcript_button
        gr.update(visible=False), # submit_query_button
        ".txt",                   # output_format
        _("status_waiting"),      # status_badge
        default_provider,         # provider
        gr.update(value=default_brand, visible=has_gemini), # google_brand_radio
    )



def preset_query_summary():
    return _("preset_summary_val")


def preset_query_todo():
    return _("preset_todo_val")


def preset_query_fix():
    return _("preset_fix_val")


def notify_copy():
    gr.Info(_("text_copied"))


def browse_local_files(existing_paths=""):
    """Open a native file dialog to select files."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        files = filedialog.askopenfilenames(
            title=_("select_media_title"),
            filetypes=[
                (_("media_files_filter"), "*.avi *.flac *.m4a *.mkv *.mov *.mp3 *.mp4 *.ogg *.opus *.wav *.webm"),
                (_("all_files_filter"), "*.*"),
            ],
            parent=root,
        )
        root.destroy()

        if files:
            new_paths = "\n".join(list(files))
            existing = existing_paths.strip() if existing_paths else ""
            if existing:
                return f"{existing}\n{new_paths}"
            return new_paths
        return gr.update()
    except Exception as e:
        logging.error(f"Error selecting files: {e}")
        gr.Error(_("error_selecting_media").format(str(e)))
        return gr.update()

def browse_local_folders(existing_paths=""):
    """Open a native folder dialog and recursively get all files inside."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        import os

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        folder = filedialog.askdirectory(
            title=_("dialog_select_type_title"),
            parent=root,
        )
        root.destroy()

        if folder:
            SUPPORTED_EXTS = {".avi", ".flac", ".m4a", ".mkv", ".mov", ".mp3", ".mp4", ".ogg", ".opus", ".wav", ".webm"}
            expanded_paths = []
            for root_dir, dirs, files in os.walk(folder):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_EXTS:
                        expanded_paths.append(os.path.join(root_dir, f))
            
            if expanded_paths:
                new_paths = "\n".join(expanded_paths)
                existing = existing_paths.strip() if existing_paths else ""
                if existing:
                    return f"{existing}\n{new_paths}"
                return new_paths
        return gr.update()
    except Exception as e:
        logging.error(f"Error selecting folders: {e}")
        gr.Error(_("error_selecting_media").format(str(e)))
        return gr.update()


GEMINI_TEMPLATE = (
    "# Configuration file for Google Gemini API Key\n"
    "# Replace YOUR_GEMINI_API_KEY_HERE with your Google Gemini API key\n"
    'gemini_api_key: "YOUR_GEMINI_API_KEY_HERE"\n'
)


def read_config_file_text(file_path: str) -> str:
    """Read config file text, creating it with default template if missing."""
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        template = GEMINI_TEMPLATE if "gemini" in file_path else ""
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(template)
        return template
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error reading config file {abs_path}: {e}")
        return f"# Error reading file: {e}"


def write_config_file_text(file_path: str, content: str) -> None:
    """Save content to configuration file."""
    abs_path = os.path.abspath(file_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(content)
    gr.Info(_("file_saved_toast"))


def open_file_in_notepad(file_path: str) -> None:
    """Open config file directly in Notepad on Windows or system text editor."""
    import subprocess
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        read_config_file_text(file_path)
    try:
        if sys.platform == "win32":
            subprocess.Popen(["notepad.exe", abs_path])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-e", abs_path])
        else:
            subprocess.Popen(["xdg-open", abs_path])
    except Exception as e:
        logging.error(f"Error opening editor for {abs_path}: {e}")
        gr.Error(f"Error launching editor: {e}")


def browse_output_folder(file_paths_text="", current_override=""):
    """Open a folder dialog to choose the output directory.
    Default points to the common root of the selected files."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        from pathlib import Path

        default_dir = ""
        if current_override and os.path.isdir(current_override):
            default_dir = current_override
        elif file_paths_text and file_paths_text.strip():
            paths = [p.strip() for p in file_paths_text.strip().split("\n") if p.strip()]
            if paths:
                try:
                    common = os.path.commonpath(paths)
                    default_dir = common if os.path.isdir(common) else str(Path(common).parent)
                except ValueError:
                    default_dir = str(Path(paths[0]).parent)

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        folder = filedialog.askdirectory(
            title=_("dialog_select_output_folder_title"),
            initialdir=default_dir or os.path.expanduser("~"),
            parent=root,
        )
        root.destroy()

        if folder:
            return folder
        return gr.update()
    except Exception as e:
        logging.error(f"Error selecting output folder: {e}")
        return gr.update()


def _compute_output_dir(expanded_paths, output_dir_override=""):
    """Compute the timestamped output directory and common root.

    Returns:
        (common_root: Path, output_dir: Path, timestamp_str: str)
    """
    from pathlib import Path
    import datetime

    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"{timestamp_str}_transcription"

    if output_dir_override and os.path.isdir(output_dir_override):
        base = Path(output_dir_override)
    else:
        try:
            common = os.path.commonpath(expanded_paths)
            base = Path(common) if os.path.isdir(common) else Path(common).parent
        except ValueError:
            base = Path(expanded_paths[0]).parent

    output_dir = base / folder_name
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        common_root = Path(os.path.commonpath(expanded_paths))
        if not common_root.is_dir():
            common_root = common_root.parent
    except ValueError:
        common_root = Path(expanded_paths[0]).parent

    return common_root, output_dir, timestamp_str


def quit_app():
    try:
        logging.info(_("quitting_app"))
        cleanup_temp_storage()
        os.kill(os.getpid(), signal.SIGINT)
    except Exception as e:
        logging.error(f"Error quitting application: {e}")
        raise


custom_css = """
#config-screen {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100% !important;
    height: 100% !important;
    z-index: 99999 !important;
    background-color: var(--background-fill-primary) !important;
    padding: 40px !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    box-sizing: border-box !important;
}
#config-screen > * {
    flex-shrink: 0 !important;
}
.scrollable-markdown {
    max-height: 400px !important;
    overflow-y: auto !important;
    position: relative !important;
}
.scrollable-markdown * {
    overflow: visible !important;
    max-height: none !important;
}
.scrollable-markdown .progress-level,
.scrollable-markdown .meta-text {
    display: none !important;
}
* {
    user-select: text !important;
    -webkit-user-select: text !important;
    -ms-user-select: text !important;
    -moz-user-select: text !important;
}
"""

js_head_script = """
<script>
function playCompletionSound() {
    try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        const ctx = new AudioCtx();
        const now = ctx.currentTime;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(523.25, now);
        osc.frequency.exponentialRampToValueAtTime(659.25, now + 0.12);
        osc.frequency.exponentialRampToValueAtTime(783.99, now + 0.24);
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.5);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.5);
    } catch (e) {
        console.error("Audio chime error:", e);
    }
}
</script>
"""

def set_status_completed():
    gr.Info(_("toast_completed_whisper"))
    return _("status_completed")

with gr.Blocks(title="Whisper Utility", head=js_head_script) as demo:
    setup_logging()
    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown(_("title"))
            status_badge = gr.Markdown(_("status_waiting"), elem_id="status_badge")
    with gr.Tabs():
        with gr.Tab(_("tab_transcription")):
            _init_is_remote = (default_config_values.get("transcription_backend", "local") == "remote")

            with gr.Row():
                transcription_backend = gr.Radio(
                    choices=[_("backend_local"), _("backend_remote")],
                    value=_("backend_remote") if _init_is_remote else _("backend_local"),
                    label=_("backend_label"),
                )
            with gr.Row(visible=_init_is_remote) as remote_server_box:
                remote_server_url = gr.Textbox(
                    label=_("remote_url_label"),
                    value=default_config_values.get("remote_server_url", "http://192.168.1.32:8088"),
                    scale=2,
                )
                remote_model = gr.Dropdown(
                    label=_("remote_model_label"),
                    choices=[],
                    value="",
                    scale=2,
                    allow_custom_value=True,
                    visible=False,
                )
                remote_status = gr.Textbox(
                    label=_("remote_status_label"),
                    value=_("remote_status_waiting"),
                    interactive=False,
                    scale=2,
                )
            test_remote_btn = gr.Button(_("test_connection_btn"), variant="secondary", scale=1, visible=_init_is_remote)

            with gr.Accordion(_("configurations_accordion"), open=False) as config_accordion:
                with gr.Accordion(label=_("explanation_accordion"), open=False):
                    explanation_md = gr.Markdown(
                        _("explanation_remote_text") if _init_is_remote else _("explanation_text")
                    )

                # Local Whisper hardware configurations (visible ONLY when backend is local)
                with gr.Column(visible=not _init_is_remote) as local_only_box:
                    with gr.Row():
                        device = gr.Dropdown(choices=default_values['configurations']['devices'], value=default_config_values["device"], label=_("device_label"))
                        cpu_threads = gr.Slider(
                            minimum=1,
                            maximum=32,
                            value=default_config_values["cpu_threads"],
                            step=1,
                            label=_("cpu_threads_label"),
                        )
                        num_workers = gr.Slider(minimum=default_values['configurations']['num_workers']['min'], value=default_config_values["num_workers"], step=1, label=_("num_workers_label"))
                    with gr.Row():
                        batch_size = gr.Slider(minimum=default_values['configurations']['batch_size']['min'], value=default_config_values["batch_size"], step=1, label=_("batch_size_label"))
                        beam_size = gr.Slider(
                            minimum=default_values['configurations']['beam_size']['min'],
                            value=default_config_values["beam_size"],
                            step=1,
                            label=_("beam_size_label"),
                        )
                        temperature = gr.Slider(minimum=default_values['configurations']['temperature']['min'], value=default_config_values["temperature"], step=0.1, label=_("temperature_label"))
                    with gr.Row():
                        condition_on_previous_text = gr.Checkbox(value=default_config_values["condition_on_previous_text"], label=_("condition_on_previous_text_label"))
                        word_timestamps = gr.Checkbox(value=default_config_values["word_timestamps"], label=_("word_timestamps_label"))

                # Core configurations (model, compute_type, language - present on both local and server)
                _model_choices = _init_remote_choices if (_init_is_remote and _init_remote_choices) else default_values['configurations']['models']
                _model_val = _init_remote_active if (_init_is_remote and _init_remote_active) else default_config_values["whisper_model"]
                _compute_choices = ["int8", "float16", "auto"] if _init_is_remote else default_values['configurations']['compute_types']
                _compute_val = _init_remote_compute if _init_is_remote else default_config_values["compute_type"]

                with gr.Row():
                    whisper_model = gr.Dropdown(
                        choices=_model_choices,
                        value=_model_val,
                        label=_("whisper_model_label"),
                        scale=2,
                        allow_custom_value=True,
                    )
                    compute_type = gr.Dropdown(
                        choices=_compute_choices,
                        value=_compute_val,
                        label=_("compute_type_label"),
                        scale=1,
                        allow_custom_value=True,
                    )
                    _available_languages = list(default_values['configurations']['languages'])
                    if "auto" not in _available_languages:
                        _available_languages = ["auto"] + _available_languages
                    language = gr.Dropdown(
                        choices=_available_languages,
                        value=default_config_values["language"],
                        label=_("language_label"),
                        scale=1,
                        allow_custom_value=True,
                    )

                # Remote-only configurations (VAD, silence timeout, initial prompt - returned by server)
                with gr.Column(visible=_init_is_remote) as remote_only_box:
                    with gr.Row():
                        vad_threshold = gr.Slider(
                            minimum=0.1,
                            maximum=0.95,
                            value=float(default_config_values.get("vad_threshold", 0.5)),
                            step=0.05,
                            label=_("vad_threshold_label"),
                        )
                        silence_threshold = gr.Slider(
                            minimum=0.2,
                            maximum=3.0,
                            value=float(default_config_values.get("silence_threshold", 0.6)),
                            step=0.1,
                            label=_("silence_threshold_label"),
                        )
                    with gr.Row():
                        initial_prompt = gr.Textbox(
                            label=_("initial_prompt_label"),
                            placeholder=_("initial_prompt_placeholder"),
                            value=str(default_config_values.get("initial_prompt", "")),
                            lines=2,
                        )

                with gr.Row():
                    save_configurations = gr.Button(_("save_configurations"), variant="secondary", visible=not _init_is_remote)

            config_path_input = gr.State("settings/default.yaml")

            with gr.Row():
                file_path_input = gr.Textbox(
                    label=_("media_file_path_label"),
                    placeholder=_("media_file_path_placeholder"),
                    lines=3,
                )
            with gr.Row():
                browse_files_btn = gr.Button(_("dialog_btn_files"), variant="secondary")
                browse_folders_btn = gr.Button(_("dialog_btn_folder"), variant="secondary")

            with gr.Row():
                output_dir_display = gr.Textbox(
                    label=_("output_dir_label"),
                    placeholder=_("output_dir_placeholder"),
                    lines=1,
                    interactive=True,
                    scale=4,
                )
                output_format = gr.Radio(choices=[".txt", ".md"], value=".txt", label=_("output_format_label"), scale=1)
            with gr.Row():
                choose_output_dir_btn = gr.Button(_("choose_output_dir_btn"), variant="secondary")

            with gr.Row():
                gr.Markdown(_("transcription_title"))
            with gr.Accordion(_("transcription_accordion")):
                copy_transcription_button = gr.Button(_("copy_transcription"), variant="secondary", size="sm")
                output_text = gr.Markdown(_("transcription_placeholder"), container=True, line_breaks=True, elem_classes="scrollable-markdown")

            transcript_file_path = gr.State()
            save_transcript_button = gr.Button(_("save_transcript_as"), variant="primary", visible=False)
            with gr.Row():
                transcribe_button = gr.Button(_("transcribe_btn"), variant="secondary")
                stop_transcribe_btn = gr.Button(_("stop_btn"), variant="stop", visible=False)

            # Ensure UI elements exist for AI querying
            gemini_model = None
            user_query = None
            gemini_response = None

            gemini_api_key = get_gemini_api_key()
            gemini_models = get_sorted_gemini_models(gemini_api_key)
            has_gemini = len(gemini_models) > 0

            with gr.Accordion(_("ai_provider_accordion"), open=True):
                # Provider selection: if Gemini API key and models are present, allow all providers; otherwise only local providers
                provider_choices = ["Google", "Ollama", "LM Studio"] if has_gemini else ["Ollama", "LM Studio"]
                provider = gr.Radio(
                    choices=provider_choices,
                    value="Google" if has_gemini else "Ollama",
                    label=_("provider_label")
                )

                google_brand_radio = gr.Radio(
                    choices=["Gemini", "Gemma"],
                    value="Gemini",
                    label=_("model_family_label"),
                    visible=has_gemini,
                )


                initial_filtered_models = [m for m in gemini_models if "gemini" in m.lower()]
                if not initial_filtered_models and gemini_models:
                    initial_filtered_models = [m for m in gemini_models if "gemma" in m.lower()]

                default_val = None
                for m in initial_filtered_models:
                    if "gemini-flash-latest" in m.lower():
                        default_val = m
                        break
                if not default_val and initial_filtered_models:
                    default_val = initial_filtered_models[0]

                # Gemini model selector (only meaningful when using Gemini/Google)
                gemini_model = gr.Dropdown(
                    choices=initial_filtered_models,
                    value=default_val,
                    allow_custom_value=True,
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

                # Response language selector for AI assistant
                response_language = gr.Radio(
                    choices=["Italiano", "English"],
                    value="Italiano",
                    label=_("response_language_label"),
                )

                with gr.Row():
                    preset_summary_button = gr.Button(_("preset_summary"), variant="secondary")
                    preset_todo_button = gr.Button(_("preset_todo"), variant="secondary")
                    preset_fix_button = gr.Button(_("preset_fix"), variant="secondary")

                fix_text_mode = gr.State(False)
                user_query = gr.Textbox(label=_("enter_query_label"))

                with gr.Row():
                    submit_query_button = gr.Button(_("submit_query_btn"), variant="primary", visible=False)
                    stop_query_btn = gr.Button(_("stop_btn"), variant="stop", visible=False)

            preset_summary_button.click(
                fn=preset_query_summary,
                inputs=[],
                outputs=[user_query],
            ).then(fn=lambda: False, inputs=[], outputs=[fix_text_mode])

            preset_todo_button.click(
                fn=preset_query_todo,
                inputs=[],
                outputs=[user_query],
            ).then(fn=lambda: False, inputs=[], outputs=[fix_text_mode])

            preset_fix_button.click(
                fn=preset_query_fix,
                inputs=[],
                outputs=[user_query],
            ).then(fn=lambda: True, inputs=[], outputs=[fix_text_mode])

            with gr.Accordion(_("ai_response_accordion")):
                copy_response_button = gr.Button(_("copy_response"), variant="secondary", size="sm")
                gemini_response = gr.Markdown(_("response_placeholder"), container=True, line_breaks=True, elem_classes="scrollable-markdown")

            with gr.Row():
                reset_button = gr.Button(_("reset_fields"), variant="secondary")


        with gr.Tab(_("tab_settings")):
            with gr.Row():
                gr.Markdown(_("settings_interface_title"))
            with gr.Row():
                _ui_lang_choices = ["italian", "english"]
                _ui_lang_default = default_config_values.get("ui_language", "italian")
                ui_language_dropdown = gr.Dropdown(
                    choices=_ui_lang_choices,
                    value=_ui_lang_default if _ui_lang_default in _ui_lang_choices else "italian",
                    label=_("ui_language_label") if _("ui_language_label") != "ui_language_label" else "🌐 Interface Language (requires restart)",
                    scale=3,
                )
            save_settings_btn = gr.Button(_("save_configurations"), variant="secondary", scale=1)

            # ── Model Manager ─────────────────────────────────────────────────────────
            with gr.Accordion(_("model_manager_accordion"), open=False):
                gr.Markdown(
                    "Manage downloaded Whisper models in the Hugging Face cache. "
                    "Disk sizes are shown for downloaded models. "
                    "**Deleting a model will remove it from disk — it can be re-downloaded anytime.**"
                )

                model_status_md = gr.Markdown(_("model_manager_status_initial"))
                model_download_status = gr.Textbox(
                    label="Download status",
                    interactive=False,
                    lines=2,
                    visible=False,
                )

                with gr.Row():
                    model_select = gr.Dropdown(
                        choices=["tiny", "tiny.en", "base", "base.en", "small", "small.en",
                                 "medium", "medium.en", "large-v1", "large-v2", "large-v3",
                                 "large-v3-turbo", "turbo", "distil-large-v2", "distil-large-v3",
                                 "distil-large-v3.5", "distil-medium.en", "distil-small.en"],
                        value="large-v3",
                        label="Select model",
                        scale=3,
                    )
                    model_device_select = gr.Dropdown(
                        choices=["cpu", "cuda"],
                        value=default_config_values.get("device", "cpu"),
                        label="Download device",
                        scale=1,
                    )

                with gr.Row():
                    refresh_models_btn = gr.Button(_("model_manager_refresh_btn"), variant="secondary", size="sm")
                    download_model_btn = gr.Button(_("model_manager_download_btn"), variant="primary", size="sm")
                    delete_model_btn = gr.Button(_("model_manager_delete_btn"), variant="stop", size="sm")

                def _format_model_table(statuses):
                    lines = ["| Model | Status | Size |", "|-------|--------|------|"]
                    for s in statuses:
                        icon = "🟢" if s["is_downloaded"] else "⚪"
                        size_str = f"{s['size_mb']:.0f} MB" if s["is_downloaded"] else "—"
                        lines.append(f"| `{s['name']}` | {icon} {'Downloaded' if s['is_downloaded'] else 'Not downloaded'} | {size_str} |")
                    return "\n".join(lines)

                def refresh_model_list():
                    from model_manager import list_whisper_models_status
                    statuses = list_whisper_models_status()
                    return _format_model_table(statuses)

                def do_download_model(model_name, device):
                    from model_manager import download_model
                    yield gr.update(visible=True, value=f"⏳ Starting download of '{model_name}'..."), gr.update()
                    messages = []
                    def _cb(msg):
                        messages.append(msg)
                    ok = download_model(model_name, device=device, compute_type="auto", progress_callback=_cb)
                    status_msg = f"✅ '{model_name}' downloaded successfully!" if ok else f"❌ Download failed for '{model_name}'."
                    table = refresh_model_list()
                    yield gr.update(visible=True, value="\n".join(messages) + "\n" + status_msg), table

                def do_delete_model(model_name):
                    from model_manager import delete_model_cache, list_whisper_models_status
                    ok = delete_model_cache(model_name)
                    msg = f"✅ Deleted '{model_name}' cache." if ok else f"❌ Failed to delete '{model_name}'."
                    statuses = list_whisper_models_status()
                    return _format_model_table(statuses), gr.update(visible=True, value=msg)

                refresh_models_btn.click(
                    fn=refresh_model_list,
                    inputs=[],
                    outputs=[model_status_md],
                )

                download_model_btn.click(
                    fn=do_download_model,
                    inputs=[model_select, model_device_select],
                    outputs=[model_download_status, model_status_md],
                    stream_every=0.2,
                )

                delete_model_btn.click(
                    fn=do_delete_model,
                    inputs=[model_select],
                    outputs=[model_status_md, model_download_status],
                    js=f"(model) => {{ if (!confirm(`{_('model_manager_delete_confirm')}`)) {{ throw new Error('cancelled'); }} return [model]; }}",
                )


            gr.Markdown(f"### {_('config_modal_title')}")
            gr.Markdown(f"### {_('config_modal_default_yaml_title')}\n{_('config_modal_default_yaml_desc')}")
            gr.Markdown("---")
            gr.Markdown(f"### {_('config_modal_gemini_yaml_title')}\n{_('config_modal_gemini_yaml_desc')}")

            with gr.Row():
                config_file_selector = gr.Dropdown(
                    choices=["settings/default.yaml", "secrets/gemini.yaml"],
                    value="settings/default.yaml",
                    label=_("select_config_file_label"),
                    scale=3,
                )
            config_editor = gr.Code(
                value=read_config_file_text("settings/default.yaml"),
                language="yaml",
                label=_("config_content_label"),
                lines=15,
            )
            with gr.Row():
                save_config_file_btn = gr.Button(_("save_config_file_btn"), variant="primary", size="sm")
                open_in_notepad_btn = gr.Button(_("open_in_notepad_btn"), variant="secondary", size="sm")


            gr.Markdown("---")
            gr.Markdown(_("updater_title"))
            with gr.Row():
                update_status_md = gr.Markdown(_("installed_version").format(version=CURRENT_VERSION))
                check_updates_btn = gr.Button(_("updater_check_btn"), variant="secondary", size="sm")
                launch_updater_btn = gr.Button(_("updater_launch_btn"), variant="primary", size="sm", visible=False)

    browse_files_btn.click(
        fn=browse_local_files,
        inputs=[file_path_input],
        outputs=[file_path_input],
    )
    browse_folders_btn.click(
        fn=browse_local_folders,
        inputs=[file_path_input],
        outputs=[file_path_input],
    )

    def _on_backend_change(b_choice):
        is_remote = (b_choice == _("backend_remote"))
        exp_text = _("explanation_remote_text") if is_remote else _("explanation_text")
        if not is_remote:
            return (
                gr.update(visible=False),
                gr.update(value=""),
                gr.update(choices=default_values['configurations']['models'], value=default_config_values["whisper_model"]),
                gr.update(choices=default_values['configurations']['compute_types'], value=default_config_values["compute_type"]),
                gr.update(visible=True),  # local_only_box (SHOW local options)
                gr.update(visible=False), # remote_only_box (HIDE remote options)
                gr.update(value=exp_text),
                gr.update(visible=True),  # save_configurations (SHOW on local)
                gr.update(visible=False), # test_remote_btn (HIDE on local)
            )
        # For remote: DO NOT make network calls automatically! Only show remote controls and prompt to test
        return (
            gr.update(visible=True),
            gr.update(value=_("remote_status_waiting")),
            gr.update(),
            gr.update(choices=["int8", "float16", "auto"]),
            gr.update(visible=False), # local_only_box (HIDES ALL NON-SERVER OPTIONS!)
            gr.update(visible=True),  # remote_only_box (SHOWS SERVER OPTIONS!)
            gr.update(value=exp_text),
            gr.update(visible=False), # save_configurations (HIDE on remote)
            gr.update(visible=True),  # test_remote_btn (SHOW on remote)
        )

    transcription_backend.change(
        fn=_on_backend_change,
        inputs=[transcription_backend],
        outputs=[
            remote_server_box,
            remote_status,
            whisper_model,
            compute_type,
            local_only_box,
            remote_only_box,
            explanation_md,
            save_configurations,
            test_remote_btn,
        ],
    )

    def _test_remote_conn(current_url):
        # Fetch models with retries
        choices, active_model, _raw_models, err = fetch_remote_models(current_url, only_downloaded=True, retries=3, retry_delay=1.0)
        if err:
            err_msg = _("remote_error_status").format(error=err)
            gr.Warning(err_msg)
            return (
                gr.update(value=err_msg),
                gr.update(),
                gr.update(choices=["int8", "float16", "auto"]),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
            )

        # Retrieve remote settings and health with retries
        settings_dict, _s_err = fetch_remote_settings(current_url, retries=3, retry_delay=1.0)
        ok, health, _h_err = check_server_health(current_url, retries=3, retry_delay=1.0)

        # Extract values from server
        active_model = settings_dict.get("WHISPER_MODEL") or active_model or (health.get("model", "") if ok else "")
        c_type = settings_dict.get("WHISPER_COMPUTE_TYPE") or (health.get("compute_type", "int8") if ok else "int8")
        server_lang = settings_dict.get("WHISPER_LANGUAGE") or (health.get("default_language", "it") if ok else "it")
        server_device = settings_dict.get("WHISPER_DEVICE") or (health.get("device", "cpu") if ok else "cpu")
        server_vad = settings_dict.get("VAD_THRESHOLD", 0.5)
        server_silence = settings_dict.get("SILENCE_DURATION_THRESHOLD", 0.6)
        server_prompt = settings_dict.get("INITIAL_PROMPT", "")

        dev_str = f"{server_device.upper()}, {c_type}"
        status_msg = _("remote_connected_status").format(model=active_model, device=dev_str)
        model_val = active_model if (active_model in choices) else (choices[0] if choices else "")

        # Compute updates for ⚙️ Advanced Configurations
        lang_update = gr.update(value=server_lang.lower()) if server_lang else gr.update()
        vad_update = gr.update(value=float(server_vad))
        silence_update = gr.update(value=float(server_silence))
        prompt_update = gr.update(value=str(server_prompt))

        return (
            gr.update(value=status_msg),
            gr.update(choices=choices, value=model_val),
            gr.update(choices=["int8", "float16", "auto"], value=c_type),
            lang_update,
            vad_update,
            silence_update,
            prompt_update,
        )

    test_remote_btn.click(
        fn=_test_remote_conn,
        inputs=[remote_server_url],
        outputs=[
            remote_status,
            whisper_model,
            compute_type,
            language,
            vad_threshold,
            silence_threshold,
            initial_prompt,
        ],
    )


    def _on_whisper_model_change(selected_model, b_choice, current_url, current_compute):
        is_remote = (b_choice == _("backend_remote"))
        if not is_remote or not selected_model or not current_url:
            return gr.update()
        ok, health, _h_err = check_server_health(current_url, retries=2)
        if ok and health.get("model") == selected_model and health.get("compute_type") == current_compute:
            dev_str = f"{health.get('device', 'cpu').upper()}, {health.get('compute_type', 'int8')}"
            return gr.update(value=_("remote_connected_status").format(model=selected_model, device=dev_str))
        switched, msg = switch_remote_model(current_url, selected_model, compute_type=current_compute, retries=2)
        if switched:
            msg_text = _("remote_model_switched").format(model=selected_model)
            gr.Info(msg_text)
            ok, health, _h_err2 = check_server_health(current_url, retries=2)
            dev_str = f"{health.get('device', 'cpu').upper()}, {health.get('compute_type', current_compute or 'int8')}" if ok else "online"
            badge_text = _("remote_connected_status").format(model=selected_model, device=dev_str)
            return gr.update(value=badge_text)
        else:
            err_text = _("remote_switch_error").format(error=msg)
            gr.Warning(err_text)
            return gr.update(value=err_text)

    whisper_model.change(
        fn=_on_whisper_model_change,
        inputs=[whisper_model, transcription_backend, remote_server_url, compute_type],
        outputs=[remote_status],
    )

    def _on_compute_type_change(new_compute, b_choice, current_url, current_model):
        is_remote = (b_choice == _("backend_remote"))
        if not is_remote or not current_url or not current_model:
            return gr.update()
        switched, msg = switch_remote_model(current_url, current_model, compute_type=new_compute, retries=2)
        if switched:
            ok, health, _h_err = check_server_health(current_url, retries=2)
            dev_str = f"{health.get('device', 'cpu').upper()}, {health.get('compute_type', new_compute)}" if ok else "online"
            badge_text = _("remote_connected_status").format(model=current_model, device=dev_str)
            gr.Info(f"Compute type commutato su: {new_compute}")
            return gr.update(value=badge_text)
        else:
            err_text = _("remote_switch_error").format(error=msg)
            gr.Warning(err_text)
            return gr.update(value=err_text)

    compute_type.change(
        fn=_on_compute_type_change,
        inputs=[compute_type, transcription_backend, remote_server_url, whisper_model],
        outputs=[remote_status],
    )

    choose_output_dir_btn.click(
        fn=browse_output_folder,
        inputs=[file_path_input, output_dir_display],
        outputs=[output_dir_display],
    )

    config_file_selector.change(
        fn=read_config_file_text,
        inputs=[config_file_selector],
        outputs=[config_editor],
    )

    save_config_file_btn.click(
        fn=write_config_file_text,
        inputs=[config_file_selector, config_editor],
        outputs=[],
    )

    open_in_notepad_btn.click(
        fn=open_file_in_notepad,
        inputs=[config_file_selector],
        outputs=[],
    )



    def _provider_change(p):
        # show Gemini model choices only when Google selected
        if str(p).lower().startswith('g'):
            return (
                gr.update(visible=True),
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
                gr.update(visible=False),
                gr.update(visible=True, choices=models, value=value),
                gr.update(visible=False, choices=[], value=""),
            )

        # when LM Studio selected, fetch models and show dropdown
        lm_models = list_lmstudio_models() or [NO_MODELS_FOUND]
        lm_value = lm_models[0] if lm_models and lm_models[0] != NO_MODELS_FOUND else ""
        return (
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False, choices=[], value=""),
            gr.update(visible=True, choices=lm_models, value=lm_value),
        )

    provider.change(fn=_provider_change, inputs=[provider], outputs=[google_brand_radio, gemini_model, ollama_model, lmstudio_model])

    def _update_google_models(brand):
        filtered = [m for m in gemini_models if brand.lower() in m.lower()]
        val = None
        if brand.lower() == "gemini":
            for m in filtered:
                if "gemini-flash-latest" in m.lower():
                    val = m
                    break
        if not val and filtered:
            val = filtered[0]
        return gr.update(choices=filtered, value=val)

    google_brand_radio.change(
        fn=_update_google_models,
        inputs=[google_brand_radio],
        outputs=[gemini_model],
    )

    query_start = submit_query_button.click(
        fn=lambda: (gr.update(visible=False), gr.update(visible=True), _("status_generating_ai")),
        inputs=[],
        outputs=[submit_query_button, stop_query_btn, status_badge]
    )
    query_event = query_start.then(
        fn=query_gemini,
        inputs=[user_query, output_text, gemini_model, provider, ollama_model, lmstudio_model, fix_text_mode, response_language],
        outputs=[gemini_response],
        stream_every=0.05,  # flush UI at most every 50 ms
    )
    query_event.then(
        fn=set_status_completed,
        inputs=[],
        outputs=[status_badge]
    ).then(
        fn=lambda: (gr.update(visible=True), gr.update(visible=False)),
        inputs=[],
        outputs=[submit_query_button, stop_query_btn]
    ).then(
        fn=None,
        inputs=[],
        js="() => { playCompletionSound(); }"
    )
    stop_query_btn.click(
        fn=lambda: (gr.update(visible=True), gr.update(visible=False), _("status_ai_interrupted")),
        inputs=[],
        outputs=[submit_query_button, stop_query_btn, status_badge],
        cancels=[query_event]
    )
    with gr.Row():
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

    for btn in [save_configurations, save_settings_btn]:
        btn.click(
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
                ui_language_dropdown,
                transcription_backend,
                remote_server_url,
                vad_threshold,
                silence_threshold,
                initial_prompt,
            ],
            outputs=[]
        )

    reset_button.click(
        fn=reset_fields,
        inputs=[],
        outputs=[file_path_input, config_path_input, device, cpu_threads, num_workers, language, whisper_model, compute_type, temperature, beam_size, batch_size, condition_on_previous_text, output_text, transcript_file_path, word_timestamps, gemini_model, user_query, gemini_response, save_transcript_button, submit_query_button, output_format, status_badge, provider, google_brand_radio]
    ).then(fn=lambda: False, inputs=[], outputs=[fix_text_mode])

    def transcribe_wrapper(file_paths_text, device, cpu_threads, num_workers, language, whisper_model, compute_type, temperature, beam_size, batch_size, condition_on_previous_text, word_timestamps, output_format=".txt", output_dir_override="", backend_choice=None, remote_url="http://192.168.1.32:8088", initial_prompt="", progress=gr.Progress(track_tqdm=False)):
        if not file_paths_text or not file_paths_text.strip():
            yield _("invalid_file").format("No file selected"), None, gr.update(visible=False), gr.update(visible=False), gr.update()
            return

        is_remote = (backend_choice == _("backend_remote") or backend_choice == "remote")
        backend_val = "remote" if is_remote else "local"

        progress(0.05, desc=_("progress_prep_transcription"))
        yield _("transcription_in_progress"), None, gr.update(visible=False), gr.update(visible=False), gr.update()

        raw_paths = [p.strip() for p in file_paths_text.strip().split('\n') if p.strip()]
        
        SUPPORTED_EXTS = {".avi", ".flac", ".m4a", ".mkv", ".mov", ".mp3", ".mp4", ".ogg", ".opus", ".wav", ".webm"}
        expanded_paths = []
        for p in raw_paths:
            if os.path.isdir(p):
                for root_dir, dirs, files in os.walk(p):
                    for f in files:
                        ext = os.path.splitext(f)[1].lower()
                        if ext in SUPPORTED_EXTS:
                            expanded_paths.append(os.path.join(root_dir, f))
            else:
                expanded_paths.append(p)

        file_paths_text_new = "\n".join(expanded_paths)

        if not expanded_paths:
            yield _("invalid_file").format("No valid files found"), None, gr.update(visible=False), gr.update(visible=False), file_paths_text
            return

        valid_paths = []
        for path in expanded_paths:
            try:
                valid_paths.append(str(validate_local_media_path(path)))
            except SecurityError as e:
                logging.warning("Rejected media path: %s", e)
                yield _("invalid_file").format(f"{path}: {e}"), None, gr.update(visible=False), gr.update(visible=False), file_paths_text_new
                return

        # Compute timestamped output directory
        from pathlib import Path
        common_root, output_dir, timestamp_str = _compute_output_dir(expanded_paths, output_dir_override or "")

        session_transcription = ""
        last_output_path = None

        progress_desc = _("progress_uploading_remote") if is_remote else _("progress_loading_whisper")
        progress(0.15, desc=progress_desc)
        for transcription, output_path, _folder_path in transcribe_file(
            valid_paths, device, cpu_threads, num_workers, language,
            whisper_model, compute_type, temperature, beam_size,
            batch_size, condition_on_previous_text, word_timestamps,
            output_format, output_dir=output_dir, common_root=common_root,
            backend=backend_val, remote_server_url=remote_url,
            initial_prompt=initial_prompt,
        ):
            if output_path:
                last_output_path = output_path
                yield transcription, output_path, gr.update(visible=True), gr.update(visible=True), file_paths_text_new
            else:
                yield transcription, output_path, gr.update(visible=False), gr.update(visible=False), file_paths_text_new

        progress(1.0, desc=_("progress_transcription_completed"))
        # Save combined transcription file at session end only when multiple files are processed
        if len(expanded_paths) > 1 and last_output_path:
            try:
                combined_file = output_dir / f"{timestamp_str}_transcription{output_format}"
                with open(combined_file, "w", encoding="utf-8") as f:
                    f.write(transcription)
                logging.info(f"Combined transcription saved to {combined_file}")
            except Exception as e:
                logging.error(f"Error saving combined transcription: {e}", exc_info=True)

    proc_start = transcribe_button.click(
        fn=lambda: (gr.update(visible=False), gr.update(visible=True), _("status_transcribing")),
        inputs=[],
        outputs=[transcribe_button, stop_transcribe_btn, status_badge]
    )
    proc_event = proc_start.then(
        fn=transcribe_wrapper,
        inputs=[file_path_input, device, cpu_threads, num_workers, language, whisper_model, compute_type, temperature, beam_size, batch_size, condition_on_previous_text, word_timestamps, output_format, output_dir_display, transcription_backend, remote_server_url, initial_prompt],
        outputs=[output_text, transcript_file_path, save_transcript_button, submit_query_button, file_path_input],
        stream_every=0.1
    )
    proc_event.then(
        fn=set_status_completed,
        inputs=[],
        outputs=[status_badge]
    ).then(
        fn=lambda: (gr.update(visible=True), gr.update(visible=False)),
        inputs=[],
        outputs=[transcribe_button, stop_transcribe_btn]
    ).then(
        fn=None,
        inputs=[],
        js="() => { playCompletionSound(); }"
    )
    stop_transcribe_btn.click(
        fn=lambda: (gr.update(visible=True), gr.update(visible=False), _("status_interrupted")),
        inputs=[],
        outputs=[transcribe_button, stop_transcribe_btn, status_badge],
        cancels=[proc_event]
    )

    quit_button.click(
        fn=quit_app,
        inputs=[],
        outputs=[]
    )

    def save_transcript_wrapper(file_path, output_format=".txt"):
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
                defaultextension=output_format,
                filetypes=[
                    (_("markdown_files_filter") if output_format == ".md" else _("text_files_filter"), f"*{output_format}"),
                    (_("all_files_filter"), "*.*")
                ],
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
        inputs=[transcript_file_path, output_format], 
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

    def on_check_updates():
        res = check_for_updates()
        if res.get("has_update"):
            msg = _("update_available").format(latest=res['latest_version'], current=CURRENT_VERSION)
            btn_label = _("updater_launch_update_btn").format(latest=res['latest_version'])
            return msg, gr.update(value=btn_label, variant="primary", visible=True)
        elif "check_failed" in str(res.get("status")):
            msg = _("update_check_failed").format(current=CURRENT_VERSION)
            btn_label = _("updater_reinstall_btn").format(version=CURRENT_VERSION)
            return msg, gr.update(value=btn_label, variant="secondary", visible=True)
        else:
            msg = _("update_up_to_date").format(current=CURRENT_VERSION)
            btn_label = _("updater_reinstall_btn").format(version=CURRENT_VERSION)
            return msg, gr.update(value=btn_label, variant="secondary", visible=True)

    check_updates_btn.click(
        fn=on_check_updates,
        inputs=[],
        outputs=[update_status_md, launch_updater_btn]
    )

    def on_launch_updater():
        success, outcome = launch_installer_update()
        if success:
            if outcome == "opened_browser":
                msg = _("updater_launched_browser")
                gr.Info(msg)
                return f"🌐 **{msg}**"
            else:
                msg = _("update_installer_launched")
                gr.Info(msg)
                return f"🚀 **{msg}**"
        else:
            err = _("update_installer_failed")
            gr.Error(err)
            return f"❌ **{err}** (`{outcome}`)"

    launch_updater_btn.click(
        fn=on_launch_updater,
        inputs=[],
        outputs=[update_status_md]
    )
