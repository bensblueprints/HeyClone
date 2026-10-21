#!/usr/bin/env python3
"""Cross-platform installer for HeyClone.

Creates a dedicated virtual environment, installs the package (and optionally
the GPU/model dependencies), and writes launcher scripts so you can run
``heyclone`` without activating the venv.

Usage:
    python install.py                # core install (GPU detection + CLI)
    python install.py --gpu          # also install voice/avatar model deps
    python install.py --dir PATH     # install into a custom location

Safe to re-run; pass ``--force`` to recreate the venv from scratch.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def default_install_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "heyclone"


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _run(cmd: list[str]) -> None:
    print("+ " + " ".join(cmd))
    subprocess.check_call(cmd)


def _create_launchers(install_dir: Path, venv_dir: Path) -> list[Path]:
    bin_dir = install_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    if os.name == "nt":
        exe = venv_dir / "Scripts" / "heyclone.exe"
        bat = bin_dir / "heyclone.bat"
        bat.write_text(f'@echo off\r\n"{exe}" %*\r\n', encoding="utf-8")
        created.append(bat)
        ps1 = bin_dir / "heyclone.ps1"
        ps1.write_text(f'& "{exe}" @args\n', encoding="utf-8")
        created.append(ps1)
    else:
        target = venv_dir / "bin" / "heyclone"
        launcher = bin_dir / "heyclone"
        launcher.write_text(f'#!/usr/bin/env sh\nexec "{target}" "$@"\n', encoding="utf-8")
        launcher.chmod(0o755)
        created.append(launcher)
    return created


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install HeyClone into a virtual environment.")
    parser.add_argument("--dir", type=Path, default=None, help="Install directory (default: per-user app data).")
    parser.add_argument("--gpu", action="store_true", help="Also install GPU/model dependencies (large).")
    parser.add_argument("--force", action="store_true", help="Recreate the virtual environment.")
    args = parser.parse_args(argv)

    install_dir = args.dir or default_install_dir()
    venv_dir = install_dir / "venv"
    venv_python = _venv_python(venv_dir)

    print(f"HeyClone installer")
    print(f"  install dir : {install_dir}")
    print(f"  python      : {sys.executable}")

    # 1. Virtual environment
    if venv_python.exists() and not args.force:
        print("  venv        : already present")
    else:
        print("  venv        : creating ...")
        venv.EnvBuilder(with_pip=True, clear=True).create(str(venv_dir))
        venv_python = _venv_python(venv_dir)

    # 2. Package
    _run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
    _run([str(venv_python), "-m", "pip", "install", str(PROJECT_ROOT)])

    # 3. Optional GPU/model deps
    if args.gpu:
        gpu_req = PROJECT_ROOT / "requirements-gpu.txt"
        if gpu_req.is_file():
            _run([str(venv_python), "-m", "pip", "install", "-r", str(gpu_req)])
        else:
            print(f"  warning: {gpu_req} not found; skipping GPU deps.")

    # 4. Launchers
    launchers = _create_launchers(install_dir, venv_dir)
    bin_dir = install_dir / "bin"

    print()
    print("Install complete.")
    for launcher in launchers:
        print(f"  launcher : {launcher}")
    print()
    print("Run it:")
    if os.name == "nt":
        print(f'  "{bin_dir / "heyclone.bat"}" gpu')
        print("  (or add the 'bin' folder to your PATH, then: heyclone gpu)")
    else:
        print(f'  "{bin_dir / "heyclone"}" gpu')
        print("  (or add the 'bin' folder to your PATH, then: heyclone gpu)")
    print()
    print("To install the GPU/model dependencies later, re-run with --gpu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
