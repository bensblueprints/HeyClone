"""Regression checks for incompatible OpenCV wheels and missing bundle data."""

import sys
import unittest
from types import SimpleNamespace
from unittest import mock

from heyclone.avatar.opencv import load_face_detector
from heyclone.doctor import check_environment
from heyclone.gpu.detect import DetectionResult


class TestOpenCVCompatibility(unittest.TestCase):
    def test_opencv5_reports_repair_instead_of_attribute_error(self):
        with mock.patch.dict(sys.modules, {"cv2": SimpleNamespace(__version__="5.0.0")}):
            with self.assertRaisesRegex(RuntimeError, "opencv-python>=4.8,<5"):
                load_face_detector()

    def test_frozen_error_requests_corrected_executable(self):
        with mock.patch.dict(sys.modules, {"cv2": SimpleNamespace(__version__="5.0.0")}), \
             mock.patch.object(sys, "frozen", True, create=True):
            with self.assertRaisesRegex(RuntimeError, "corrected HeyClone executable"):
                load_face_detector()

    def test_missing_cascade_file_is_reported(self):
        cv2 = SimpleNamespace(CascadeClassifier=mock.Mock(), data=SimpleNamespace(haarcascades="missing"))
        with mock.patch.dict(sys.modules, {"cv2": cv2}), \
             mock.patch("heyclone.avatar.opencv.Path.is_file", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "cascade data is missing"):
                load_face_detector()
        cv2.CascadeClassifier.assert_not_called()

    def test_doctor_rejects_importable_but_incompatible_opencv(self):
        with mock.patch("heyclone.doctor._module_available", side_effect=lambda name: name == "cv2"), \
             mock.patch.dict(sys.modules, {"cv2": SimpleNamespace(__version__="5.0.0")}):
            checks = check_environment(DetectionResult(gpus=[]))
        check = next(c for c in checks if c.name == "Avatar face detection")
        self.assertFalse(check.ok)
        self.assertIn("5.0.0", check.hint)
