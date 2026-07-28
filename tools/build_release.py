"""
build_release.py - Unified cross-platform release build script for Whisper Utility.

Usage:
    python tools/build_release.py

This script:
1. Runs PyInstaller with whisper.spec to build the core standalone application.
2. Archives the compiled dist output into whisper_app_<os>.zip for distribution via GitHub Releases.
"""

import os
import platform
import shutil
import subprocess
import sys
import zipfile


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def build_release() -> None:
    print("🔨 Building Whisper Utility Release Package...")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    # 1. Run PyInstaller
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "whisper.spec"]
    print(f"Running: {' '.join(cmd)}")
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print("❌ PyInstaller build failed!", file=sys.stderr)
        sys.exit(1)

    dist_whisper = os.path.join(project_root, "dist", "Whisper")
    if not os.path.exists(dist_whisper):
        print(f"❌ Target folder {dist_whisper} not found after build!", file=sys.stderr)
        sys.exit(1)

    # Copy extra folders if needed
    settings_src = os.path.join(project_root, "settings")
    settings_dst = os.path.join(dist_whisper, "settings")
    if os.path.exists(settings_src) and not os.path.exists(settings_dst):
        shutil.copytree(settings_src, settings_dst)

    # 2. Package into zip archive
    system = platform.system().lower()
    os_suffix = "win" if system == "windows" else ("mac" if system == "darwin" else "linux")
    zip_name = os.path.join(project_root, "dist", f"whisper_app_{os_suffix}.zip")

    print(f"📦 Creating distribution archive: {zip_name}...")
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dist_whisper):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, dist_whisper)
                zf.write(abs_path, rel_path)

    print(f"🎉 Build complete!")
    print(f"Output archive: {zip_name}")


if __name__ == "__main__":
    build_release()
