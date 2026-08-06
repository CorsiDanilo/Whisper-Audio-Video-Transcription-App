"""
splash.py - Lightweight bilingual splash screen for Whisper Utility Installer.
"""

import locale
import os
import sys
import tkinter as tk
from tkinter import ttk


_STRINGS = {
    "it": {
        "title": "Whisper Utility Setup – Avvio in corso...",
        "init": "⚙️  Inizializzazione programma di installazione...",
        "hw": "🔍  Rilevamento componenti di sistema...",
        "gui": "🚀  Caricamento interfaccia guidata...",
        "ready": "✅  Pronto!",
    },
    "en": {
        "title": "Whisper Utility Setup – Launching...",
        "init": "⚙️  Initializing setup installer...",
        "hw": "🔍  Detecting system hardware...",
        "gui": "🚀  Loading setup wizard...",
        "ready": "✅  Ready!",
    },
}


def _detect_lang() -> str:
    """Detect OS system language, return 'it' or 'en'."""
    try:
        loc = locale.getdefaultlocale()[0]
        code = loc.split("_")[0].lower() if loc else "en"
        return "it" if code == "it" else "en"
    except Exception:
        return "en"


def _get_icon_path() -> str:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        p = os.path.join(base, "logo.ico")
        if os.path.exists(p):
            return p
    for candidate in [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.ico"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logo.ico"),
        os.path.abspath("logo.ico"),
    ]:
        if os.path.exists(candidate):
            return candidate
    return ""


# ── Colour palette ───────────────────────────────────────────────────────────
_BG = "#1a1a2e"
_SURFACE = "#16213e"
_ACCENT = "#e94560"
_TEXT = "#eaeaea"
_MUTED = "#8899aa"


class InstallerSplashScreen:
    """Minimal Tkinter splash screen shown during setup initialization."""

    def __init__(self) -> None:
        self._lang = _detect_lang()
        self._strings = _STRINGS["it"] if self._lang == "it" else _STRINGS["en"]
        self._closed = False

        self._root = tk.Tk()
        self._root.overrideredirect(True)  # borderless window
        self._root.configure(bg=_BG)
        self._root.attributes("-topmost", True)

        try:
            icon = _get_icon_path()
            if icon:
                self._root.iconbitmap(icon)
        except Exception:
            pass

        # ── Window size & centering ───────────────────────────────────────────
        W, H = 480, 240
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        self._root.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")

        # ── Accent border (left bar) ───────────────────────────────────────────
        bar = tk.Frame(self._root, bg=_ACCENT, width=5)
        bar.pack(side="left", fill="y")

        inner = tk.Frame(self._root, bg=_BG, padx=28, pady=28)
        inner.pack(fill="both", expand=True)

        # App title
        tk.Label(
            inner,
            text="🎙️ Whisper Utility Setup",
            bg=_BG,
            fg=_TEXT,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")

        # Subtitle
        tk.Label(
            inner,
            text=self._strings["title"].split("–")[-1].strip(),
            bg=_BG,
            fg=_MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(2, 16))

        # Status label
        self._status_var = tk.StringVar(value=self._strings["init"])
        tk.Label(
            inner,
            textvariable=self._status_var,
            bg=_BG,
            fg=_TEXT,
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        ).pack(anchor="w", fill="x")

        # Progress bar
        style = ttk.Style(self._root)
        style.theme_use("clam")
        style.configure(
            "Splash.Horizontal.TProgressbar",
            troughcolor=_SURFACE,
            background=_ACCENT,
            bordercolor=_BG,
            lightcolor=_ACCENT,
            darkcolor=_ACCENT,
        )
        self._progress_var = tk.IntVar(value=0)
        self._bar = ttk.Progressbar(
            inner,
            orient="horizontal",
            length=400,
            mode="determinate",
            variable=self._progress_var,
            style="Splash.Horizontal.TProgressbar",
        )
        self._bar.pack(anchor="w", fill="x", pady=(10, 0))

        # Version label
        tk.Label(
            inner,
            text="v3.1.0",
            bg=_BG,
            fg=_MUTED,
            font=("Segoe UI", 8),
        ).pack(anchor="e", pady=(6, 0))

        self._root.update()

    def update_status(self, message_key: str, percentage: int) -> None:
        if self._closed:
            return
        text = self._strings.get(message_key, message_key)
        self._status_var.set(text)
        self._progress_var.set(max(0, min(100, percentage)))
        try:
            self._root.update()
        except Exception:
            pass

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._root.destroy()
        except Exception:
            pass
