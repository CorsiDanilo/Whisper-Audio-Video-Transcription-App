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
from pathlib import Path


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

    system = platform.system().lower()
    machine = platform.machine().lower()
    dist_whisper = distribution_root(project_root, system)
    if not dist_whisper.exists():
        print(f"❌ Target folder {dist_whisper} not found after build!", file=sys.stderr)
        sys.exit(1)

    # Copy extra folders if needed
    settings_src = os.path.join(project_root, "settings")
    settings_dst = dist_whisper / "settings"
    if os.path.exists(settings_src) and not settings_dst.exists():
        shutil.copytree(settings_src, settings_dst)

    # 2. Package into zip archive
    zip_name = os.path.join(project_root, "dist", release_archive_name(system, machine))

    print(f"📦 Creating distribution archive: {zip_name}...")
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dist_whisper):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, dist_whisper)
                zf.write(abs_path, rel_path)

    print("🎉 Build complete!")
    print(f"Output archive: {zip_name}")


def distribution_root(project_root: str | Path, system: str) -> Path:
    """Return the PyInstaller output consumed by the release archiver."""
    dist_dir = Path(project_root) / "dist"
    return dist_dir / "Whisper Utility.app" if system == "darwin" else dist_dir / "Whisper"


def release_archive_name(system: str, machine: str) -> str:
    """Return the release archive name for the current platform and CPU."""
    if system == "darwin":
        arch = "arm64" if machine.lower() in ("arm64", "aarch64") else "x64"
        return f"whisper_app_mac_{arch}.zip"
    os_suffix = "win" if system == "windows" else "linux"
    return f"whisper_app_{os_suffix}.zip"


if __name__ == "__main__":
    build_release()
