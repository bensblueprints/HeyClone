"""Persistent voice references for zero-shot cloning; no training is needed."""

import json
import os
import shutil
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

from .clone import VoiceCloner


def data_dir():
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "HeyClone"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/HeyClone"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "heyclone"


@dataclass
class SavedVoice:
    id: str
    name: str
    reference: Path


class VoiceLibrary:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else data_dir()

    def voices(self):
        result = []
        for manifest in sorted((self.root / "voices").glob("*/voice.json")):
            try:
                info = json.loads(manifest.read_text(encoding="utf-8"))
                reference = manifest.parent / Path(info["reference"]).name
                if reference.is_file() and isinstance(info["name"], str):
                    result.append(SavedVoice(manifest.parent.name, info["name"], reference))
            except (ValueError, KeyError, OSError, TypeError):
                continue
        return sorted(result, key=lambda voice: voice.name.casefold())

    def add(self, name, source):
        if not name.strip():
            raise ValueError("Give your voice a name first.")
        source = VoiceCloner._validate_reference(source)
        # Decode before saving, so corrupt or silent uploads never become voices.
        import soundfile as sf
        import numpy as np

        try:
            with sf.SoundFile(source) as audio:
                if len(audio) / audio.samplerate < 3:
                    raise ValueError("Use at least 3 seconds of speech; 6-15 seconds is recommended.")
                sample_rate = audio.samplerate
                samples = audio.read(frames=sample_rate * 30, dtype="float32", always_2d=True).mean(axis=1)
        except RuntimeError as exc:
            raise ValueError("Could not read this audio. Upload WAV, MP3, FLAC or OGG.") from exc
        if not np.isfinite(samples).all() or np.max(np.abs(samples)) < 0.001:
            raise ValueError("This clip is silent. Record or upload audible speech.")
        voice_id = uuid.uuid4().hex
        folder = self.root / "voices" / voice_id
        folder.mkdir(parents=True)
        try:
            reference = folder / "reference.wav"
            sf.write(reference, samples, sample_rate, subtype="PCM_16")
            manifest = folder / "voice.json"
            manifest.write_text(json.dumps({"name": name.strip(), "reference": reference.name}), encoding="utf-8")
        except Exception:
            shutil.rmtree(folder)
            raise
        return SavedVoice(voice_id, name.strip(), reference)

    def output_path(self):
        folder = self.root / "speech"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"speech-{uuid.uuid4().hex[:12]}.wav"
