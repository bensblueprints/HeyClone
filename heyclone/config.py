"""VRAM-tier presets that drive the avatar/voice pipeline configuration.

Lower VRAM tiers reduce the face-crop resolution, switch to lower precision, and
enable layer offloading to fit the model within the available GPU memory.
"""

from __future__ import annotations

from dataclasses import dataclass

from .gpu.detect import VramTier


@dataclass(frozen=True)
class TierPreset:
    tier: VramTier
    label: str
    model_precision: str
    face_resolution: tuple[int, int]
    max_batch_size: int
    offload_layers: bool
    audio_sample_rate: int
    notes: str = ""


PRESETS: dict[VramTier, TierPreset] = {
    VramTier.NONE: TierPreset(
        tier=VramTier.NONE,
        label="CPU-only (no discrete GPU)",
        model_precision="fp32 (CPU)",
        face_resolution=(192, 192),
        max_batch_size=1,
        offload_layers=True,
        audio_sample_rate=16000,
        notes="Very slow; voice cloning may work, real-time avatar lip-sync will not.",
    ),
    VramTier.LOW: TierPreset(
        tier=VramTier.LOW,
        label="Low VRAM (<6 GB)",
        model_precision="fp16",
        face_resolution=(224, 224),
        max_batch_size=1,
        offload_layers=True,
        audio_sample_rate=16000,
        notes="Minimal settings; enable memory offloading and fp16.",
    ),
    VramTier.GB8: TierPreset(
        tier=VramTier.GB8,
        label="8 GB VRAM",
        model_precision="fp16",
        face_resolution=(256, 256),
        max_batch_size=1,
        offload_layers=True,
        audio_sample_rate=16000,
        notes="Comfortable for voice cloning and near-real-time lip-sync.",
    ),
    VramTier.GB16: TierPreset(
        tier=VramTier.GB16,
        label="16 GB VRAM",
        model_precision="fp16",
        face_resolution=(256, 256),
        max_batch_size=2,
        offload_layers=False,
        audio_sample_rate=22050,
        notes="Balanced quality/performance.",
    ),
    VramTier.GB32: TierPreset(
        tier=VramTier.GB32,
        label="32 GB VRAM",
        model_precision="fp32 (or bf16)",
        face_resolution=(512, 512),
        max_batch_size=4,
        offload_layers=False,
        audio_sample_rate=24000,
        notes="Full-quality, no offloading.",
    ),
}


def get_preset(tier: VramTier) -> TierPreset:
    """Return the preset for a tier, falling back to NONE for unknown tiers."""
    return PRESETS.get(tier, PRESETS[VramTier.NONE])
