"""Tests for the avatar-cloning module (no model download required)."""

import os
import tempfile
import unittest
from unittest import mock

from heyclone.avatar.clone import AvatarCloner
from heyclone.gpu.detect import DetectionResult, GpuBackend, GpuInfo, VramTier


def _make_cloner(vram_mb: int) -> AvatarCloner:
    gpu = GpuInfo(0, "Test GPU", vram_mb, GpuBackend.NVML, is_cuda=True)
    return AvatarCloner(detection=DetectionResult(gpus=[gpu], backend=GpuBackend.NVML))


class TestAvatarClonerConfig(unittest.TestCase):
    def test_face_resolution_follows_tier(self):
        self.assertEqual(_make_cloner(8192).preset.face_resolution, (256, 256))
        self.assertEqual(_make_cloner(24576).preset.face_resolution, (512, 512))


class TestAvatarClonerValidation(unittest.TestCase):
    def test_missing_source_raises(self):
        cloner = _make_cloner(8192)
        with self.assertRaises(FileNotFoundError):
            cloner.prepare("does_not_exist.png")

    def test_unsupported_format_raises(self):
        cloner = _make_cloner(8192)
        fd, path = tempfile.mkstemp(suffix=".txt")
        os.close(fd)
        try:
            with self.assertRaises(ValueError):
                cloner.prepare(path)
        finally:
            os.unlink(path)

    def test_missing_opencv_raises_clear_error(self):
        cloner = _make_cloner(8192)
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            with mock.patch("builtins.__import__", side_effect=ImportError("no cv2")):
                with self.assertRaises(RuntimeError) as ctx:
                    cloner.prepare(path)
        finally:
            os.unlink(path)
        self.assertIn("opencv-python", str(ctx.exception))


class TestAvatarAnimateValidation(unittest.TestCase):
    def test_missing_audio_raises_before_engine_check(self):
        cloner = _make_cloner(8192)
        from heyclone.avatar.clone import AvatarProfile

        avatar = AvatarProfile("x.png", ".", (256, 256))
        with self.assertRaises(FileNotFoundError):
            cloner.animate(avatar, "missing.wav", "out.mp4")


if __name__ == "__main__":
    unittest.main()
