# RunMe Desktop

Minimal desktop app for macOS and Linux that launches saved shell scripts from a GUI.

## Run

```bash
python3 main.py
```

Or install it as a package:

```bash
pip install -e .
runme-desktop
```

## Build An App

Use PyInstaller to create a native app bundle/binary for the current platform.

Install build tooling:

```bash
pip install -e ".[build]"
```

If you want to avoid dependency churn in your main Python environment, build in a fresh virtualenv or Conda env instead of your day-to-day env.

Build:

```bash
pyinstaller runme-desktop.spec
```

Results:

- macOS: `dist/RunMe.app`
- Linux: `dist/RunMe/RunMe`

Notes:

- The app icon comes from `src/runme/data/icon.png`.
- Build on macOS for macOS, and on Linux for Linux. PyInstaller is not a cross-compiler.
- On Linux, you can install the built binary system-wide yourself or wrap it in a `.deb`, `.rpm`, AppImage, or Flatpak if you want a distro-native installer.
- On macOS, you can copy `dist/RunMe.app` into `/Applications`. If you want a signed distributable app, you still need to codesign and notarize it.

## Install On Linux

After building on Linux:

```bash
pyinstaller runme-desktop.spec
bash install_linux.sh
```

The install script will:

- Copy `dist/RunMe/` to `~/.local/opt/runme`
- Create a desktop launcher at `~/.local/share/applications/runme.desktop`
- Create a CLI symlink at `~/.local/bin/runme`

Important:

- Keep the full PyInstaller output directory together; do not copy only the `RunMe` binary.
- Ensure `~/.local/bin` is on your `PATH` if you want to launch it as `runme`.

## Features

- Create categories
- Add, edit, clone, and delete commands
- Store each command as an editable `.sh` script
- Choose whether a command runs inline or in a new terminal window
- Run multiple commands concurrently
- View command output in a built-in console window

App data is stored in `~/.runme-desktop/`.
