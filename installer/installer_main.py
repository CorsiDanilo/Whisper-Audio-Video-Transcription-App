"""
installer_main.py - Entry point for the Whisper Utility Smart Installer.

Run directly:
    python installer/installer_main.py

Compile to standalone binary:
    pyinstaller --onefile --noconfirm --name WhisperUtilitySetup installer/installer_main.py
"""

import os
import sys

# Ensure project root is in sys.path when running script directly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from installer.gui import InstallerWizard


def main() -> None:
    app = InstallerWizard()
    app.mainloop()


if __name__ == "__main__":
    main()
