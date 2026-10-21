"""Zero-shot voice cloning via a pretrained text-to-speech engine.

A short reference clip of the user's voice is fed to the TTS engine as a
*speaker sample*; the engine then synthesizes arbitrary text in that voice. The
GPU tier detected earlier decides whether to run on CUDA and what sample rate to
target.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..config import get_preset
from ..gpu.detect import DetectionResult, detect_gpus

_SUPPORTED_AUDIO = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}


@dataclass
class VoiceCloneResult:
    output_path: str
    model_name: str
    gpu_used: bool
    sample_rate: int


class VoiceCloner:
    """Clones a reference voice and synthesizes speech with it."""

    MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"

    def __init__(self, detection: Optional[DetectionResult] = None):
        self.detection = detection if detection is not None else detect_gpus()
        self.preset = get_preset(self.detection.tier)
        self.use_gpu = self.detection.has_cuda
        self._tts = None

    def _load(self):
        if self._tts is not None:
            return self._tts
        try:
            from TTS.api import TTS  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Voice cloning requires the 'TTS' package. "
                "Install it with:  pip install TTS"
            ) from exc
        self._tts = TTS(self.MODEL_NAME, gpu=self.use_gpu)
        return self._tts

    @staticmethod
    def _validate_reference(reference_wav: os.PathLike | str) -> Path:
        ref = Path(reference_wav)
        if not ref.is_file():
            raise FileNotFoundError(f"Reference audio not found: {ref}")
        if ref.suffix.lower() not in _SUPPORTED_AUDIO:
            raise ValueError(
                f"Unsupported reference audio format '{ref.suffix}'; "
                f"expected one of {sorted(_SUPPORTED_AUDIO)}"
            )
        return ref

    def clone_voice(
        self,
        reference_wav: os.PathLike | str,
        text: str,
        output_wav: os.PathLike | str,
        language: str = "en",
    ) -> VoiceCloneResult:
        """Synthesize ``text`` in the voice of ``reference_wav``.

        ``reference_wav`` should be a clean 6-15 second clip of the target
        speaker. The engine is zero-shot: no fine-tuning is required.
        """
        if not text or not text.strip():
            raise ValueError("text must be non-empty")
        ref = self._validate_reference(reference_wav)
        out = Path(output_wav)
        out.parent.mkdir(parents=True, exist_ok=True)

        tts = self._load()
        tts.tts_to_file(
            text=text.strip(),
            speaker_wav=str(ref),
            language=language,
            file_path=str(out),
        )

        return VoiceCloneResult(
            output_path=str(out),
            model_name=self.MODEL_NAME,
            gpu_used=self.use_gpu,
            sample_rate=self.preset.audio_sample_rate,
        )
