"""Validate the OpenCV API and cascade data used by avatar preparation."""

import sys
from pathlib import Path


def load_face_detector():
    remedy = (
        "Install the corrected HeyClone executable."
        if getattr(sys, "frozen", False)
        else 'Run: python -m pip install --upgrade "opencv-python>=4.8,<5"'
    )
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(f"Avatar face detection requires opencv-python 4.x. {remedy}") from exc

    cascade_dir = getattr(getattr(cv2, "data", None), "haarcascades", None)
    if not callable(getattr(cv2, "CascadeClassifier", None)) or not cascade_dir:
        version = getattr(cv2, "__version__", "unknown")
        raise RuntimeError(
            f"OpenCV {version} lacks the Haar cascade API/data required by HeyClone. {remedy}"
        )
    cascade_path = Path(cascade_dir) / "haarcascade_frontalface_default.xml"
    if not cascade_path.is_file():
        raise RuntimeError(f"OpenCV face cascade data is missing. {remedy}")
    cascade = cv2.CascadeClassifier(str(cascade_path))
    if cascade.empty():
        raise RuntimeError(f"OpenCV face cascade could not be loaded. {remedy}")
    return cv2, cascade
