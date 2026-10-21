"""GPU detection and VRAM tiering."""

from .detect import (
    DetectionResult,
    GpuBackend,
    GpuInfo,
    VramTier,
    classify_vram,
    detect_gpus,
)

__all__ = [
    "DetectionResult",
    "GpuBackend",
    "GpuInfo",
    "VramTier",
    "classify_vram",
    "detect_gpus",
]
