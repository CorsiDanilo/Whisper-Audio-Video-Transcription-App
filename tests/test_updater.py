import json
import unittest
from pathlib import Path
from unittest.mock import patch

import splash
import updater
from installer.manifest import DEFAULT_MANIFEST_URL


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self) -> bytes:
        return self._payload


class UpdaterTests(unittest.TestCase):
    def test_fetch_latest_release_version_reads_github_tag(self):
        with patch(
            "updater.urlopen",
            return_value=_FakeResponse({"tag_name": "v3.2.2"}),
        ):
            self.assertEqual(updater.fetch_latest_release_version(), "3.2.2")

    def test_check_for_updates_detects_release_newer_than_installed(self):
        with (
            patch.object(updater, "CURRENT_VERSION", "3.2.1"),
            patch.object(updater, "fetch_latest_release_version", return_value="3.2.2"),
        ):
            result = updater.check_for_updates()

        self.assertTrue(result["has_update"])
        self.assertEqual(result["latest_version"], "3.2.2")

    def test_check_for_updates_reports_api_failure(self):
        with patch.object(
            updater,
            "fetch_latest_release_version",
            side_effect=RuntimeError("network unavailable"),
        ):
            result = updater.check_for_updates()

        self.assertFalse(result["has_update"])
        self.assertIn("check_failed", result["status"])

    def test_manifest_version_and_urls_match_current_release(self):
        manifest_path = Path(__file__).parents[1] / "installer" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["version"], updater.CURRENT_VERSION)
        for url in manifest["components"]["app_core"].values():
            self.assertIn(f"/releases/download/v{updater.CURRENT_VERSION}/", url)
            self.assertIn("Whisper-Audio-Video-Transcription-App", url)

    def test_desktop_splash_uses_current_release_version(self):
        self.assertEqual(splash.APP_VERSION, updater.CURRENT_VERSION)

    def test_installer_manifest_comes_from_main(self):
        self.assertEqual(
            DEFAULT_MANIFEST_URL,
            "https://raw.githubusercontent.com/CorsiDanilo/Whisper-Audio-Video-Transcription-App/main/installer/manifest.json",
        )


if __name__ == "__main__":
    unittest.main()
