from pathlib import Path


ROOT = Path.cwd()
ICON = ROOT / "src" / "runme" / "data" / "icon.png"


a = Analysis(
    ["main.py"],
    pathex=[str(ROOT), str(ROOT / "src")],
    binaries=[],
    datas=[(str(ICON), "runme/data")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="RunMe",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(ICON),
)

app = BUNDLE(
    exe,
    name="RunMe.app",
    icon=str(ICON),
    bundle_identifier="com.nicolai.runme",
)
