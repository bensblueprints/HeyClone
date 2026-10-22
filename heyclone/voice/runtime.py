"""Optional isolated speech engine for the standalone Windows application."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import zipfile


def runtime_python():
    from .library import data_dir
    return data_dir() / "voice-runtime" / "Scripts" / "python.exe"


def _run(command, **kwargs):
    proc = subprocess.run(command, capture_output=True, text=True,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), **kwargs)
    if proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout)[-3000:])
    return proc


def install_runtime():
    if sys.platform != "win32":
        raise RuntimeError("Install coqui-tts, torch and torchaudio in your Python environment.")
    from .library import data_dir
    root = data_dir()
    tools = root / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    uv = tools / "uv.exe"
    if not uv.is_file():
        archive = tools / "uv.zip"
        urllib.request.urlretrieve(
            "https://github.com/astral-sh/uv/releases/download/0.13.5/uv-x86_64-pc-windows-msvc.zip", archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != "a38b8d1902b7cfbc76b423ba1bb456f623f42064cdc72628b6075b89afd1019a":
            raise RuntimeError("Voice setup download failed its checksum. Please retry.")
        with zipfile.ZipFile(archive) as bundle:
            member = next(n for n in bundle.namelist() if Path(n).name == "uv.exe")
            uv.write_bytes(bundle.read(member))
        archive.unlink()
    env = dict(os.environ, UV_PYTHON_INSTALL_DIR=str(root / "python"))
    python = runtime_python()
    if not python.is_file():
        _run([str(uv), "venv", "--python", "3.11", str(python.parent.parent)], env=env)
    _run([str(uv), "pip", "install", "--python", str(python),
          "torch==2.8.0", "torchaudio==2.8.0", "--torch-backend=auto"], env=env)
    _run([str(uv), "pip", "install", "--python", str(python), "coqui-tts>=0.27.4,<0.28"], env=env)
    _run([str(python), "-c", "from TTS.api import TTS"], env=env)
    (python.parent.parent / "ready").write_text("coqui-tts", encoding="utf-8")
    return "Voice engine installed. Select a voice and generate speech. The model downloads on first use."


WORKER = '''
import json, sys
from TTS.api import TTS
import torch
args = json.load(sys.stdin)
model = TTS(args["model"]).to("cuda" if args["gpu"] and torch.cuda.is_available() else "cpu")
model.tts_to_file(text=args["text"], speaker_wav=args["reference"], language=args["language"], file_path=args["output"])
'''


def synthesize(model, reference, text, output, language, gpu):
    from .library import data_dir
    python = runtime_python()
    if not python.is_file():
        raise RuntimeError("Click Set up voice engine in the Voices tab before generating speech.")
    if not (data_dir() / "xtts-terms-accepted").is_file():
        raise RuntimeError("Review and accept the XTTS model terms in the Voices tab first.")
    payload = dict(model=model, reference=str(reference), text=text,
                   output=str(output), language=language, gpu=gpu)
    _run([str(python), "-c", WORKER], input=json.dumps(payload),
         env=dict(os.environ, COQUI_TOS_AGREED="1"))
