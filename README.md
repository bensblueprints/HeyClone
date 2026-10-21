# HeyClone

A talking-head avatar and voice cloning toolkit. HeyClone clones a person's
**avatar** (a video of them lip-synced to audio) and **voice**, with automatic
GPU/VRAM detection so it picks the right quality preset for an 8 GB, 16 GB, or
32 GB card.

## What it does

```
avatar source image/video  ──►  face detect + crop   ──►  lip-sync  ──►  talking avatar
reference voice clip       ──►  voice clone          ──►  synthesized speech  ──┘
```

Three capabilities, each wired to the detected GPU tier:

| Capability | Backend | Verifiable here? |
|---|---|---|
| GPU / VRAM detection (8/16/32 GB) | `pynvml` → `nvidia-smi` → `torch` → `rocm-smi` → WMI | Yes — fully working |
| Voice cloning | zero-shot TTS engine | Needs `pip install TTS` + GPU |
| Avatar lip-sync | external lip-sync engine | Needs an engine checkout + GPU |

## Install

```bash
cd heyclone
pip install -e .          # core (adds the `heyclone` command + pynvml)
```

For the heavy stages, on a CUDA machine:

```bash
pip install -r requirements-gpu.txt
```

## Installers

One-command installers that create a dedicated virtual environment and a
`heyclone` launcher (no global pip pollution):

| OS | Installer |
|---|---|
| Windows | `installers\install-windows.bat` (or `install-windows.ps1`) |
| Linux | `installers/install-linux.sh` |
| macOS | `installers/install-macos.command` (double-clickable) |

```bash
# Linux / macOS
./installers/install-linux.sh --gpu

# Windows
installers\install-windows.bat --gpu
```

Add `--gpu` to also install the voice/avatar model dependencies; use
`--dir PATH` to choose an install location. Re-running is safe (`--force`
recreates the venv). After installing, run `heyclone gpu` / `heyclone doctor`.

To build distributable native packages (run on the target OS):

- Windows `.exe` — compile `packaging/windows/heyclone.iss` with
  [Inno Setup](https://jrsoftware.org/isinfo.php)
- Linux `.deb` — `packaging/linux/build-deb.sh`
- macOS `.pkg` — `packaging/macos/build-pkg.sh`

## Commands

```bash
# 0. Check what's installed / missing
heyclone doctor

# 1. Check the GPU and the preset it selects
heyclone gpu

# 2. Clone a voice and synthesize speech
heyclone voice --reference my_voice.wav --text "Hello world" --output out.wav --language en

# 3. Build the avatar face crop
heyclone avatar --source my_face.png --output avatar/

# 4. End-to-end: avatar + cloned voice -> talking avatar
heyclone clone --source my_face.png --reference my_voice.wav \
    --text "Hello, this is my clone" --output result.mp4
```

All commands can also run as `python -m heyclone <command>`.

## VRAM tiers

| Detected VRAM | Tier | Precision | Face crop | Offload |
|---|---|---|---|---|
| < 6 GB / integrated / none | `low` / `none` | fp16 / CPU | 224x224 | yes |
| ~8 GB | `8gb` | fp16 | 256x256 | yes |
| ~16 GB | `16gb` | fp16 | 256x256 | no |
| ~24 GB+ | `32gb` | fp32/bf16 | 512x512 | no |

Lower tiers downscale the face crop and offload layers so an 8 GB card still
runs; a 32 GB card runs full quality.

## Dependencies

- **Voice cloning** — `pip install TTS` (zero-shot). A clean 6-15 s reference
  clip is enough; no fine-tuning. Requires a GPU for reasonable speed, but CPU
  also works (slowly).
- **Avatar face detection** — `pip install opencv-python` (Haar cascade, no
  weights).
- **Avatar lip-sync** — point `LIPSYNC_DIR` at a talking-head lip-sync engine
  checkout (with its `scripts/inference.py`), download its weights, and pass an
  inference YAML via `AvatarCloner.animate(..., inference_config=...)` when the
  default doesn't fit.

## Status / limitations

GPU VRAM detection + tiering is implemented and fully tested. Voice cloning and
avatar lip-sync are real integrations with clean interfaces, but their final
inference requires a CUDA GPU and the model weights listed above — neither of
which can run on a machine with only integrated graphics. The test suite covers
all logic that doesn't require a GPU; end-to-end model inference must be
verified on appropriate hardware.
