"""
shortcut_manager.py - OS-aware shortcut and uninstaller creation.

Creates:
  - Desktop / menu shortcuts for the installed application.
  - An uninstall script inside the installation directory so the user can
    cleanly remove the app without a separate uninstaller binary.
"""

import os
import subprocess
import sys


APP_NAME = "Whisper Utility"


# ── Shortcuts ─────────────────────────────────────────────────────────────────

def create_shortcuts(install_dir: str, os_name: str, app_name: str = APP_NAME) -> None:
    """Create OS-appropriate application shortcuts.

    Args:
        install_dir: Root directory where the app was installed.
        os_name: One of "windows", "macos", "linux".
        app_name: Human-readable application name.
    """
    if os_name == "windows":
        _create_windows_shortcuts(install_dir, app_name)
    elif os_name == "macos":
        _create_macos_shortcuts(install_dir, app_name)
    elif os_name == "linux":
        _create_linux_shortcuts(install_dir, app_name)


def _create_windows_shortcuts(install_dir: str, app_name: str) -> None:
    exe_path = os.path.join(install_dir, "Whisper.exe")
    bat_path = os.path.join(install_dir, "Whisper.bat")
    icon_path = os.path.join(install_dir, "logo.ico")

    # Copy logo.ico if it doesn't exist in install_dir
    if not os.path.exists(icon_path):
        src_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        src_icon = os.path.join(src_root, "logo.ico")
        if os.path.exists(src_icon):
            import shutil
            try:
                shutil.copy2(src_icon, icon_path)
            except Exception:
                pass

    # If standalone compiled Whisper.exe is missing, write a Whisper.bat launcher using pythonw (no console window)
    if not os.path.exists(exe_path):
        target_path = bat_path
        cand1 = os.path.join(install_dir, ".venv", "Scripts", "pythonw.exe")
        cand2 = os.path.join(sys.prefix, "Scripts", "pythonw.exe")
        cand3 = sys.executable.replace("python.exe", "pythonw.exe")
        py_exe = sys.executable
        for cand in (cand1, cand2, cand3):
            if os.path.exists(cand):
                py_exe = cand
                break
        bat_content = f'@echo off\ncd /d "{install_dir}"\nstart "" "{py_exe}" "%~dp0app_main.py"\n'
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
    else:
        target_path = exe_path

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, f"{app_name}.lnk")

    ps_script = (
        "$WshShell = New-Object -comObject WScript.Shell; "
        f"$s = $WshShell.CreateShortcut('{shortcut_path}'); "
        f"$s.TargetPath = '{target_path}'; "
        f"$s.WorkingDirectory = '{install_dir}'; "
        f"$s.IconLocation = '{icon_path},0'; "
        "$s.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
        capture_output=True,
    )

    # Also create Start Menu entry
    start_menu = os.path.join(
        os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"
    )
    if os.path.isdir(start_menu):
        sm_shortcut = os.path.join(start_menu, f"{app_name}.lnk")
        ps_script2 = (
            "$WshShell = New-Object -comObject WScript.Shell; "
            f"$s = $WshShell.CreateShortcut('{sm_shortcut}'); "
            f"$s.TargetPath = '{target_path}'; "
            f"$s.WorkingDirectory = '{install_dir}'; "
            f"$s.IconLocation = '{icon_path},0'; "
            "$s.Save()"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script2],
            capture_output=True,
        )


def _create_macos_shortcuts(install_dir: str, app_name: str) -> None:
    """On macOS the app bundle lives in install_dir; create a Desktop alias."""
    desktop = os.path.expanduser("~/Desktop")
    alias_path = os.path.join(desktop, f"{app_name}.app")
    app_bundle = os.path.join(install_dir, f"{app_name}.app")
    if os.path.exists(app_bundle) and not os.path.exists(alias_path):
        script = f'tell application "Finder" to make alias file to POSIX file "{app_bundle}" at POSIX file "{desktop}"'
        subprocess.run(["osascript", "-e", script], capture_output=True)


def _create_linux_shortcuts(install_dir: str, app_name: str) -> None:
    executable = os.path.join(install_dir, "app_main")
    icon = os.path.join(install_dir, "logo.png")
    desktop_entry = (
        "[Desktop Entry]\n"
        f"Name={app_name}\n"
        f"Exec={executable}\n"
        f"Icon={icon}\n"
        "Type=Application\n"
        "Terminal=false\n"
        "Categories=AudioVideo;Utility;\n"
    )
    apps_dir = os.path.expanduser("~/.local/share/applications")
    os.makedirs(apps_dir, exist_ok=True)
    entry_path = os.path.join(apps_dir, "whisper-utility.desktop")
    with open(entry_path, "w", encoding="utf-8") as fh:
        fh.write(desktop_entry)
    os.chmod(entry_path, 0o755)


# ── Uninstaller ───────────────────────────────────────────────────────────────

def create_uninstaller(install_dir: str, os_name: str) -> None:
    """Write an uninstall script into *install_dir*.

    The script is platform-agnostic Python so it runs wherever Python is
    available; on Windows an additional .bat wrapper is written for
    double-click convenience.

    Args:
        install_dir: Root directory where the app was installed.
        os_name: One of "windows", "macos", "linux".
    """
    script_path = os.path.join(install_dir, "uninstall.py")
    code = """\
import os
import shutil
import sys

install_dir = os.path.dirname(os.path.abspath(__file__))

print(f"This will permanently remove Whisper Utility from:\\n  {install_dir}")
keep_config = input("Keep your settings and transcripts? [Y/n]: ").strip().lower()

try:
    if keep_config != "n":
        # Remove everything except settings/ and output/
        for item in os.listdir(install_dir):
            if item in ("settings", "output"):
                continue
            target = os.path.join(install_dir, item)
            if os.path.isdir(target):
                shutil.rmtree(target, ignore_errors=True)
            else:
                os.remove(target)
    else:
        shutil.rmtree(install_dir, ignore_errors=True)
    print("Whisper Utility has been uninstalled successfully.")
except Exception as exc:
    print(f"Uninstall error: {exc}", file=sys.stderr)
    sys.exit(1)
"""
    with open(script_path, "w", encoding="utf-8") as fh:
        fh.write(code)

    if os_name == "windows":
        bat_path = os.path.join(install_dir, "uninstall.bat")
        bat_code = f'@echo off\npython "{script_path}"\npause\n'
        with open(bat_path, "w", encoding="utf-8") as fh:
            fh.write(bat_code)
    elif os_name in ("linux", "macos"):
        os.chmod(script_path, 0o755)
