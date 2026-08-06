"""
installer_main.py - Entry point for the Whisper Utility Smart Installer.

Run directly:
    python installer/installer_main.py

Compile to standalone directory package (prevents false-positive AV blocks):
    pyinstaller --onedir --noconsole --noupx --icon logo.ico --noconfirm --name WhisperUtilitySetup installer/installer_main.py
"""

import os
import sys

# Ensure project root is in sys.path when running script directly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)


from installer.splash import InstallerSplashScreen

_splash = InstallerSplashScreen()
_splash.update_status("init", 15)

from installer.hardware_detector import detect_hardware  # noqa: F401  (warms up hw detection module)
_splash.update_status("hw", 45)

from installer.gui import InstallerWizard
_splash.update_status("gui", 80)


def main() -> None:
    _splash.update_status("ready", 100)
    _splash.close()
    app = InstallerWizard()
    app.mainloop()


if __name__ == "__main__":
    main()
