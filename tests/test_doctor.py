"""Tests for the environment readiness checks (no model download required)."""

import unittest
from unittest import mock

from heyclone.doctor import Check, check_environment
from heyclone.gpu.detect import DetectionResult, GpuBackend, GpuInfo


class TestCheckEnvironment(unittest.TestCase):
    def test_all_missing_on_bare_cpu(self):
        with mock.patch("heyclone.doctor._module_available", return_value=False), \
             mock.patch.dict("os.environ", {}, clear=True):
            checks = check_environment(detection=DetectionResult(gpus=[]))
        self.assertEqual(len(checks), 6)
        self.assertTrue(all(isinstance(c, Check) for c in checks))
        gpu_check = next(c for c in checks if c.name == "GPU (CUDA)")
        self.assertFalse(gpu_check.ok)
        self.assertEqual(gpu_check.status, "none")
        driver_check = next(c for c in checks if c.name == "GPU driver")
        self.assertFalse(driver_check.ok)
        self.assertEqual(driver_check.status, "missing")

    def test_cuda_gpu_reported_ok(self):
        gpu = GpuInfo(0, "RTX 4090", 24576, GpuBackend.NVML, is_cuda=True)
        det = DetectionResult(gpus=[gpu], backend=GpuBackend.NVML)
        with mock.patch("heyclone.doctor._module_available", return_value=False), \
             mock.patch.dict("os.environ", {}, clear=True):
            checks = check_environment(detection=det)
        gpu_check = next(c for c in checks if c.name == "GPU (CUDA)")
        self.assertTrue(gpu_check.ok)
        self.assertIn("32gb", gpu_check.status)
        driver_check = next(c for c in checks if c.name == "GPU driver")
        self.assertTrue(driver_check.ok)
        self.assertEqual(driver_check.status, "nvml")

    def test_full_stack_reports_ok(self):
        gpu = GpuInfo(0, "RTX 3090", 24576, GpuBackend.NVML, is_cuda=True)
        det = DetectionResult(gpus=[gpu], backend=GpuBackend.NVML)
        with mock.patch("heyclone.doctor._module_available", return_value=True), \
             mock.patch("heyclone.doctor._torch_cuda_available", return_value=True), \
             mock.patch.dict("os.environ", {"LIPSYNC_DIR": "/tmp/lipsync"}), \
             mock.patch("heyclone.doctor.Path.is_file", return_value=True):
            checks = check_environment(detection=det)
        self.assertTrue(all(c.ok for c in checks))


if __name__ == "__main__":
    unittest.main()
