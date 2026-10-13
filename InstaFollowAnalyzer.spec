# Build on the target OS. Keep Qt as replaceable shared libraries in onedir.
from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / "scripts" / "launcher.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[(str(root / name), ".") for name in (
        "LICENSE", "THIRD_PARTY_NOTICES.md", "README.md",
    )],
    hiddenimports=[],
    hookspath=[str(root / "scripts" / "hooks")],
    runtime_hooks=[],
    excludes=["tkinter", "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick",
              "PySide6.QtWebEngineCore", "PySide6.QtPdf"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="InstaFollowAnalyzer", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="InstaFollowAnalyzer")
