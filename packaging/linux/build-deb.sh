#!/usr/bin/env bash
# Build a .deb that installs HeyClone source to /opt/heyclone and links the
# `heyclone` launcher into /usr/local/bin.
#
# Run on Debian/Ubuntu (requires dpkg-deb). Then install with:
#   sudo apt install ./build/deb/heyclone_0.1.0_amd64.deb
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="0.1.0"
PKG="heyclone_${VERSION}_amd64"
BUILD="$ROOT/build/deb/$PKG"
TARGET="/opt/heyclone"

rm -rf "$ROOT/build/deb"
mkdir -p "$BUILD/DEBIAN" "$BUILD$TARGET"

# Copy source (exclude transient dirs).
rsync -a --exclude '.git' --exclude '.venv' --exclude '.install-test' \
      --exclude '__pycache__' --exclude '*.egg-info' --exclude 'build' --exclude 'dist' \
      "$ROOT/heyclone" "$ROOT/install.py" "$ROOT/pyproject.toml" \
      "$ROOT/requirements.txt" "$ROOT/requirements-gpu.txt" "$ROOT/README.md" \
      "$BUILD$TARGET/"

cat > "$BUILD/DEBIAN/control" <<EOF
Package: heyclone
Version: $VERSION
Architecture: amd64
Maintainer: HeyClone <noreply@example.com>
Depends: python3, python3-venv, python3-pip
Description: Talking-head avatar & voice cloning with VRAM-aware presets
EOF

cat > "$BUILD/DEBIAN/postinst" <<EOF
#!/bin/sh
set -e
python3 "$TARGET/install.py" --dir "$TARGET"
ln -sf "$TARGET/bin/heyclone" /usr/local/bin/heyclone
EOF
chmod 755 "$BUILD/DEBIAN/postinst"

dpkg-deb --build "$BUILD" "$ROOT/build/deb/$PKG.deb"
echo "Built $ROOT/build/deb/$PKG.deb"
