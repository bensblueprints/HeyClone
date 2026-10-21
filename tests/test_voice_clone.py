"""Tests for the voice-cloning module (no model download required)."""

import unittest
from unittest import mock

from heyclone.gpu.detect import DetectionResult
from heyclone.voice.clone import VoiceCloner


class TestVoiceClonerConfig(unittest.TestCase):
    def test_cpu_detection_disables_gpu(self):
        cloner = VoiceCloner(detection=DetectionResult(gpus=[]))
        self.assertFalse(cloner.use_gpu)
        self.assertEqual(cloner.preset.audio_sample_rate, 16000)

    def test_cuda_detection_enables_gpu(self):
        from heyclone.gpu.detect import GpuInfo, GpuBackend

        gpu = GpuInfo(0, "RTX 4090", 24576, GpuBackend.NVML, is_cuda=True)
        cloner = VoiceCloner(detection=DetectionResult(gpus=[gpu], backend=GpuBackend.NVML))
        self.assertTrue(cloner.use_gpu)
        self.assertEqual(cloner.preset.audio_sample_rate, 24000)


class TestVoiceClonerValidation(unittest.TestCase):
    def test_missing_reference_raises_before_model_load(self):
        cloner = VoiceCloner(detection=DetectionResult(gpus=[]))
        with self.assertRaises(FileNotFoundError):
            cloner.clone_voice("does_not_exist.wav", "hello", "out.wav")

    def test_empty_text_raises(self):
        cloner = VoiceCloner(detection=DetectionResult(gpus=[]))
        with self.assertRaises(ValueError):
            cloner.clone_voice("ref.wav", "   ", "out.wav")

    def test_missing_tts_package_raises_clear_error(self):
        import os
        import tempfile

        cloner = VoiceCloner(detection=DetectionResult(gpus=[]))
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            # Simulate the TTS package being absent.
            with mock.patch("builtins.__import__", side_effect=ImportError("no TTS")):
                with self.assertRaises(RuntimeError) as ctx:
                    cloner.clone_voice(path, "hello", "out.wav")
        finally:
            os.unlink(path)
        self.assertIn("TTS", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
