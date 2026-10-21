#!/usr/bin/env bash
# HeyClone macOS installer (launcher for install.py).
# Double-clickable from Finder as install-macos.command, or run from Terminal.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "Python 3.9+ is required." >&2
    echo "Install it from https://www.python.org/downloads/macos/ and re-run." >&2
    exit 1
fi

exec "$PY" "$ROOT/install.py" "$@"
