"""Regression coverage for WhatsApp audio filename detection."""

from pathlib import Path
import unittest

import audio_processing


class WhatsAppAudioFileTests(unittest.TestCase):
    def test_accepts_opus_extension_case_insensitively(self):
        self.assertTrue(audio_processing.is_whatsapp_audio_file("voice.opus"))
        self.assertTrue(audio_processing.is_whatsapp_audio_file("VOICE.OPUS"))
        self.assertTrue(audio_processing.is_whatsapp_audio_file(Path("uploads/voice.OpUs")))

    def test_rejects_nearby_or_non_opus_extensions(self):
        for file_path in (
            "voice",
            ".opus",
            "voice.opus.mp3",
            "voice.opus ",
            "voice.ogg",
        ):
            with self.subTest(file_path=file_path):
                self.assertFalse(audio_processing.is_whatsapp_audio_file(file_path))

    def test_invalid_path_types_follow_splitext_contract(self):
        for file_path in (None, 42):
            with self.subTest(file_path=file_path):
                with self.assertRaises(TypeError):
                    audio_processing.is_whatsapp_audio_file(file_path)

        self.assertFalse(audio_processing.is_whatsapp_audio_file(b"voice.opus"))


if __name__ == "__main__":
    unittest.main()
