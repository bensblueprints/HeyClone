#!/usr/bin/env bash
# Build a .pkg that installs HeyClone source into /Applications/HeyClone and
# links the `heyclone` launcher into /usr/local/bin.
#
# Run on macOS (requires pkgbuild from the Xcode Command Line Tools).
# The resulting .pkg can be installed with the Installer app.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="0.1.0"
TARGET="/Applications/HeyClone"
PAYLOAD="$ROOT/build/macos/payload"
SCRIPTS="$ROOT/build/macos/scripts"

rm -rf "$ROOT/build/macos"
mkdir -p "$PAYLOAD$TARGET" "$SCRIPTS"

rsync -a --exclude '.git' --exclude '.venv' --exclude '.install-test' \
      --exclude '__pycache__' --exclude '*.egg-info' --exclude 'build' --exclude 'dist' \
      "$ROOT/heyclone" "$ROOT/install.py" "$ROOT/pyproject.toml" \
      "$ROOT/requirements.txt" "$ROOT/requirements-gpu.txt" "$ROOT/README.md" \
      "$PAYLOAD$TARGET/"

cat > "$SCRIPTS/postinstall" <<EOF
#!/bin/sh
set -e
python3 "$TARGET/install.py" --dir "$TARGET"
ln -sf "$TARGET/bin/heyclone" /usr/local/bin/heyclone
EOF
chmod 755 "$SCRIPTS/postinstall"

pkgbuild \
  --root "$PAYLOAD" \
  --scripts "$SCRIPTS" \
  --identifier com.heyclone.avatar \
  --version "$VERSION" \
  --install-location / \
  "$ROOT/build/macos/HeyClone-$VERSION.pkg"

echo "Built $ROOT/build/macos/HeyClone-$VERSION.pkg"
