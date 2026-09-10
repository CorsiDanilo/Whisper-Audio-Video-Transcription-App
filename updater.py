"""
updater.py - Version checker and installer launcher for Whisper Utility.
"""

import os
import sys
import subprocess
from typing import Dict, Any
from packaging.version import parse as parse_version
from installer.manifest import Manifest, ManifestError

CURRENT_VERSION = "3.2.1"


def check_for_updates() -> Dict[str, Any]:
    """
    Fetch remote manifest and compare latest version against CURRENT_VERSION.
    """
    try:
        remote_manifest = Manifest.fetch_remote()
        latest_version = remote_manifest.version

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


def launch_installer_update(install_dir: str = "") -> bool:
    """
    Launch the installer script/binary in a separate process to update the application.
    """
    project_root = os.path.dirname(os.path.abspath(__file__))
    target_dir = install_dir or project_root

    installer_script = os.path.join(project_root, "installer", "installer_main.py")

    try:
        if os.path.exists(installer_script):
            subprocess.Popen([sys.executable, installer_script], cwd=project_root)
            return True
        return False
    except Exception:
        return False
