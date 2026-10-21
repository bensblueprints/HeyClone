"""Tests for VRAM tier classification and preset selection."""

import unittest

from heyclone.config import get_preset
from heyclone.gpu.detect import GpuInfo, VramTier, classify_vram, detect_gpus


class TestClassifyVram(unittest.TestCase):
    def test_low_tier(self):
        self.assertEqual(classify_vram(2048), VramTier.LOW)  # 2 GB
        self.assertEqual(classify_vram(4096), VramTier.LOW)  # 4 GB

    def test_8gb_tier(self):
        self.assertEqual(classify_vram(6144), VramTier.GB8)   # 6 GB
        self.assertEqual(classify_vram(8192), VramTier.GB8)   # 8 GB
        self.assertEqual(classify_vram(11264), VramTier.GB8)  # 11 GB

    def test_16gb_tier(self):
        self.assertEqual(classify_vram(12288), VramTier.GB16)  # 12 GB
        self.assertEqual(classify_vram(16384), VramTier.GB16)  # 16 GB
        self.assertEqual(classify_vram(23552), VramTier.GB16)  # 23 GB

    def test_32gb_tier(self):
        self.assertEqual(classify_vram(24576), VramTier.GB32)  # 24 GB
        self.assertEqual(classify_vram(32768), VramTier.GB32)  # 32 GB
        self.assertEqual(classify_vram(49152), VramTier.GB32)  # 48 GB


class TestGpuInfo(unittest.TestCase):
    def test_tier_property(self):
        gpu = GpuInfo(0, "Test GPU", 16384, "nvml", is_cuda=True)
        self.assertEqual(gpu.total_gb, 16.0)
        self.assertEqual(gpu.tier, VramTier.GB16)

    def test_32gb_gpu_uses_32gb_preset(self):
        gpu = GpuInfo(0, "RTX 4090", 24576, "nvml", is_cuda=True)
        preset = get_preset(gpu.tier)
        self.assertEqual(preset.tier, VramTier.GB32)
        self.assertFalse(preset.offload_layers)
        self.assertEqual(preset.face_resolution, (512, 512))

    def test_8gb_gpu_offloads(self):
        gpu = GpuInfo(0, "RTX 3060", 8192, "nvml", is_cuda=True)
        preset = get_preset(gpu.tier)
        self.assertEqual(preset.tier, VramTier.GB8)
        self.assertTrue(preset.offload_layers)
        self.assertEqual(preset.model_precision, "fp16")


class TestDetectGpus(unittest.TestCase):
    def test_detect_returns_result(self):
        result = detect_gpus()
        # On any machine (even CPU-only) this must return a valid result.
        self.assertIsNotNone(result)
        self.assertIsInstance(result.tier, VramTier)

    def test_empty_result_is_none_tier(self):
        # Simulated: no GPUs means NONE tier, not a crash.
        from heyclone.gpu.detect import DetectionResult

        result = DetectionResult(gpus=[])
        self.assertEqual(result.tier, VramTier.NONE)
        self.assertIsNone(result.best_gpu)
        self.assertFalse(result.has_cuda)


if __name__ == "__main__":
    unittest.main()
