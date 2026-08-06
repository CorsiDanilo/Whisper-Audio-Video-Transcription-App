"""
gui.py - Multi-step Tkinter installer wizard for Whisper Utility (v2).

Pages:
    1. Welcome & path selection
    2. Hardware summary & component list
    3. Download & installation progress (with speed/ETA metrics)
    4. Completion

All network/disk operations run on a background thread so the GUI
remains responsive. All text labels adapt automatically to the user's OS language.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import ctypes
from typing import Optional

from installer.downloader import DownloadError, FileDownloader, format_bytes, format_eta
from installer.extractor import extract_archive
from installer.hardware_detector import HardwareInfo, detect_hardware
from installer.locales import get_locale_strings
from installer.manifest import Manifest, ManifestError
from installer.shortcut_manager import create_shortcuts, create_uninstaller
from installer.config_manager import load_existing_configs, save_merged_configs

if sys.platform == "win32":
    try:
        app_id = "CorsiDanilo.WhisperUtility.Installer"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

# ── Colour palette ────────────────────────────────────────────────────────────
BG = "#1a1a2e"
SURFACE = "#16213e"
ACCENT = "#e94560"
ACCENT2 = "#0f3460"
TEXT = "#eaeaea"
MUTED = "#8899aa"
SUCCESS = "#4caf50"

FONT_TITLE = ("Segoe UI", 20, "bold")
FONT_HEADING = ("Segoe UI", 13, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_MONO = ("Consolas", 9)

MANIFEST_URL = (
    "https://raw.githubusercontent.com/CorsiDanilo/whisper-utility/main/installer/manifest.json"
)

# Placeholder used while hardware detection runs in background
_HARDWARE_LOADING = "detecting..."


class InstallerWizard(tk.Tk):
    """Root window that hosts a stack of wizard page frames."""

    def __init__(self) -> None:
        super().__init__()

        # ── Locale (detect system language immediately, before any widget creation) ──
        self._lang_code = "it"  # default; updated in _reload_locale
        try:
            import locale
            loc = locale.getdefaultlocale()[0]
            self._lang_code = loc.split("_")[0].lower() if loc else "en"
        except Exception:
            self._lang_code = "en"
        self.strings = get_locale_strings(self._lang_code)

        # ── Placeholder hardware (window opens instantly) ──────────────────────
        self.hardware: HardwareInfo = HardwareInfo(
            os_name="windows", arch="x64",
            has_nvidia_gpu=False, is_apple_silicon=False,
            gpu_name=None,
        )
        self._hw_ready = False
        self.default_dir = self._default_install_dir()
        self.install_dir = tk.StringVar(value=self.default_dir)
        self.manifest: Optional[Manifest] = None
        self._downloader = FileDownloader()
        self._cancel_flag = threading.Event()

        # ── Configuration State ──────────────────────────────────────────────
        self.gemini_key_var = tk.StringVar(value="")
        self.ui_lang_var = tk.StringVar(value="italian")
        self.whisper_model_var = tk.StringVar(value="large-v3")
        self.device_var = tk.StringVar(value="cpu")  # updated after hw detection
        self.cpu_threads_var = tk.IntVar(value=min(os.cpu_count() or 6, 16))
        self.has_existing_configs = False

        # ── Window setup ──────────────────────────────────────────────────────
        self.title(self.strings["title"])
        self.geometry("680x460")
        self.resizable(False, False)
        self.configure(bg=BG)
        self._center_window()

        try:
            self.iconbitmap(self._resource("logo.ico"))
        except Exception:
            pass

        # ── Style ─────────────────────────────────────────────────────────────
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Surface.TFrame", background=SURFACE)
        style.configure("TLabel", background=BG, foreground=TEXT, font=FONT_BODY)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=FONT_BODY)
        style.configure("Surface.TLabel", background=SURFACE, foreground=TEXT, font=FONT_BODY)
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=FONT_TITLE)
        style.configure("Heading.TLabel", background=BG, foreground=ACCENT, font=FONT_HEADING)
        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=(16, 8),
        )
        style.map("Accent.TButton", background=[("active", "#c73652")])
        style.configure(
            "Ghost.TButton",
            background=SURFACE,
            foreground=MUTED,
            font=FONT_BODY,
            relief="flat",
            padding=(12, 6),
        )
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=SURFACE,
            background=ACCENT,
            bordercolor=BG,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
        )
        style.configure(
            "Green.Horizontal.TProgressbar",
            troughcolor=SURFACE,
            background=SUCCESS,
        )
        style.configure("TEntry", fieldbackground=SURFACE, foreground=TEXT, insertcolor=TEXT)

        # ── Page container ────────────────────────────────────────────────────
        self._container = ttk.Frame(self)
        self._container.pack(fill="both", expand=True)

        self._show_welcome()

        # ── Kick off hardware detection in background ─────────────────────────
        threading.Thread(target=self._detect_hw_async, daemon=True).start()

    # ── Page navigation ───────────────────────────────────────────────────────

    def _detect_hw_async(self) -> None:
        """Run hardware detection in background and update UI when done."""
        result = detect_hardware()
        self._hw_ready = True
        self.hardware = result
        # Update device_var based on actual hardware
        self.device_var.set("cuda" if result.has_nvidia_gpu else "cpu")
        # Update the welcome page hardware info label if still visible
        self.after(0, self._refresh_hw_label)

    def _refresh_hw_label(self) -> None:
        """Refresh hardware status label on the welcome page (if it exists)."""
        if hasattr(self, "_hw_status_var"):
            if self.hardware.has_nvidia_gpu:
                gpu_text = self.strings["gpu_label_cuda"].format(gpu=self.hardware.gpu_name)
            elif self.hardware.is_apple_silicon:
                gpu_text = self.strings["gpu_label_metal"]
            else:
                gpu_text = self.strings["gpu_label_cpu"]
            os_text = f"{self.strings['os_label']}    {self.hardware.os_name.title()} ({self.hardware.arch})"
            self._hw_status_var.set(f"{os_text}\n{gpu_text}")
        if hasattr(self, "_hw_spinner_var"):
            self._hw_spinner_var.set("")

    def _reload_locale(self, lang_code: str) -> None:
        """Switch installer UI language and re-render current page."""
        self._lang_code = lang_code
        self.strings = get_locale_strings(lang_code)
        self.title(self.strings["title"])
        self._show_welcome()

    def _clear(self) -> None:
        for child in self._container.winfo_children():
            child.destroy()

    def _show_welcome(self) -> None:
        self._clear()
        f = ttk.Frame(self._container, padding=(40, 30))
        f.pack(fill="both", expand=True)

        # Left accent bar
        accent_bar = tk.Frame(f, bg=ACCENT, width=4)
        accent_bar.place(x=0, y=0, relheight=1)

        # ── Language selector row (top-right) ─────────────────────────────────
        lang_row = ttk.Frame(f)
        lang_row.pack(anchor="ne", pady=(0, 8))
        _lang_label_it = "🌐 Lingua / Language:"
        ttk.Label(lang_row, text=_lang_label_it, style="Muted.TLabel").pack(side="left", padx=(0, 6))
        _lang_var = tk.StringVar(value=self._lang_code)
        _lang_cb = ttk.Combobox(
            lang_row,
            textvariable=_lang_var,
            values=["it", "en"],
            state="readonly",
            width=5,
        )
        _lang_cb.pack(side="left")

        def _on_lang_change(event=None):
            self._reload_locale(_lang_var.get())

        _lang_cb.bind("<<ComboboxSelected>>", _on_lang_change)

        ttk.Label(f, text=self.strings["welcome_heading"], style="Title.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(f, text=self.strings["welcome_sub"], style="Heading.TLabel").pack(anchor="w", pady=(0, 12))

        # System info card (live-updating)
        card = ttk.Frame(f, style="Surface.TFrame", padding=12)
        card.pack(fill="x", pady=(0, 10))

        self._hw_status_var = tk.StringVar()
        self._hw_spinner_var = tk.StringVar()
        if self._hw_ready:
            # Hardware already detected (e.g., page refreshed via language switch)
            self._refresh_hw_label()
        else:
            _detecting_it = "⏳ Rilevamento hardware in corso..." if self._lang_code == "it" else "⏳ Detecting hardware..."
            self._hw_status_var.set(_detecting_it)
            self._hw_spinner_var.set("")

        ttk.Label(card, textvariable=self._hw_status_var, style="Surface.TLabel", justify="left").pack(anchor="w")
        ttk.Label(card, textvariable=self._hw_spinner_var, style="Surface.TLabel", foreground=MUTED).pack(anchor="w")

        # Install path
        ttk.Label(f, text=self.strings["path_label"]).pack(anchor="w", pady=(8, 2))
        row = ttk.Frame(f)
        row.pack(fill="x", pady=(0, 20))
        ttk.Entry(row, textvariable=self.install_dir, width=52).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(row, text=self.strings["btn_browse"], style="Ghost.TButton", command=self._browse).pack(side="left")

        # Navigation
        nav = ttk.Frame(f)
        nav.pack(fill="x", side="bottom")
        ttk.Button(nav, text=self.strings["btn_next"], style="Accent.TButton", command=self._show_summary).pack(side="right")

    def _show_summary(self) -> None:
        self._clear()
        f = ttk.Frame(self._container, padding=(40, 30))
        f.pack(fill="both", expand=True)

        ttk.Label(f, text=self.strings["summary_title"], style="Title.TLabel").pack(anchor="w", pady=(0, 16))

        items = [
            ("📦", self.strings["summary_core"], "~120 MB"),
            ("🎬", self.strings["summary_ffmpeg"], "~80 MB"),
        ]
        if self.hardware.has_nvidia_gpu:
            items.append(("⚡", self.strings["summary_cuda"], "~350 MB"))

        card = ttk.Frame(f, style="Surface.TFrame", padding=14)
        card.pack(fill="x", pady=(0, 20))
        for icon, label, size in items:
            row = ttk.Frame(card, style="Surface.TFrame")
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=f"{icon}  {label}", style="Surface.TLabel", width=46).pack(side="left")
            ttk.Label(row, text=size, style="Surface.TLabel", foreground=MUTED).pack(side="right")

        ttk.Label(
            f,
            text=f"{self.strings['summary_dest']}  {self.install_dir.get()}",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 20))

        nav = ttk.Frame(f)
        nav.pack(fill="x", side="bottom")
        ttk.Button(nav, text=self.strings["btn_back"], style="Ghost.TButton", command=self._show_welcome).pack(side="left")
        ttk.Button(nav, text=self.strings["btn_next"], style="Accent.TButton", command=self._show_config).pack(side="right")

    def _show_config(self) -> None:
        self._clear()
        f = ttk.Frame(self._container, padding=(40, 20))
        f.pack(fill="both", expand=True)

        # Check existing config in install_dir
        existing = load_existing_configs(self.install_dir.get())
        if existing["has_existing"]:
            self.has_existing_configs = True
            if existing["gemini_api_key"]:
                self.gemini_key_var.set(existing["gemini_api_key"])
            st = existing["settings"]
            if "ui_language" in st:
                self.ui_lang_var.set(st["ui_language"])
            if "whisper_model" in st:
                self.whisper_model_var.set(st["whisper_model"])
            if "device" in st:
                self.device_var.set(st["device"])
            if "cpu_threads" in st:
                try:
                    self.cpu_threads_var.set(int(st["cpu_threads"]))
                except Exception:
                    pass

        ttk.Label(f, text=self.strings.get("config_title", "Configuration"), style="Title.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(f, text=self.strings.get("config_sub", "Customize settings"), style="Muted.TLabel").pack(anchor="w", pady=(0, 10))

        if existing["has_existing"]:
            note_card = ttk.Frame(f, style="Surface.TFrame", padding=8)
            note_card.pack(fill="x", pady=(0, 10))
            ttk.Label(
                note_card,
                text=self.strings.get("config_existing_detected", "Existing settings detected"),
                style="Surface.TLabel",
                foreground=ACCENT,
            ).pack(anchor="w")

        form = ttk.Frame(f)
        form.pack(fill="x", expand=True, pady=(0, 10))

        # Gemini API Key
        ttk.Label(form, text=self.strings.get("lbl_gemini_key", "Gemini API Key:")).grid(row=0, column=0, sticky="w", pady=4, padx=(0, 10))
        key_entry = ttk.Entry(form, textvariable=self.gemini_key_var, width=42, show="•")
        key_entry.grid(row=0, column=1, sticky="w", pady=4)

        show_var = tk.BooleanVar(value=False)

        def _toggle_key():
            key_entry.configure(show="" if show_var.get() else "•")

        ttk.Checkbutton(form, text="👁", variable=show_var, command=_toggle_key).grid(row=0, column=2, sticky="w", padx=4)

        # UI Language
        ttk.Label(form, text=self.strings.get("lbl_ui_language", "Interface Language:")).grid(row=1, column=0, sticky="w", pady=4, padx=(0, 10))
        lang_cb = ttk.Combobox(form, textvariable=self.ui_lang_var, values=["italian", "english", "spanish", "french", "german"], state="readonly", width=39)
        lang_cb.grid(row=1, column=1, sticky="w", pady=4)

        # Whisper Model
        ttk.Label(form, text=self.strings.get("lbl_whisper_model", "Whisper Model:")).grid(row=2, column=0, sticky="w", pady=4, padx=(0, 10))
        model_cb = ttk.Combobox(form, textvariable=self.whisper_model_var, values=["large-v3", "medium", "base", "small", "tiny", "large-v3-turbo", "distil-large-v3"], state="readonly", width=39)
        model_cb.grid(row=2, column=1, sticky="w", pady=4)

        # Device
        ttk.Label(form, text=self.strings.get("lbl_device", "Computation Device:")).grid(row=3, column=0, sticky="w", pady=4, padx=(0, 10))
        dev_cb = ttk.Combobox(form, textvariable=self.device_var, values=["cuda", "cpu"], state="readonly", width=39)
        dev_cb.grid(row=3, column=1, sticky="w", pady=4)

        # CPU Threads
        ttk.Label(form, text=self.strings.get("lbl_cpu_threads", "CPU Threads:")).grid(row=4, column=0, sticky="w", pady=4, padx=(0, 10))
        cpu_sb = ttk.Spinbox(form, from_=1, to=16, textvariable=self.cpu_threads_var, width=10)
        cpu_sb.grid(row=4, column=1, sticky="w", pady=4)

        # Navigation
        nav = ttk.Frame(f)
        nav.pack(fill="x", side="bottom")
        ttk.Button(nav, text=self.strings["btn_back"], style="Ghost.TButton", command=self._show_summary).pack(side="left")
        ttk.Button(nav, text=self.strings["btn_install"], style="Accent.TButton", command=self._start_install).pack(side="right")

    def _show_progress(self) -> None:
        self._clear()
        f = ttk.Frame(self._container, padding=(40, 30))
        f.pack(fill="both", expand=True)

        ttk.Label(f, text=self.strings["installing_title"], style="Title.TLabel").pack(anchor="w", pady=(0, 20))

        # Current component
        self._status_var = tk.StringVar(value=self.strings["msg_preparing"])
        ttk.Label(f, textvariable=self._status_var, style="Heading.TLabel").pack(anchor="w")

        # Per-file progress
        ttk.Label(f, text=self.strings["lbl_file_progress"]).pack(anchor="w", pady=(10, 2))
        self._file_bar = ttk.Progressbar(f, style="Horizontal.TProgressbar", length=580, mode="determinate")
        self._file_bar.pack(fill="x")
        self._file_pct = tk.StringVar(value="0 %")
        ttk.Label(f, textvariable=self._file_pct, style="Muted.TLabel").pack(anchor="e")

        # Overall progress
        ttk.Label(f, text=self.strings["lbl_overall_progress"]).pack(anchor="w", pady=(10, 2))
        self._overall_bar = ttk.Progressbar(f, style="Horizontal.TProgressbar", length=580, mode="determinate")
        self._overall_bar.pack(fill="x")
        self._overall_pct = tk.StringVar(value="0 %")
        ttk.Label(f, textvariable=self._overall_pct, style="Muted.TLabel").pack(anchor="e")

        # Log box
        self._log = tk.Text(
            f,
            height=6,
            bg=SURFACE,
            fg=TEXT,
            font=FONT_MONO,
            relief="flat",
            state="disabled",
        )
        self._log.pack(fill="both", expand=True, pady=(14, 0))

        self._cancel_flag.clear()
        nav = ttk.Frame(f)
        nav.pack(fill="x", side="bottom", pady=(10, 0))
        ttk.Button(nav, text=self.strings["btn_cancel"], style="Ghost.TButton", command=self._cancel).pack(side="right")

    def _show_done(self, success: bool = True) -> None:
        log_text = ""
        if hasattr(self, "_log"):
            try:
                log_text = self._log.get("1.0", "end").strip()
            except Exception:
                pass

        self._clear()
        f = ttk.Frame(self._container, padding=(40, 30))
        f.pack(fill="both", expand=True)

        if success:
            ttk.Label(f, text=self.strings["complete_title"], style="Title.TLabel").pack(anchor="w", pady=(0, 10))
            ttk.Label(
                f,
                text=f"{self.strings['complete_sub']}\n{self.install_dir.get()}",
                style="Muted.TLabel",
            ).pack(anchor="w", pady=(0, 20))
            self._launch_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(f, text=self.strings["chk_launch"], variable=self._launch_var).pack(anchor="w")
        else:
            ttk.Label(f, text=self.strings["failed_title"], style="Title.TLabel").pack(anchor="w", pady=(0, 10))
            ttk.Label(f, text=self.strings["failed_sub"], style="Muted.TLabel").pack(anchor="w")
            self._launch_var = tk.BooleanVar(value=False)
            
            if log_text:
                log_box = tk.Text(
                    f,
                    height=8,
                    bg=SURFACE,
                    fg=TEXT,
                    font=FONT_MONO,
                    relief="flat",
                )
                log_box.pack(fill="both", expand=True, pady=(14, 0))
                log_box.insert("end", log_text)
                log_box.see("end")
                log_box.configure(state="disabled")

        nav = ttk.Frame(f)
        nav.pack(fill="x", side="bottom")
        ttk.Button(nav, text=self.strings["btn_finish"], style="Accent.TButton", command=lambda: self._finish(success)).pack(side="right")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _browse(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.install_dir.get(), title="Select installation directory")
        if selected:
            self.install_dir.set(selected)

    def _cancel(self) -> None:
        self._cancel_flag.set()

    def _start_install(self) -> None:
        self._show_progress()
        thread = threading.Thread(target=self._install_worker, daemon=True)
        thread.start()

    def _install_worker(self) -> None:
        try:
            self._log_write(f"{self.strings['msg_fetching_manifest']}\n")
            try:
                self.manifest = Manifest.fetch_remote(MANIFEST_URL)
            except ManifestError as exc:
                self._log_write(f"{self.strings['msg_manifest_error'].format(exc=exc)}\n")
                self._log_write(f"{self.strings['msg_manifest_fallback']}\n")
                local = self._resource("manifest.json")
                self.manifest = Manifest.from_file(local)

            os_name = self.hardware.os_name
            arch = self.hardware.arch
            install_dir = self.install_dir.get()

            # Build download queue
            tasks: list[tuple[str, str, str | None]] = []

            core_key = "windows" if os_name == "windows" else f"{os_name}_{arch}"
            core_url = self.manifest.get_component_url("app_core", core_key)
            if core_url:
                ext = ".zip" if os_name == "windows" else ".tar.gz"
                tasks.append((core_url, os.path.join(install_dir, f"app_core{ext}"), None))

            ffmpeg_url = self.manifest.get_ffmpeg_url(os_name, arch)
            if ffmpeg_url:
                fname = ffmpeg_url.split("/")[-1]
                tasks.append((ffmpeg_url, os.path.join(install_dir, "ffmpeg", fname), None))

            if os_name == "windows" and self.hardware.has_nvidia_gpu:
                cuda_url = self.manifest.get_component_url("cuda_libs", "windows_nvidia")
                if cuda_url:
                    tasks.append((cuda_url, os.path.join(install_dir, "cuda_libs.zip"), None))

            total = len(tasks)
            for idx, (url, dest, sha) in enumerate(tasks, start=1):
                if self._cancel_flag.is_set():
                    self._log_write("Installation cancelled.\n")
                    return
                fname = os.path.basename(dest)
                self._set_status(f"Downloading {fname}…")
                self._log_write(f"[{idx}/{total}] {url}\n")

                def _progress(done: int, total_bytes: int, speed: float = 0.0, eta: float = 0.0, _idx: int = idx, _total: int = total) -> None:
                    if total_bytes > 0:
                        pct = int(done / total_bytes * 100)
                        done_str = format_bytes(done)
                        total_str = format_bytes(total_bytes)
                        speed_str = f"{format_bytes(speed)}/s" if speed > 0 else "--"
                        eta_str = f"ETA: {format_eta(eta)}" if eta > 0 else ""
                        detail_text = f"{pct}% ({done_str} / {total_str} - {speed_str} {eta_str})"
                        self.after(0, self._update_file_bar, pct, detail_text)
                    overall_pct = int((_idx - 1 + (done / max(total_bytes, 1))) / _total * 100)
                    self.after(0, self._update_overall_bar, overall_pct)

                try:
                    self._downloader.download_file(url, dest, sha, _progress)
                    self._log_write(f"  ✓ downloaded\n")
                except DownloadError as exc:
                    if "app_core" in fname:
                        self._log_write("  ⚠ Remote release asset not published yet.\n")
                        self._log_write("  📦 Packaging local codebase for dev testing…\n")
                        self._create_local_app_bundle(dest)
                        self._log_write("  ✓ Local app bundle created successfully\n")
                    elif "cuda" in fname:
                        self._log_write("  ⚠ CUDA package not published on GitHub Releases yet. Skipping for local test.\n")
                        continue
                    else:
                        self._log_write(f"  ✗ {exc}\n")
                        self.after(0, self._show_done, False)
                        return

                if dest.endswith((".zip", ".tar.gz", ".tar.xz", ".tgz")):
                    self._set_status(f"Extracting {fname}…")
                    self._log_write(f"  ↳ extracting to {os.path.dirname(dest)}\n")
                    extract_archive(dest, os.path.dirname(dest))
                    if os.path.exists(dest):
                        os.remove(dest)
                    self._log_write(f"  ✓ extracted\n")

                self.after(0, self._update_overall_bar, int(idx / total * 100))

            self._log_write("  ⚙ Saving configuration settings…\n")
            try:
                save_merged_configs(
                    install_dir,
                    gemini_api_key=self.gemini_key_var.get(),
                    ui_language=self.ui_lang_var.get(),
                    whisper_model=self.whisper_model_var.get(),
                    device=self.device_var.get(),
                    cpu_threads=self.cpu_threads_var.get(),
                )
                self._log_write("  ✓ Configuration saved\n")
            except Exception as exc:
                self._log_write(f"  ⚠ Configuration saving error: {exc}\n")

            self._set_status(self.strings["msg_creating_shortcuts"])
            self._log_write(f"{self.strings['msg_creating_shortcuts']}\n")
            try:
                create_shortcuts(install_dir, os_name)
                create_uninstaller(install_dir, os_name)
                self._log_write("  ✓ done\n")
            except Exception as exc:
                self._log_write(f"  ⚠ shortcuts: {exc}\n")

            self.after(0, self._update_overall_bar, 100)
            self._set_status(self.strings["msg_complete"])
            self.after(0, self._show_done, True)

        except Exception as exc:
            self._log_write(f"\nUnexpected error: {exc}\n")
            self.after(0, self._show_done, False)

    def _finish(self, success: bool) -> None:
        import subprocess
        if success and getattr(self, "_launch_var", None) and self._launch_var.get():
            exe = os.path.join(
                self.install_dir.get(),
                "Whisper.exe" if self.hardware.os_name == "windows" else "app_main",
            )
            bat = os.path.join(self.install_dir.get(), "Whisper.bat")
            if os.path.exists(exe):
                subprocess.Popen([exe], cwd=self.install_dir.get())
            elif os.path.exists(bat):
                subprocess.Popen([bat], shell=True, cwd=self.install_dir.get())
        self.destroy()

    # ── GUI helpers ───────────────────────────────────────────────────────────

    def _set_status(self, text: str) -> None:
        self.after(0, lambda: self._status_var.set(text) if hasattr(self, "_status_var") else None)

    def _update_file_bar(self, pct: int, detail_text: str = "") -> None:
        if hasattr(self, "_file_bar"):
            self._file_bar["value"] = pct
            self._file_pct.set(detail_text or f"{pct} %")

    def _update_overall_bar(self, pct: int) -> None:
        if hasattr(self, "_overall_bar"):
            self._overall_bar["value"] = pct
            self._overall_pct.set(f"{pct} %")

    def _log_write(self, text: str) -> None:
        def _write() -> None:
            if hasattr(self, "_log"):
                self._log.configure(state="normal")
                self._log.insert("end", text)
                self._log.see("end")
                self._log.configure(state="disabled")
        self.after(0, _write)

    def _center_window(self) -> None:
        self.update_idletasks()
        w = self.winfo_width() or 680
        h = self.winfo_height() or 460
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _default_install_dir(self) -> str:
        hw = self.hardware
        if hw.os_name == "windows":
            return os.path.join(os.environ.get("LOCALAPPDATA", "C:\\"), "WhisperUtility")
        if hw.os_name == "macos":
            return os.path.expanduser("~/Applications/WhisperUtility")
        return os.path.expanduser("~/.local/share/whisper-utility")

    def _create_local_app_bundle(self, dest_zip: str) -> None:
        import zipfile
        import platform
        import shutil
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Check if a compiled release zip already exists in dist/
        system = platform.system().lower()
        os_suffix = "win" if system == "windows" else ("mac" if system == "darwin" else "linux")
        built_zip = os.path.join(project_root, "dist", f"whisper_app_{os_suffix}.zip")
        
        if os.path.exists(built_zip):
            os.makedirs(os.path.dirname(dest_zip), exist_ok=True)
            shutil.copy2(built_zip, dest_zip)
            return

        # Fallback to source code if no compiled zip is found
        ignore_dirs = {".venv", ".git", "build", "dist", "__pycache__", ".pytest_cache", ".ruff_cache", "temp_download"}
        os.makedirs(os.path.dirname(dest_zip), exist_ok=True)
        with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(project_root):
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                for f in files:
                    if f.endswith((".pyc", ".pyo", ".log")):
                        continue
                    abs_path = os.path.join(root, f)
                    rel_path = os.path.relpath(abs_path, project_root)
                    zf.write(abs_path, rel_path)

    @staticmethod
    def _resource(filename: str) -> str:
        """Return path to a bundled resource (handles PyInstaller _MEIPASS or dev layout)."""
        base = getattr(sys, "_MEIPASS", None)
        if base:
            return os.path.join(base, filename)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        p1 = os.path.join(script_dir, filename)
        if os.path.exists(p1):
            return p1
        p2 = os.path.join(os.path.dirname(script_dir), filename)
        if os.path.exists(p2):
            return p2
        return os.path.join(script_dir, filename)
