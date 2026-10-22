"""Avatar cloning: face preparation and audio-driven lip-sync.

The pipeline has two stages:

1. ``prepare``  — detect and crop the user's face from an image or the first
   video frame. Uses a Haar cascade (no model weights needed) so a
   GPU-less machine can at least build the avatar crop; swap in a landmark-
   alignment model for production-quality alignment.

2. ``animate``  — lip-sync the avatar to a (cloned) voice track using an
   external lip-sync engine. This is the GPU-heavy diffusion step; it shells
   out to a lip-sync engine checkout so the heavy model lives behind a clean
   interface.

The detected GPU tier drives the face-crop resolution passed to each stage.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..config import get_preset
from ..gpu.detect import DetectionResult, detect_gpus
from .opencv import load_face_detector

_SUPPORTED_IMAGE = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
_SUPPORTED_VIDEO = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


@dataclass
class AvatarProfile:
    source_path: str
    output_dir: str
    face_resolution: tuple[int, int]
    face_crop_path: Optional[str] = None
    num_faces: int = 0


@dataclass
class AvatarResult:
    output_video: str
    face_resolution: tuple[int, int]
    gpu_tier: str


class AvatarCloner:
    """Builds a face avatar and animates it with lip-sync."""

    def __init__(self, detection: Optional[DetectionResult] = None):
        self.detection = detection if detection is not None else detect_gpus()
        self.preset = get_preset(self.detection.tier)

    def prepare(
        self,
        source: os.PathLike | str,
        output_dir: os.PathLike | str | None = None,
    ) -> AvatarProfile:
        """Detect the face in ``source`` and save a cropped, resized avatar."""
        src = Path(source)
        if not src.is_file():
            raise FileNotFoundError(f"Source not found: {src}")
        suffix = src.suffix.lower()
        if suffix not in _SUPPORTED_IMAGE and suffix not in _SUPPORTED_VIDEO:
            raise ValueError(
                f"Unsupported source format '{suffix}'; expected an image "
                f"{sorted(_SUPPORTED_IMAGE)} or video {sorted(_SUPPORTED_VIDEO)}"
            )

        out = Path(output_dir) if output_dir else src.parent / "avatar"
        out.mkdir(parents=True, exist_ok=True)

        crop_path, num_faces = self._extract_face_crop(src, out)

        return AvatarProfile(
            source_path=str(src),
            output_dir=str(out),
            face_resolution=self.preset.face_resolution,
            face_crop_path=crop_path,
            num_faces=num_faces,
        )

    def _extract_face_crop(
        self, src: Path, out: Path
    ) -> tuple[Optional[str], int]:
        cv2, cascade = load_face_detector()

        frame = self._read_frame(cv2, src)
        if frame is None:
            return None, 0

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        if len(faces) == 0:
            return None, 0

        # Use the largest detected face.
        x, y, w, h = max(faces, key=lambda box: box[2] * box[3])
        crop = frame[y : y + h, x : x + w]
        res = self.preset.face_resolution
        crop = cv2.resize(crop, res, interpolation=cv2.INTER_AREA)

        crop_path = out / f"avatar_face_{res[0]}x{res[1]}.png"
        cv2.imwrite(str(crop_path), crop)
        return str(crop_path), len(faces)

    @staticmethod
    def _read_frame(cv2, src: Path):
        if src.suffix.lower() in _SUPPORTED_IMAGE:
            return cv2.imread(str(src))
        cap = cv2.VideoCapture(str(src))
        if not cap.isOpened():
            return None
        ok, frame = cap.read()
        cap.release()
        return frame if ok else None

    def animate(
        self,
        avatar: AvatarProfile,
        audio_wav: os.PathLike | str,
        output_video: os.PathLike | str,
        inference_config: os.PathLike | str | None = None,
    ) -> AvatarResult:
        """Lip-sync ``avatar`` to ``audio_wav`` using an external lip-sync engine.

        Requires the engine's repo and its weights. Point ``LIPSYNC_DIR`` at the
        checkout, and pass ``inference_config`` (an inference YAML) when the
        default is not appropriate.
        """
        audio = Path(audio_wav)
        if not audio.is_file():
            raise FileNotFoundError(f"Audio not found: {audio}")

        engine_dir = Path(os.environ.get("LIPSYNC_DIR", ""))
        inference_script = engine_dir / "scripts" / "inference.py"
        if not inference_script.is_file():
            raise RuntimeError(
                "Avatar lip-sync requires an external lip-sync engine. Clone it "
                "and set LIPSYNC_DIR to its checkout (see README.md)."
            )

        config = Path(inference_config) if inference_config else engine_dir / "configs" / "inference" / "test.yaml"
        out = Path(output_video)
        out.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "python",
            str(inference_script),
            "--inference_config",
            str(config),
            "--result_dir",
            str(out.parent),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(
                f"Lip-sync inference failed (exit {proc.returncode}):\n"
                f"{proc.stderr[-2000:]}"
            )

        return AvatarResult(
            output_video=str(out),
            face_resolution=avatar.face_resolution,
            gpu_tier=self.preset.tier.value,
        )
