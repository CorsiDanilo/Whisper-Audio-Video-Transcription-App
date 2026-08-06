"""
locales.py - Multilingual localization dictionary for Whisper Utility Setup Wizard.

Supports English (en) and Italian (it).
Automatically detects the operating system locale via locale.getdefaultlocale().
"""

import locale
from typing import Dict, Any, Optional

STRINGS_EN: Dict[str, str] = {
    "title": "Whisper Utility – Setup Wizard",
    "welcome_heading": "Welcome to Whisper Utility",
    "welcome_sub": "Setup Wizard",
    "os_label": "🖥  OS:",
    "gpu_label_cuda": "⚡  GPU:   {gpu}  (CUDA accelerated)",
    "gpu_label_metal": "⚡  GPU:   Apple Silicon – Metal / Accelerate",
    "gpu_label_cpu": "💻  GPU:   None detected – CPU-only mode",
    "path_label": "Installation directory:",
    "btn_browse": "Browse…",
    "btn_next": "Next →",
    "btn_back": "← Back",
    "btn_install": "Install",
    "btn_cancel": "Cancel",
    "btn_finish": "Finish",
    "summary_title": "Components to Install",
    "summary_core": "Whisper Utility (core application)",
    "summary_ffmpeg": "FFmpeg static build (official mirror)",
    "summary_cuda": "CUDA runtime libraries (cuBLAS / cuDNN)",
    "summary_dest": "→ Destination:",
    "installing_title": "Installing…",
    "lbl_file_progress": "Current file:",
    "lbl_overall_progress": "Overall progress:",
    "complete_title": "✅  Installation complete!",
    "complete_sub": "Whisper Utility was installed to:",
    "failed_title": "❌  Installation failed",
    "failed_sub": "Check the log above for details.",
    "chk_launch": "Launch Whisper Utility now",
    "msg_preparing": "Preparing installation…",
    "msg_fetching_manifest": "Fetching installation manifest…",
    "msg_manifest_error": "⚠ Could not fetch remote manifest: {exc}",
    "msg_manifest_fallback": "Continuing with local manifest fallback…",
    "msg_creating_shortcuts": "Creating shortcuts and uninstaller…",
    "msg_complete": "Installation Complete!",
    "config_title": "Configuration Settings",
    "config_sub": "Customize your initial setup or keep existing settings.",
    "config_existing_detected": "ℹ  Existing settings detected in destination folder. Pre-filled below.",
    "lbl_gemini_key": "Gemini API Key (optional):",
    "lbl_ui_language": "Interface Language:",
    "lbl_whisper_model": "Default Whisper Model:",
    "lbl_device": "Computation Device:",
    "lbl_cpu_threads": "CPU Threads:",
}

STRINGS_IT: Dict[str, str] = {
    "title": "Whisper Utility – Procedura di Installazione",
    "welcome_heading": "Benvenuto in Whisper Utility",
    "welcome_sub": "Installazione guidata",
    "os_label": "🖥  OS:",
    "gpu_label_cuda": "⚡  GPU:   {gpu}  (Accelerazione CUDA)",
    "gpu_label_metal": "⚡  GPU:   Apple Silicon – Metal / Accelerate",
    "gpu_label_cpu": "💻  GPU:   Nessuna GPU – Modalità CPU",
    "path_label": "Cartella di destinazione:",
    "btn_browse": "Sfoglia…",
    "btn_next": "Avanti →",
    "btn_back": "← Indietro",
    "btn_install": "Installa",
    "btn_cancel": "Annulla",
    "btn_finish": "Fine",
    "summary_title": "Componenti da Installare",
    "summary_core": "Whisper Utility (applicazione principale)",
    "summary_ffmpeg": "FFmpeg statico (mirror ufficiale)",
    "summary_cuda": "Librerie CUDA (cuBLAS / cuDNN)",
    "summary_dest": "→ Destinazione:",
    "installing_title": "Installazione in corso…",
    "lbl_file_progress": "File corrente:",
    "lbl_overall_progress": "Avanzamento totale:",
    "complete_title": "✅  Installazione completata!",
    "complete_sub": "Whisper Utility è stata installata in:",
    "failed_title": "❌  Installazione fallita",
    "failed_sub": "Controlla il registro degli errori per i dettagli.",
    "chk_launch": "Avvia Whisper Utility ora",
    "msg_preparing": "Preparazione dell'installazione…",
    "msg_fetching_manifest": "Recupero manifest di installazione…",
    "msg_manifest_error": "⚠ Impossibile recuperare il manifest remoto: {exc}",
    "msg_manifest_fallback": "Uso del manifest locale di riserva…",
    "msg_creating_shortcuts": "Creazione delle scorciatoie ed uninstaller…",
    "msg_complete": "Installazione Completata!",
    "config_title": "Configurazione Impostazioni",
    "config_sub": "Personalizza le opzioni o mantieni quelle correnti.",
    "config_existing_detected": "ℹ  Impostazioni esistenti rilevate nella destinazione. Campi pre-compilati.",
    "lbl_gemini_key": "Gemini API Key (opzionale):",
    "lbl_ui_language": "Lingua Interfaccia:",
    "lbl_whisper_model": "Modello Whisper Predefinito:",
    "lbl_device": "Dispositivo di Calcolo:",
    "lbl_cpu_threads": "Thread CPU:",
}


def get_locale_strings(override_lang: Optional[str] = None) -> Dict[str, str]:
    """Return dictionary of UI strings for the current system locale or override_lang.

    Accepts both ISO 639-1 codes ('it', 'en') and long names ('italian', 'english').
    """
    if override_lang:
        lang = override_lang.lower()
    else:
        try:
            loc = locale.getdefaultlocale()[0]
            lang = loc.split("_")[0].lower() if loc else "en"
        except Exception:
            lang = "en"

    # Normalise: accept both 'it' / 'italian' and 'en' / 'english'
    is_italian = lang in ("it", "italian")
    return STRINGS_IT if is_italian else STRINGS_EN
