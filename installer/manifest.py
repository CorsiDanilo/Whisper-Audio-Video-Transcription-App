"""
manifest.py - Fetches and parses the remote installer manifest (manifest.json).

The manifest lives on GitHub Releases and tells the installer which URLs to
use for each OS/arch combination.  It is fetched once at startup so the
installer binary itself never needs to be rebuilt for URL-only changes.

Example manifest structure:
    {
        "version": "1.0.0",
        "components": {
            "app_core": {
                "windows":    "https://...",
                "macos_arm64": "https://...",
                "linux":      "https://..."
            },
            "ffmpeg": {
                "windows_x64": "https://www.gyan.dev/...",
                "macos_arm64": "https://evermeet.cx/...",
                "linux_x64":   "https://johnvansickle.com/..."
            },
            "cuda_libs": {
                "windows_nvidia": "https://..."
            }
        },
        "sha256": {
            "windows_x64": "abc123..."
        }
    }
"""

import json
import urllib.request
from typing import Any, Dict, Optional

from version import REPOSITORY

DEFAULT_MANIFEST_URL = (
    f"https://raw.githubusercontent.com/{REPOSITORY}/main/installer/manifest.json"
)


class ManifestError(Exception):
    """Raised when the remote manifest cannot be fetched or parsed."""


class Manifest:
    """Parsed view of the remote installer manifest."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.data = data
        self.version: str = data.get("version", "1.0.0")
        self._components: Dict[str, Dict[str, str]] = data.get("components", {})
        self._sha256: Dict[str, str] = data.get("sha256", {})

    # ── factory ───────────────────────────────────────────────────────────────

    @classmethod
    def fetch_remote(cls, url: str = DEFAULT_MANIFEST_URL, timeout: int = 10) -> "Manifest":
        """Download and parse the remote manifest JSON.

        Raises:
            ManifestError: If the network request fails or JSON is invalid.
        """
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "WhisperUtilityInstaller/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data: Dict[str, Any] = json.loads(resp.read().decode("utf-8"))
                return cls(data)
        except Exception as exc:
            raise ManifestError(f"Failed to fetch manifest from {url}: {exc}") from exc

    @classmethod
    def from_file(cls, path: str) -> "Manifest":
        """Load a manifest from a local JSON file (useful for offline testing)."""
        with open(path, encoding="utf-8") as fh:
            return cls(json.load(fh))

    # ── helpers ───────────────────────────────────────────────────────────────

    def get_ffmpeg_url(self, os_name: str, arch: str) -> Optional[str]:
        """Return the FFmpeg download URL for the given OS and architecture.

        The manifest key is ``<os_name>_<arch>``, e.g. ``windows_x64``.
        """
        key = f"{os_name}_{arch}"
        return self._components.get("ffmpeg", {}).get(key)

    def get_component_url(self, component: str, key: str) -> Optional[str]:
        """Generic lookup: ``manifest.get_component_url("app_core", "linux")``."""
        return self._components.get(component, {}).get(key)

    def get_sha256(self, key: str) -> Optional[str]:
        """Return the expected SHA-256 for *key*, or None if not listed."""
        return self._sha256.get(key)
