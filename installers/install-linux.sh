#!/usr/bin/env bash
# HeyClone Linux installer (launcher for install.py)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "Python 3.9+ is required." >&2
    echo "Install it first, e.g.:  sudo apt install python3 python3-venv python3-pip" >&2
    exit 1
fi

exec "$PY" "$ROOT/install.py" "$@"
