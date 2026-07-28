"""
hardware_detector.py - Detects OS, architecture, and GPU capabilities.

Produces a HardwareInfo dataclass used by the installer to decide which
components (FFmpeg build, CUDA DLLs) to download.
"""

import platform
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class HardwareInfo:
    """Collected system information used to drive installer decisions."""

    os_name: str          # "windows" | "macos" | "linux"
    arch: str             # "x64" | "arm64"
    has_nvidia_gpu: bool  # True if nvidia-smi is present and returns a GPU name
    is_apple_silicon: bool  # True only on macOS arm64
    gpu_name: Optional[str] = None  # Human-readable GPU name, or None


def detect_hardware() -> HardwareInfo:
    """Inspect the current system and return a HardwareInfo instance."""
    system = platform.system().lower()
    if system == "darwin":
        os_name = "macos"
    elif system == "windows":
        os_name = "windows"
    else:
        os_name = "linux"

    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
    is_apple_silicon = (os_name == "macos" and arch == "arm64")

    has_nvidia = False
    gpu_name: Optional[str] = None

    if shutil.which("nvidia-smi"):
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=gpu_name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0 and res.stdout.strip():
                has_nvidia = True
                gpu_name = res.stdout.strip().split("\n")[0].strip()
        except Exception:
            # nvidia-smi found but failed — treat as no GPU
            pass

    return HardwareInfo(
        os_name=os_name,
        arch=arch,
        has_nvidia_gpu=has_nvidia,
        is_apple_silicon=is_apple_silicon,
        gpu_name=gpu_name,
    )
