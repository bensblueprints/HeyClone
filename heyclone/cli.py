"""Command-line interface for HeyClone."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .avatar.clone import AvatarCloner
from .config import get_preset
from .doctor import check_environment
from .gpu.detect import VramTier, detect_gpus
from .voice.clone import VoiceCloner


def _cmd_gpu(args: argparse.Namespace) -> int:
    result = detect_gpus()

    if not result.gpus:
        preset = get_preset(VramTier.NONE)
        print("No discrete GPU detected.")
        print(f"  tier   : {VramTier.NONE.value}")
        print(f"  preset : {preset.label}")
        print("  note   : avatar/voice cloning is unavailable without a CUDA GPU;")
        print("           voice cloning may still run on CPU (very slowly).")
        return 0

    print(f"Detected {len(result.gpus)} GPU(s) via {result.backend.value}:")
    for g in result.gpus:
        print(f"  [{g.index}] {g.name}  -  {g.total_gb:.2f} GB  ({g.tier.value} tier)")

    best = result.best_gpu
    preset = get_preset(best.tier)
    print()
    print(f"Selected: {best.name} ({best.total_gb:.2f} GB)  ->  tier '{best.tier.value}'")
    print(f"Preset  : {preset.label}")
    print(f"  precision    : {preset.model_precision}")
    print(f"  face res     : {preset.face_resolution[0]}x{preset.face_resolution[1]}")
    print(f"  batch size   : {preset.max_batch_size}")
    print(f"  offload      : {preset.offload_layers}")
    print(f"  audio rate   : {preset.audio_sample_rate} Hz")
    if preset.notes:
        print(f"  notes        : {preset.notes}")
    if result.note:
        print(f"  detector note: {result.note}")
    return 0


def _cmd_voice(args: argparse.Namespace) -> int:
    cloner = VoiceCloner()
    print(f"Voice cloning  -  GPU tier: {cloner.detection.tier.value}, gpu={cloner.use_gpu}")
    try:
        result = cloner.clone_voice(args.reference, args.text, args.output, args.language)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote cloned voice to: {result.output_path}")
    print(f"  model      : {result.model_name}")
    print(f"  gpu        : {result.gpu_used}")
    print(f"  sample rate: {result.sample_rate} Hz")
    return 0


def _cmd_avatar(args: argparse.Namespace) -> int:
    cloner = AvatarCloner()
    print(f"Avatar prep  -  GPU tier: {cloner.detection.tier.value}")
    try:
        profile = cloner.prepare(args.source, args.output)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"  source     : {profile.source_path}")
    print(f"  output dir : {profile.output_dir}")
    print(f"  face res   : {profile.face_resolution[0]}x{profile.face_resolution[1]}")
    print(f"  faces found: {profile.num_faces}")
    print(f"  face crop  : {profile.face_crop_path or 'none'}")
    if profile.num_faces == 0:
        print("  warning: no face detected; check the source image/video.")
    return 0


def _cmd_clone(args: argparse.Namespace) -> int:
    detection = detect_gpus()
    print(f"HeyClone clone  -  GPU tier: {detection.tier.value}")

    avatar_cloner = AvatarCloner(detection=detection)
    voice_cloner = VoiceCloner(detection=detection)
    out_parent = Path(args.output).parent or Path(".")

    try:
        profile = avatar_cloner.prepare(args.source, out_parent)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"[1/3] avatar error: {exc}", file=sys.stderr)
        return 1
    print(f"[1/3] avatar face crop: {profile.face_crop_path or 'no face detected'}")

    voice_out = out_parent / "cloned_voice.wav"
    try:
        vres = voice_cloner.clone_voice(args.reference, args.text, voice_out, args.language)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"[2/3] voice error: {exc}", file=sys.stderr)
        return 1
    print(f"[2/3] cloned voice: {vres.output_path}")

    try:
        ares = avatar_cloner.animate(profile, vres.output_path, args.output)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"[3/3] lip-sync error: {exc}", file=sys.stderr)
        return 1
    print(f"[3/3] animated avatar: {ares.output_video}")
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    checks = check_environment()
    width = max(len(c.name) for c in checks)
    print("Environment readiness:")
    for c in checks:
        mark = "OK  " if c.ok else "MISS"
        line = f"  [{mark}] {c.name:<{width}}  {c.status}"
        if c.hint:
            line += f"  (hint: {c.hint})"
        print(line)
    ok_count = sum(1 for c in checks if c.ok)
    print(f"\n{ok_count}/{len(checks)} checks passed.")
    if ok_count < len(checks):
        print("Install the missing items above (see README.md) to enable cloning.")
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="heyclone",
        description="HeyClone - talking-head avatar & voice cloning with VRAM-aware presets.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_gpu = sub.add_parser("gpu", help="Detect the GPU and show its VRAM tier + preset.")
    p_gpu.set_defaults(func=_cmd_gpu)

    p_doctor = sub.add_parser("doctor", help="Check environment readiness for cloning.")
    p_doctor.set_defaults(func=_cmd_doctor)

    p_voice = sub.add_parser("voice", help="Clone a reference voice and synthesize speech.")
    p_voice.add_argument("--reference", required=True, help="Reference audio of the voice to clone.")
    p_voice.add_argument("--text", required=True, help="Text to speak in the cloned voice.")
    p_voice.add_argument("--output", required=True, help="Output audio path.")
    p_voice.add_argument("--language", default="en", help="ISO language code (default: en).")
    p_voice.set_defaults(func=_cmd_voice)

    p_avatar = sub.add_parser("avatar", help="Detect and crop the face for an avatar.")
    p_avatar.add_argument("--source", required=True, help="Source image or video of the face.")
    p_avatar.add_argument("--output", default=None, help="Directory for the cropped avatar.")
    p_avatar.set_defaults(func=_cmd_avatar)

    p_clone = sub.add_parser("clone", help="End-to-end: avatar + cloned voice -> talking avatar.")
    p_clone.add_argument("--source", required=True, help="Source image/video of the person.")
    p_clone.add_argument("--reference", required=True, help="Reference audio of the person's voice.")
    p_clone.add_argument("--text", required=True, help="Text to speak in the cloned voice.")
    p_clone.add_argument("--output", required=True, help="Output video path.")
    p_clone.add_argument("--language", default="en", help="ISO language code (default: en).")
    p_clone.set_defaults(func=_cmd_clone)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
