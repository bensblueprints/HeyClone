"""Isolated local voice engines with in-app downloads and persistent diagnostics."""

from collections import deque
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import zipfile

ENGINES = {
    "nano": {"label": "Chatterbox Nano (English)", "runtime": "chatterbox", "model": "ResembleAI/chatterbox-nano", "revision": "71ccd1d0081b430592cea481f4307e764e07bc64", "implementation": "5de7a54aa4e5e2baadb0182dde554908b48b85c2", "languages": "en"},
    "xtts": {"label": "Coqui XTTS v2", "runtime": "xtts", "model": "tts_models/multilingual/multi-dataset/xtts_v2", "revision": "xtts-v2", "languages": "en es fr de it pt pl tr ru nl cs ar zh-cn ja hu ko hi"},
}
DEFAULT_ENGINE = "nano"


def _spec(engine):
    if engine not in ENGINES:
        raise ValueError(f"Unknown voice engine: {engine}")
    return ENGINES[engine]


def runtime_python(engine="xtts"):
    from .library import data_dir
    spec = _spec(engine)
    folder = data_dir() / "voice-runtime" if spec["runtime"] == "xtts" else data_dir() / "engines" / spec["runtime"]
    return folder / "Scripts" / "python.exe"


def _marker(engine):
    return runtime_python(engine).parent.parent / f"ready-{engine}.json"


def engine_ready(engine):
    try:
        return runtime_python(engine).is_file() and json.loads(_marker(engine).read_text()) == _spec(engine)
    except (OSError, ValueError):
        return False


def _run(command, *, progress=None, log=None, input=None, **kwargs):
    lines = deque(maxlen=40)
    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), **kwargs) as proc:
        if input is not None:
            proc.stdin.write(input)
        proc.stdin.close()
        with open(log, "a", encoding="utf-8") if log else open(os.devnull, "w") as output:
            for line in proc.stdout:
                output.write(line)
                output.flush()
                lines.append(line)
                if progress and line.strip():
                    progress(line.strip()[-180:])
        if proc.wait():
            detail = "".join(lines)[-2500:]
            raise RuntimeError(f"Voice engine failed: {detail}" + (f"\nFull log: {log}" if log else ""))


def _environment(engine):
    from .library import data_dir
    root = data_dir()
    env = dict(os.environ, UV_PYTHON_INSTALL_DIR=str(root / "python"),
               HF_HOME=str(root / "model-cache"), HF_HUB_DISABLE_XET="1",
               PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    if engine == "xtts":
        if not (root / "xtts-terms-accepted").is_file():
            raise RuntimeError("Review the XTTS license in the app before installing or using Coqui.")
        env["COQUI_TOS_AGREED"] = "1"
    return env


def install_runtime(engine=DEFAULT_ENGINE, progress=None):
    if sys.platform != "win32":
        raise RuntimeError("In-app engine installation currently supports Windows.")
    from .library import data_dir
    spec = _spec(engine)
    env = _environment(engine)
    root = data_dir()
    tools = root / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / f"setup-{engine}.log"
    log.write_text(f"Installing {spec['label']}\n", encoding="utf-8")
    report = progress or (lambda message: None)
    uv = tools / "uv.exe"
    if not uv.is_file():
        report("Downloading the Python installer...")
        archive = tools / "uv.zip"
        with urllib.request.urlopen("https://github.com/astral-sh/uv/releases/download/0.13.5/uv-x86_64-pc-windows-msvc.zip", timeout=120) as response:
            archive.write_bytes(response.read())
        if hashlib.sha256(archive.read_bytes()).hexdigest() != "a38b8d1902b7cfbc76b423ba1bb456f623f42064cdc72628b6075b89afd1019a":
            raise RuntimeError("Voice setup download failed its checksum. Please retry.")
        with zipfile.ZipFile(archive) as bundle:
            member = next(n for n in bundle.namelist() if Path(n).name == "uv.exe")
            uv.write_bytes(bundle.read(member))
        archive.unlink()
    python = runtime_python(engine)
    _marker(engine).unlink(missing_ok=True)
    options = dict(env=env, progress=progress, log=log)
    if not python.is_file():
        report("Preparing the isolated Python runtime...")
        _run([str(uv), "venv", "--python", "3.11", str(python.parent.parent)], **options)
    report("Installing speech dependencies. This can take several minutes...")
    if spec["runtime"] == "chatterbox":
        # Nano is newer than the PyPI wheel. Use its released dependencies, then
        # install a pinned upstream source archive without requiring system Git.
        _run([str(uv), "pip", "install", "--python", str(python), "chatterbox-tts==0.1.7", "setuptools==80.9.0",
              "--reinstall-package", "chatterbox-tts", "--torch-backend=auto"], **options)
        source = f"https://github.com/resemble-ai/chatterbox/archive/{spec['implementation']}.zip"
        _run([str(uv), "pip", "install", "--python", str(python), "--no-deps",
              "--reinstall-package", "chatterbox-tts", source], **options)
    else:
        _run([str(uv), "pip", "install", "--python", str(python), "torch==2.8.0", "torchaudio==2.8.0", "--torch-backend=auto"], **options)
        _run([str(uv), "pip", "install", "--python", str(python), "coqui-tts==0.27.5", "transformers>=4.57,<5"], **options)
    report("Downloading and loading the voice model. Please keep HeyClone open...")
    payload = dict(engine=engine, model=spec["model"], revision=spec["revision"], prepare=True)
    _run([str(python), "-c", WORKER], input=json.dumps(payload), **options)
    _marker(engine).write_text(json.dumps(spec), encoding="utf-8")
    return f"{spec['label']} is ready. Model downloaded and loaded successfully."


WORKER = r'''import json, sys, os
if os.name == "nt":
    import ctypes
    ctypes.windll.kernel32.SetDllDirectoryW(None)
import torch
import soundfile as sf
args = json.load(sys.stdin)
torch.set_num_threads(min(8, os.cpu_count() or 4))
device = "cuda" if args.get("gpu") and torch.cuda.is_available() else "cpu"
engine = args["engine"]
print("Loading " + args["model"], flush=True)
if engine == "xtts":
    from TTS.api import TTS
    model = TTS(args["model"]).to(device)
else:
    from huggingface_hub import snapshot_download
    if engine == "nano":
        from chatterbox.tts_turbo import ChatterboxTurboTTS
        patterns = ["ve.safetensors", "t3_nano_v1.safetensors", "s3gen_meanflow.safetensors", "*.json", "*.txt", "conds.pt"]
        folder = snapshot_download(args["model"], revision=args["revision"], allow_patterns=patterns)
        model = ChatterboxTurboTTS.from_local(folder, device=device, nano=True)
if args.get("prepare"):
    print("MODEL_READY", flush=True)
else:
    if engine == "xtts":
        model.tts_to_file(text=args["text"], speaker_wav=args["reference"], language=args["language"], file_path=args["output"])
    else:
        kwargs = {"audio_prompt_path": args["reference"]} if args.get("reference") else {}
        wav = model.generate(args["text"], **kwargs)
        sf.write(args["output"], wav.squeeze().cpu().numpy(), model.sr)
    with sf.SoundFile(args["output"]) as audio:
        if len(audio) == 0:
            raise RuntimeError("The engine produced empty audio")
        print("RESULT " + json.dumps({"sample_rate": audio.samplerate, "gpu_used": device == "cuda"}), flush=True)
'''


def synthesize(model, reference, text, output, language, gpu, engine="xtts", progress=None):
    from .library import data_dir
    spec = _spec(engine)
    if language not in spec["languages"].split():
        raise ValueError(f"{spec['label']} supports: {spec['languages']}. Choose another engine or language.")
    if not engine_ready(engine):
        raise RuntimeError(f"Install {spec['label']} in the Voices tab first.")
    env = _environment(engine)
    if engine == "nano":
        import soundfile as sf
        with sf.SoundFile(reference) as audio:
            if len(audio) / audio.samplerate <= 5:
                raise ValueError("Chatterbox Nano needs more than 5 seconds of speech. Upload or record a 6?15 second clip.")
    logs = data_dir() / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / f"speech-{engine}.log"
    log.write_text("Generating speech\n", encoding="utf-8")
    payload = dict(engine=engine, model=spec["model"], revision=spec["revision"], reference=str(reference), text=text,
                   output=str(output), language=language, gpu=gpu)
    _run([str(runtime_python(engine)), "-c", WORKER], input=json.dumps(payload), env=env, log=log, progress=progress)
    for line in reversed(log.read_text(encoding="utf-8").splitlines()):
        if line.startswith("RESULT "):
            return json.loads(line[7:])
    raise RuntimeError(f"The voice engine did not finish successfully. See {log}")
