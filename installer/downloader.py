"""
downloader.py - Threaded HTTP downloader with SHA-256 checksum verification.

Usage:
    downloader = FileDownloader()
    downloader.download_file(url, target_path, expected_sha256, progress_callback)
"""

import hashlib
import os
import time
import urllib.request
from typing import Callable, Optional


class DownloadError(Exception):
    """Raised when a download fails or a checksum does not match."""


def format_bytes(num_bytes: float) -> str:
    """Format bytes count into human-readable string (B, KB, MB, GB)."""
    if num_bytes >= 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"
    elif num_bytes >= 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    elif num_bytes >= 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{int(num_bytes)} B"


def format_eta(seconds: float) -> str:
    """Format ETA seconds into human-readable string."""
    if seconds <= 0 or seconds > 86400:
        return "--"
    secs = int(seconds)
    if secs < 60:
        return f"{secs}s"
    mins = secs // 60
    rem_secs = secs % 60
    return f"{mins}m {rem_secs}s"


class FileDownloader:
    """Downloads a file from a URL and optionally verifies its SHA-256 hash."""

    MAX_RETRIES = 3

    def verify_checksum(self, file_path: str, expected_sha256: Optional[str]) -> bool:
        """Return True if the file matches expected_sha256, or if expected_sha256 is None."""
        if not expected_sha256:
            return True
        if not os.path.exists(str(file_path)):
            return False
        hasher = hashlib.sha256()
        with open(str(file_path), "rb") as fh:
            for chunk in iter(lambda: fh.read(65_536), b""):
                hasher.update(chunk)
        return hasher.hexdigest().lower() == expected_sha256.lower()

    def download_file(
        self,
        url: str,
        target_path: str,
        expected_sha256: Optional[str] = None,
        progress_callback: Optional[Callable[..., None]] = None,
    ) -> None:
        """
        Download *url* to *target_path*.

        Args:
            url: Remote URL to fetch.
            target_path: Local file path to write to.
            expected_sha256: If given, the file is deleted and DownloadError is
                raised when the hash does not match.
            progress_callback: Called as ``progress_callback(downloaded, total, speed, eta)``
                where *total* may be 0 if Content-Length is unknown.

        Raises:
            DownloadError: On network error or checksum mismatch.
        """
        parent = os.path.dirname(target_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        last_exc: Exception = Exception("Unknown error")
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self._fetch(url, target_path, progress_callback)
                break
            except Exception as exc:
                last_exc = exc
                if os.path.exists(target_path):
                    os.remove(target_path)
                if attempt == self.MAX_RETRIES:
                    raise DownloadError(f"Download failed after {self.MAX_RETRIES} attempts for {url}: {exc}") from exc

        if expected_sha256 and not self.verify_checksum(target_path, expected_sha256):
            os.remove(target_path)
            raise DownloadError(f"Checksum mismatch for {url}")

    # ── private ──────────────────────────────────────────────────────────────

    def _fetch(
        self,
        url: str,
        target_path: str,
        progress_callback: Optional[Callable[..., None]],
    ) -> None:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "WhisperUtilityInstaller/1.0"},
        )
        start_time = time.time()
        with urllib.request.urlopen(req) as resp, open(target_path, "wb") as fh:
            total_size = int(resp.headers.get("Content-Length", 0) or 0)
            downloaded = 0
            block = 65_536
            while True:
                buffer = resp.read(block)
                if not buffer:
                    break
                downloaded += len(buffer)
                fh.write(buffer)
                if progress_callback:
                    elapsed = time.time() - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0.0
                    rem_bytes = max(0, total_size - downloaded)
                    eta = rem_bytes / speed if speed > 0 and total_size > 0 else 0.0
                    try:
                        progress_callback(downloaded, total_size, speed, eta)
                    except TypeError:
                        progress_callback(downloaded, total_size)
