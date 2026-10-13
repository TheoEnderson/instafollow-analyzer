"""Verifica runtime e inicialização onedir fora do projeto e sem Python no PATH."""

import argparse
import hashlib
import os
import platform
import re
import struct
import subprocess
import tarfile
import tempfile
import time
import tomllib
import zipfile
from pathlib import Path


def check_archive_checksum(archive: Path) -> None:
    checksum = Path(str(archive) + ".sha256")
    try:
        expected, name = checksum.read_text(encoding="ascii").strip().split("  ", 1)
        if not re.fullmatch(r"[a-f0-9]{64}", expected) or name != archive.name:
            raise ValueError("Checksum malformado")
        with archive.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
    except (OSError, UnicodeError, ValueError) as error:
        raise SystemExit("Arquivo ou checksum SHA-256 ausente/inválido.") from error
    if actual != expected:
        raise SystemExit("Checksum SHA-256 não corresponde ao arquivo de distribuição.")
    print("Checksum SHA-256 do arquivo final conferido.")


def check_windows_executable(executable: Path) -> None:
    """Confere PE x86_64/GUI, sem depender de ferramentas ou caminhos Linux."""
    data = executable.read_bytes()
    try:
        offset = struct.unpack_from("<I", data, 0x3C)[0]
        machine = struct.unpack_from("<H", data, offset + 4)[0]
        magic = struct.unpack_from("<H", data, offset + 24)[0]
        subsystem = struct.unpack_from("<H", data, offset + 24 + 68)[0]
        valid = (
            data[:2] == b"MZ"
            and data[offset : offset + 4] == b"PE\0\0"
            and machine == 0x8664
            and magic == 0x20B
            and subsystem == 2
        )
    except struct.error:
        valid = False
    if not valid:
        raise SystemExit("Executável Windows deve ser PE x86_64 com subsistema GUI.")


def check_bundle(bundle: Path) -> None:
    bundle = bundle.resolve()
    windows = platform.system() == "Windows"
    suffix = ".exe" if windows else ""
    executable = bundle / f"InstaFollowAnalyzer{suffix}"
    internal = bundle / "_internal"
    runtime_pattern = "python3*.dll" if windows else "libpython3*.so*"
    if not executable.is_file() or not any(internal.glob(runtime_pattern)):
        raise SystemExit("Executável ou runtime Python ausente no pacote onedir.")
    pyside = internal / "PySide6"
    if windows:
        check_windows_executable(executable)
        required = {
            "qt6core.dll",
            "qt6gui.dll",
            "qt6widgets.dll",
            "qwindows.dll",
            "qoffscreen.dll",
            "vcruntime140.dll",
            "vcruntime140_1.dll",
        }
        present = {file.name.lower() for file in internal.rglob("*.dll")}
        if missing := required - present:
            raise SystemExit(f"DLLs/plugins obrigatórios ausentes: {', '.join(sorted(missing))}")
    for module in ("QtCore", "QtGui", "QtWidgets"):
        extension = ".pyd" if windows else ".so"
        if not list(pyside.glob(f"{module}*{extension}")):
            raise SystemExit(f"Módulo obrigatório ausente no pacote: {module}")
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    for key in (
        "PYTHONHOME",
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "LD_LIBRARY_PATH",
        "LD_PRELOAD",
        "QT_PLUGIN_PATH",
        "QT_QPA_PLATFORM_PLUGIN_PATH",
        "QML2_IMPORT_PATH",
    ):
        environment.pop(key, None)
    # Preservar SystemRoot/APPDATA no Windows, mas impedir descoberta de Python externo.
    with tempfile.TemporaryDirectory(prefix="instafollow smoke ") as working:
        environment["PATH"] = working
        process = subprocess.Popen([str(executable)], env=environment, cwd=working)
        try:
            time.sleep(3)
            if process.poll() is not None:
                raise SystemExit(
                    f"O aplicativo empacotado encerrou na inicialização: {process.returncode}"
                )
            print(
                "Smoke test offscreen: processo ativo após 3 s, fora do projeto e sem PATH. "
                "Não substitui testes gráficos interativos ou uma máquina sem Python instalado."
            )
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--bundle", type=Path, default=root / "dist" / "InstaFollowAnalyzer")
    group.add_argument("--archive", action="store_true", help="Testar o arquivo final da versão")
    args = parser.parse_args()
    if not args.archive:
        check_bundle(args.bundle)
        return
    with (root / "pyproject.toml").open("rb") as metadata:
        release_version = tomllib.load(metadata)["project"]["version"]
    system = platform.system().lower()
    extension = ".zip" if system == "windows" else ".tar.gz"
    archive = root / "dist" / f"InstaFollowAnalyzer-{release_version}-{system}-x86_64{extension}"
    check_archive_checksum(archive)
    with tempfile.TemporaryDirectory(prefix="instafollow extracted ") as working:
        if extension == ".zip":
            with zipfile.ZipFile(archive) as source:
                source.extractall(working)
        else:
            with tarfile.open(archive) as source:
                source.extractall(working, filter="data")
        check_bundle(Path(working) / "InstaFollowAnalyzer")


if __name__ == "__main__":
    main()
