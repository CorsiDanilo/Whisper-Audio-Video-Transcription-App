import os
from tempfile import TemporaryDirectory
import unittest
from pathlib import Path

from audio_processing import bundled_runtime_roots
from installer.gui import InstallerWizard
from installer.manifest import Manifest
from installer.platform_checks import missing_linux_runtime_dependencies
from installer.shortcut_manager import create_uninstaller
from tools import build_release


class PlatformPackagingTests(unittest.TestCase):
    def test_linux_requirements_include_pywebview_gtk_backend(self):
        requirements = Path("requirements_linux.txt").read_text(encoding="utf-8")

        self.assertRegex(requirements, r"(?im)^PyGObject(?:[<>=!~].*)?$")
        self.assertRegex(requirements, r"(?im)^pycairo(?:[<>=!~].*)?$")

    def test_linux_spec_collects_pywebview_gtk_backend(self):
        spec = Path("whisper.spec").read_text(encoding="utf-8")

        self.assertIn("collect_all('gi')", spec)
        self.assertIn("collect_all('cairo')", spec)

    def test_linux_workflow_installs_girepository_build_headers(self):
        workflow = Path(".github/workflows/build_installers.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("libgirepository-2.0-dev", workflow)
        self.assertIn('LDFLAGS="-lgmodule-2.0"', workflow)

    def test_linux_workflow_verifies_gtk_python_backend(self):
        workflow = Path(".github/workflows/build_installers.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("import gi, cairo", workflow)
        self.assertIn("from webview.platforms import gtk", workflow)

    def test_workflow_uses_bash_for_cross_platform_dependency_install(self):
        workflow = Path(".github/workflows/build_installers.yml").read_text(
            encoding="utf-8"
        )
        dependency_step = workflow.split(
            "- name: Install Python dependencies for app core", 1
        )[1].split("- name: Verify GTK Python backend (Linux)", 1)[0]

        self.assertIn("shell: bash", dependency_step)

    def test_workflow_checks_tk_without_destroying_tcl_only_interpreter(self):
        workflow = Path(".github/workflows/build_installers.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("root.eval('info patchlevel')", workflow)
        self.assertNotIn("root.destroy()", workflow)

    def test_macos_intel_build_uses_available_runner(self):
        workflow = Path(".github/workflows/build_installers.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("os: macos-15-intel", workflow)
        self.assertNotIn("os: macos-13", workflow)

    def test_manifest_uses_exact_architecture_asset(self):
        manifest = Manifest(
            {
                "components": {
                    "app_core": {
                        "macos_arm64": "arm.zip",
                        "macos_x64": "intel.zip",
                    }
                }
            }
        )

        self.assertEqual(manifest.get_app_core_url("macos", "arm64"), "arm.zip")
        self.assertEqual(manifest.get_app_core_url("macos", "x64"), "intel.zip")

    def test_manifest_allows_legacy_generic_asset_only_for_x64(self):
        manifest = Manifest({"components": {"app_core": {"linux": "linux.zip"}}})

        self.assertEqual(manifest.get_app_core_url("linux", "x64"), "linux.zip")
        self.assertIsNone(manifest.get_app_core_url("linux", "arm64"))

    def test_release_names_are_architecture_specific_on_macos(self):
        self.assertEqual(
            build_release.release_archive_name("darwin", "arm64"),
            "whisper_app_mac_arm64.zip",
        )
        self.assertEqual(
            build_release.release_archive_name("darwin", "x86_64"),
            "whisper_app_mac_x64.zip",
        )
        self.assertEqual(
            build_release.distribution_root(Path("/tmp/project"), "darwin"),
            Path("/tmp/project/dist/Whisper Utility.app"),
        )

    def test_macos_launches_the_application_bundle(self):
        self.assertEqual(
            InstallerWizard._launch_command("/opt/WhisperUtility", "macos"),
            ["open", "/opt/WhisperUtility/Whisper Utility.app"],
        )

    def test_linux_runtime_check_accepts_either_supported_webkitgtk_version(self):
        libraries = {"gtk-3", "webkit2gtk-4.0"}

        self.assertEqual(
            missing_linux_runtime_dependencies(libraries.__contains__),
            (),
        )

    def test_macos_bundle_search_includes_bundle_root_for_ffmpeg(self):
        roots = bundled_runtime_roots(
            Path("/opt/WhisperUtility/Whisper Utility.app/Contents/MacOS"), "darwin"
        )

        self.assertIn(Path("/opt/WhisperUtility/Whisper Utility.app"), roots)
        self.assertIn(Path("/opt/WhisperUtility"), roots)

    def test_installer_uses_wider_default_window_without_changing_minimum(self):
        self.assertEqual(InstallerWizard.DEFAULT_WINDOW_SIZE, (1200, 760))
        self.assertEqual(InstallerWizard.MIN_WINDOW_SIZE, (820, 560))

    def test_uninstaller_is_executable_python_script_on_unix(self):
        with TemporaryDirectory() as install_dir:
            create_uninstaller(install_dir, "linux")
            script = Path(install_dir, "uninstall.py")

            self.assertTrue(
                script.read_text(encoding="utf-8").startswith(
                    "#!/usr/bin/env python3\n"
                )
            )
            self.assertTrue(os.access(script, os.X_OK))


if __name__ == "__main__":
    unittest.main()
