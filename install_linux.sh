#!/usr/bin/env bash

set -euo pipefail

# install only if NOT already installed
if ! pip freeze | grep -q '^runme=='; then
  pip install -e .[build]
fi

pyinstaller runme-desktop.spec


ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_PATH="$ROOT_DIR/dist/RunMe"
INSTALL_DIR="${HOME}/.local/opt/runme"
BIN_DIR="${HOME}/.local/bin"
APPS_DIR="${HOME}/.local/share/applications"
DESKTOP_FILE="${APPS_DIR}/runme.desktop"
SOURCE_ICON_PATH="$ROOT_DIR/src/runme/data/icon.png"
EXEC_PATH="${INSTALL_DIR}/RunMe"
ICON_PATH="${INSTALL_DIR}/runme.png"

if [[ -d "$DIST_PATH" ]]; then
  BUILD_MODE="onedir"
elif [[ -f "$DIST_PATH" ]]; then
  BUILD_MODE="onefile"
else
  echo "Build output not found at $DIST_PATH"
  echo "Run: pyinstaller runme-desktop.spec"
  exit 1
fi

mkdir -p "${HOME}/.local/opt" "$BIN_DIR" "$APPS_DIR"
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

if [[ "$BUILD_MODE" == "onedir" ]]; then
  cp -R "$DIST_PATH"/. "$INSTALL_DIR"
else
  cp "$DIST_PATH" "$EXEC_PATH"
fi

if [[ ! -f "$SOURCE_ICON_PATH" ]]; then
  echo "Icon not found at $SOURCE_ICON_PATH"
  exit 1
fi

cp "$SOURCE_ICON_PATH" "$ICON_PATH"
chmod 755 "$EXEC_PATH"
chmod 644 "$ICON_PATH"
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
echo "Build mode: $BUILD_MODE"
echo "Launcher created at $DESKTOP_FILE"
echo "CLI symlink created at ${BIN_DIR}/runme"
