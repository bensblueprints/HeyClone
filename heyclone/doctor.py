"""Environment readiness checks for the cloning stages.

Tells the user exactly which dependencies are present/missing so they can set up
a GPU machine correctly. Pure checks — no model inference, so it runs anywhere.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .gpu.detect import DetectionResult, GpuBackend, detect_gpus


@dataclass
class Check:
    name: str
    ok: bool
    status: str
    hint: str = ""


def _module_available(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


def _torch_cuda_available() -> bool:
    if not _module_available("torch"):
        return False
    try:
        import torch  # type: ignore

        return torch.cuda.is_available()
    except Exception:
        return False


def check_environment(detection: Optional[DetectionResult] = None) -> list[Check]:
    det = detection if detection is not None else detect_gpus()
    checks: list[Check] = []

    # GPU / VRAM
    if det.has_cuda:
        gpu = det.best_gpu
        checks.append(
            Check("GPU (CUDA)", True, f"{gpu.name} - {gpu.total_gb:.2f} GB ({gpu.tier.value})")
        )
    elif det.gpus:
        gpu = det.best_gpu
        checks.append(
            Check(
                "GPU (CUDA)",
                False,
                f"{gpu.name} ({gpu.total_gb:.2f} GB) - not CUDA",
                "avatar lip-sync requires a CUDA GPU",
            )
        )
    else:
        checks.append(Check("GPU (CUDA)", False, "none", "no discrete GPU detected"))

    # GPU driver presence, inferred from the backend that detected the GPU.
    # (Importability of pynvml does NOT imply a driver is present.)
    gpu_driver_backends = {GpuBackend.NVML, GpuBackend.NVIDIA_SMI, GpuBackend.TORCH}
    driver_ok = det.backend in gpu_driver_backends
    checks.append(
        Check(
            "GPU driver",
            driver_ok,
            det.backend.value if driver_ok else "missing",
            "" if driver_ok else "install the GPU driver",
        )
    )

    # torch + CUDA
    torch_cuda = _torch_cuda_available()
    has_torch = _module_available("torch")
    torch_status = "available" if torch_cuda else ("torch installed (no CUDA)" if has_torch else "missing")
    checks.append(
        Check(
            "torch + CUDA",
            torch_cuda,
            torch_status,
            "" if torch_cuda else "pip install torch (CUDA build)",
        )
    )

    # Voice cloning
    has_tts = _module_available("TTS")
    checks.append(
        Check(
            "Voice cloning (TTS)",
            has_tts,
            "available" if has_tts else "missing",
            "" if has_tts else "pip install TTS",
        )
    )

    # Avatar face detection
    has_cv2 = _module_available("cv2")
    checks.append(
        Check(
            "Avatar face detection",
            has_cv2,
            "available" if has_cv2 else "missing",
            "" if has_cv2 else "pip install opencv-python",
        )
    )

    # Lip-sync
    engine_dir = Path(os.environ.get("LIPSYNC_DIR", ""))
    has_engine = bool(engine_dir) and (engine_dir / "scripts" / "inference.py").is_file()
    checks.append(
        Check(
            "Avatar lip-sync",
            has_engine,
            str(engine_dir) if has_engine else "missing",
            "" if has_engine else "install the lip-sync engine and set LIPSYNC_DIR",
        )
    )

    return checks
