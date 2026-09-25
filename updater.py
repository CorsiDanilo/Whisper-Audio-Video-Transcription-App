"""
updater.py - Version checker and installer launcher for Whisper Utility.
"""

import json
import os
import subprocess
import sys
import webbrowser
from typing import Dict, Any, Tuple
from urllib.request import Request, urlopen

from packaging.version import parse as parse_version

from version import APP_VERSION, REPOSITORY

CURRENT_VERSION = APP_VERSION
RELEASES_URL = f"https://github.com/{REPOSITORY}/releases/latest"
LATEST_RELEASE_API_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"


def fetch_latest_release_version(timeout: int = 10) -> str:
    """Return the latest published GitHub release version without its ``v`` prefix."""
    request = Request(
        LATEST_RELEASE_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "WhisperUtilityUpdater/1.0",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    tag_name = payload.get("tag_name")
    if not isinstance(tag_name, str) or not tag_name.strip():
        raise ValueError("GitHub latest release response has no tag_name")

    tag_name = tag_name.strip()
    return tag_name[1:] if tag_name.startswith("v") else tag_name


def check_for_updates() -> Dict[str, Any]:
    """
    Fetch the latest GitHub release and compare it against CURRENT_VERSION.
    """
    try:
        latest_version = fetch_latest_release_version()

        has_update = parse_version(latest_version) > parse_version(CURRENT_VERSION)
        return {
            "has_update": has_update,
            "latest_version": latest_version,
            "current_version": CURRENT_VERSION,
            "status": "update_available" if has_update else "up_to_date",
        }
    except Exception as exc:
        return {
            "has_update": False,
            "latest_version": CURRENT_VERSION,
            "current_version": CURRENT_VERSION,
            "status": f"check_failed: {exc}",
        }


def launch_installer_update(install_dir: str = "", force: bool = False) -> Tuple[bool, str]:
    """
    Launch the installer script/binary in a separate detached process.
    Supports development/source environments and frozen standalone packages.
    Returns (success: bool, detail: str).
    """
    is_frozen = getattr(sys, "frozen", False)

    if is_frozen:
        app_dir = os.path.dirname(os.path.abspath(sys.executable))
        candidates = [
            os.path.join(app_dir, "WhisperUtilitySetup.exe"),
            os.path.join(app_dir, "WhisperUtilitySetup_Windows.exe"),
            os.path.join(os.path.dirname(app_dir), "WhisperUtilitySetup.exe"),
            os.path.join(os.path.dirname(app_dir), "WhisperUtilitySetup_Windows.exe"),
            os.path.join(app_dir, "installer", "WhisperUtilitySetup.exe"),
            os.path.join(app_dir, "installer", "WhisperUtilitySetup_Windows.exe"),
        ]
        for cand in candidates:
            if os.path.exists(cand):
                try:
                    creationflags = (
                        subprocess.CREATE_NEW_PROCESS_GROUP
                        if sys.platform == "win32"
                        else 0
                    )
                    subprocess.Popen(
                        [cand],
                        cwd=os.path.dirname(cand),
                        creationflags=creationflags,
                        close_fds=True,
                    )
                    return True, "installer_started"
                except Exception as exc:
                    return False, f"exec_failed: {exc}"

        # If no standalone setup executable is bundled, fallback to opening GitHub releases
        try:
            webbrowser.open(RELEASES_URL)
            return True, "opened_browser"
        except Exception as exc:
            return False, f"browser_failed: {exc}"

    # Running from Python source code
    project_root = os.path.dirname(os.path.abspath(__file__))
    installer_script = os.path.join(project_root, "installer", "installer_main.py")

    if not os.path.exists(installer_script):
        return False, "installer_script_not_found"

    # Select Python executable: on Windows, prefer pythonw.exe if available in the same dir to prevent console popup
    py_exe = sys.executable
    if sys.platform == "win32":
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if os.path.exists(pythonw):
            py_exe = pythonw

    try:
        creationflags = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            if sys.platform == "win32"
            else 0
        )
        subprocess.Popen(
            [py_exe, installer_script],
            cwd=project_root,
            creationflags=creationflags,
            close_fds=True,
        )
        return True, "installer_started"
    except Exception as exc:
        return False, f"launch_failed: {exc}"
