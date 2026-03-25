#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$ROOT_DIR/dist/RunMe"
INSTALL_DIR="${HOME}/.local/opt/runme"
BIN_DIR="${HOME}/.local/bin"
APPS_DIR="${HOME}/.local/share/applications"
DESKTOP_FILE="${APPS_DIR}/runme.desktop"
EXEC_PATH="${INSTALL_DIR}/RunMe"
ICON_PATH="${INSTALL_DIR}/_internal/runme/data/icon.png"

if [[ ! -d "$DIST_DIR" ]]; then
  echo "Build output not found at $DIST_DIR"
  echo "Run: pyinstaller runme-desktop.spec"
  exit 1
fi

mkdir -p "${HOME}/.local/opt" "$BIN_DIR" "$APPS_DIR"
rm -rf "$INSTALL_DIR"
cp -R "$DIST_DIR" "$INSTALL_DIR"
ln -sf "$EXEC_PATH" "${BIN_DIR}/runme"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=RunMe
Exec=$EXEC_PATH
Icon=$ICON_PATH
Terminal=false
Categories=Utility;Development;
StartupNotify=true
EOF

chmod 644 "$DESKTOP_FILE"

echo "Installed RunMe to $INSTALL_DIR"
echo "Launcher created at $DESKTOP_FILE"
echo "CLI symlink created at ${BIN_DIR}/runme"
