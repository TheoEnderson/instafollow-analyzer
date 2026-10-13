"""Acrescenta fontes/licenças correspondentes e arquiva o build onedir nativo."""

import ast
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tomllib
import urllib.request
from importlib.metadata import distribution, version
from pathlib import Path, PurePosixPath, PureWindowsPath

from PySide6.QtCore import qVersion

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "dist" / "InstaFollowAnalyzer"
MODULES = {
    "Core": "qtbase",
    "Gui": "qtbase",
    "Widgets": "qtbase",
    "DBus": "qtbase",
    "Network": "qtbase",
    "OpenGL": "qtbase",
    "OpenGLWidgets": "qtbase",
    "PrintSupport": "qtbase",
    "Sql": "qtbase",
    "Xml": "qtbase",
    "XcbQpa": "qtbase",
    "EglFSDeviceIntegration": "qtbase",
    "EglFsKmsSupport": "qtbase",
    "WlShellIntegration": "qtwayland",
    "WaylandClient": "qtwayland",
    "WaylandCompositor": "qtwayland",
    "WaylandEglClientHwIntegration": "qtwayland",
    "WaylandEglCompositorHwIntegration": "qtwayland",
    "Svg": "qtsvg",
    "SvgWidgets": "qtsvg",
    "Qml": "qtdeclarative",
    "QmlMeta": "qtdeclarative",
    "QmlModels": "qtdeclarative",
    "Quick": "qtdeclarative",
}


def sources_required() -> set[str]:
    modules = {"qtbase", "qtimageformats"}
    for file in BUNDLE.rglob("*"):
        match = re.match(r"(?:lib)?Qt6([A-Za-z0-9]+)(?:\.so(?:\.|$)|\.dll$)", file.name)
        if match:
            name = match[1]
            if name not in MODULES:
                raise RuntimeError(f"Adicione ao mapa de fontes o módulo Qt: {name}")
            modules.add(MODULES[name])
    return modules


def download(url: str, target: Path) -> str:
    """Cache local para repetir o pacote; não é usado durante a execução do app."""
    if not target.exists():
        temporary = target.with_suffix(".partial")
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "InstaFollow-build/0.1"})
            with (
                urllib.request.urlopen(request, timeout=60) as response,
                temporary.open("wb") as out,
            ):
                shutil.copyfileobj(response, out)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return sha256_file(target)


def copy_source_notices(archive: Path, destination: Path) -> None:
    """Copia textos de licença sem extrair caminhos ou links do TAR."""
    with tarfile.open(archive, "r:xz") as source:
        for member in source:
            parts = PurePosixPath(member.name).parts
            name = parts[-1].lower()
            wanted = (
                "LICENSES" in parts
                or name.startswith(("license", "licence", "copying", "copyright"))
                or name in {"notice", "notice.txt", "qt_attribution.json"}
            )
            if (
                not wanted
                or not member.isfile()
                or member.size > 2 * 1024 * 1024
                or ".." in parts
                or PurePosixPath(member.name).is_absolute()
            ):
                continue
            output = destination.joinpath(*parts)
            output.parent.mkdir(parents=True, exist_ok=True)
            stream = source.extractfile(member)
            if stream is not None:
                with stream, output.open("wb") as out:
                    shutil.copyfileobj(stream, out)


def copy_project_tree(source: Path, destination: Path, suffixes: set[str]) -> None:
    """Copia apenas tipos publicados, sem arquivos ocultos, links ou sobras anteriores."""
    if source.is_symlink() or not source.is_dir():
        raise RuntimeError("Diretório de fontes ausente ou simbólico.")
    if destination.is_symlink():
        raise RuntimeError("Destino de fontes não pode ser um link simbólico.")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for root, directories, files in os.walk(source, followlinks=False):
        directories[:] = [
            name
            for name in directories
            if not name.startswith(".")
            and name != "__pycache__"
            and not (Path(root) / name).is_symlink()
        ]
        for name in files:
            file = Path(root) / name
            if name.startswith(".") or file.is_symlink() or file.suffix.lower() not in suffixes:
                continue
            target = destination / file.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, target)


def sha256_file(file: Path) -> str:
    digest = hashlib.sha256()
    with file.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


PROJECT_DOCUMENTS = {
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
}
GENERATED_DIRECTORIES = {"third-party", "application-source", "assets", "docs"}


def collection_mismatch(
    expected: set[str], actual: set[str], missing: set[str], unexpected: set[str]
) -> str:
    """Somente destinos relativos; nomes extras desconhecidos são redigidos."""
    limit = 12

    def equivalent(name: str) -> str:
        return name.replace("\\", "/").lower()

    known = {equivalent(name) for name in expected}
    mode = (
        "Windows: separadores e caixa"
        if platform.system() == "Windows"
        else "POSIX: caixa preservada"
    )

    def display(name: str, trusted: bool) -> str:
        if trusted or equivalent(name) in known:
            return repr(name[:180]) + (" [truncado]" if len(name) > 180 else "")
        digest = hashlib.sha256(name.encode("utf-8", errors="replace")).hexdigest()[:12]
        suffix = PurePosixPath(name).suffix.lower()
        if suffix not in {".json", ".zip", ".csv", ".txt", ".dll", ".pyd", ".so", ".exe"}:
            suffix = "<outro>"
        return f"<nome redigido sha256={digest} sufixo={suffix!r}>"

    def sample(names: set[str], trusted: bool) -> list[str]:
        return [display(name, trusted) for name in sorted(names)[:limit]]

    return (
        "Pacote contém arquivos extras ou está incompleto. Refaça um build limpo.\n"
        f"Esperados={len(expected)}; encontrados={len(actual)}; "
        f"ausentes={len(missing)}; inesperados={len(unexpected)}.\n"
        f"Ausentes (até {limit}, caminhos relativos): {sample(missing, True)}\n"
        f"Inesperados (até {limit}; nomes desconhecidos redigidos): {sample(unexpected, False)}\n"
        f"Representação: sistema={platform.system()}; "
        f"comparação={mode}; "
        f"TOC com barra invertida={sum('\\' in name for name in expected)}; "
        f"encontrados com barra invertida={sum('\\' in name for name in actual)}. "
        "Nenhum caminho de origem ou conteúdo de arquivo foi registrado."
    )


def collected_path_key(name: str, *, windows: bool) -> str:
    """Normaliza destinos relativos sem aceitar unidades, travessia ou aliases ambíguos."""
    if (
        not name
        or "\x00" in name
        or ":" in name
        or PureWindowsPath(name).anchor
        or PurePosixPath(name).is_absolute()
        or ".." in name.replace("\\", "/").split("/")
    ):
        raise RuntimeError("Inventário contém destino inseguro; refaça um build limpo.")
    path = PurePosixPath(name.replace("\\", "/") if windows else name)
    if path.as_posix() == "." or (
        windows and any(part.endswith((".", " ")) for part in path.parts)
    ):
        raise RuntimeError("Inventário contém destino ambíguo; refaça um build limpo.")
    return path.as_posix().lower() if windows else path.as_posix()


def verify_collected_files(bundle: Path, inventory: Path) -> None:
    """Recusa arquivos extras e incompletos em vez de publicar conteúdo do usuário."""
    if not inventory.is_file():
        raise RuntimeError("Inventário de build ausente. Refaça o build com PyInstaller.")
    try:
        toc = ast.literal_eval(inventory.read_text(encoding="utf-8"))
        if not isinstance(toc, tuple) or len(toc) != 1 or not isinstance(toc[0], list):
            raise ValueError()
        records = toc[0]
        if any(
            not isinstance(row, tuple) or len(row) != 3 or not all(isinstance(v, str) for v in row)
            for row in records
        ):
            raise ValueError()
    except (ValueError, SyntaxError, UnicodeError):
        raise RuntimeError("Formato de inventário COLLECT inválido; refaça o build.") from None
    windows = platform.system() == "Windows"
    expected: dict[str, str] = {}
    for name, _source, kind in records:
        if kind not in {"EXECUTABLE", "PKG", "BINARY", "EXTENSION", "DATA", "SYMLINK"}:
            raise RuntimeError("Tipo de entrada COLLECT não suportado; revise o inventário.")
        # Validar antes de prefixar: _internal/C:/... também não é um destino seguro.
        collected_path_key(name, windows=windows)
        destination = name if kind in {"EXECUTABLE", "PKG"} else f"_internal/{name}"
        key = collected_path_key(destination, windows=windows)
        if key in expected:
            raise RuntimeError("Colisão entre destinos do inventário após normalização.")
        expected[key] = destination
    actual: dict[str, str] = {}
    for root, directories, files in os.walk(bundle, followlinks=False):
        if Path(root) == bundle:
            directories[:] = [name for name in directories if name not in GENERATED_DIRECTORIES]
        for name in files + directories:
            file = Path(root) / name
            if file.is_symlink() and not file.resolve().is_relative_to(bundle.resolve()):
                raise RuntimeError("Pacote contém link externo. Refaça um build limpo.")
            if file.is_file() or file.is_symlink():
                name = file.relative_to(bundle).as_posix()
                key = collected_path_key(name, windows=windows)
                if key in actual:
                    raise RuntimeError("Colisão entre arquivos do pacote após normalização.")
                actual[key] = name
    allowed = {collected_path_key(name, windows=windows) for name in PROJECT_DOCUMENTS}
    missing = {expected[key] for key in expected.keys() - actual.keys()}
    unexpected = {actual[key] for key in actual.keys() - expected.keys() - allowed}
    if missing or unexpected:
        raise RuntimeError(
            collection_mismatch(set(expected.values()), set(actual.values()), missing, unexpected)
        )


def copy_native_notices(inventory: Path, destination: Path) -> dict:
    """Preserva avisos Debian/Ubuntu disponíveis; fontes/patches ainda exigem revisão."""
    report = {
        "packages": {},
        "files": {},
        "common_license_texts": [],
        "unresolved": [],
        "sources_review_required": True,
    }
    if platform.system() != "Linux" or shutil.which("dpkg-query") is None:
        report["unresolved"].append("Inventário de pacotes nativos exige revisão nesta plataforma.")
        return report
    records = ast.literal_eval(inventory.read_text(encoding="utf-8"))[0]
    for name, original, kind in records:
        if kind != "BINARY" or not original.startswith(("/usr/lib/", "/lib/")):
            continue
        owner = subprocess.run(
            ["dpkg-query", "-S", original],
            capture_output=True,
            text=True,
            check=False,
        )
        if owner.returncode:
            report["unresolved"].append(name)
            continue
        package = owner.stdout.split(": ", 1)[0].strip()
        report["files"][name] = package
        if package in report["packages"]:
            continue
        metadata = subprocess.run(
            ["dpkg-query", "-W", "-f=${Version}\t${source:Package}\t${source:Version}", package],
            capture_output=True,
            text=True,
            check=False,
        )
        copyright_file = Path("/usr/share/doc") / package.split(":", 1)[0] / "copyright"
        if metadata.returncode or not copyright_file.is_file():
            report["unresolved"].append(name)
            continue
        target = destination / package.replace(":", "_") / "copyright"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(copyright_file, target)
        # Avisos Debian frequentemente referem textos externos: o copyright sozinho
        # deixa o pacote sem a licença completa. Preservar os textos referenciados.
        for license_name in referenced_common_licenses(copyright_file.read_text(errors="replace")):
            license_file = Path("/usr/share/common-licenses") / license_name
            if not license_file.is_file():
                raise RuntimeError(f"Texto de licença nativa ausente: {license_name}")
            common = destination / "common-licenses" / license_name
            common.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(license_file, common)
            if license_name not in report["common_license_texts"]:
                report["common_license_texts"].append(license_name)
        report["packages"][package] = metadata.stdout.strip().split("\t")
    report["common_license_texts"].sort()
    return report


def referenced_common_licenses(text: str) -> set[str]:
    return {
        name.rstrip(".")
        for name in re.findall(r"/usr/share/common-licenses/([A-Za-z0-9_.+-]+)", text)
    }


def copy_icu_notice(bundle: Path, destination: Path) -> list[dict]:
    """ICU vem no wheel Linux, não nas fontes Qt nem nos pacotes do host."""
    majors = set()
    for file in bundle.rglob("*"):
        match = re.fullmatch(r"libicu\w+\.so\.(\d+)(?:\.\d+)*|icu\w+?(\d+)\.dll", file.name, re.I)
        if match:
            majors.add(next(group for group in match.groups() if group))
    notices = []
    for major in sorted(majors):
        if major != "73":
            raise RuntimeError(f"Revise e inclua os avisos correspondentes ao ICU {major}.")
        source = ROOT / "docs/licenses/ICU-73.2.license"
        target = destination / "ICU-73" / "LICENSE"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        notices.append(
            {"soname_major": major, "notice_release": "73.2", "sha256": sha256_file(source)}
        )
    return notices


def main() -> None:
    if not BUNDLE.is_dir():
        raise SystemExit("Gere dist/InstaFollowAnalyzer com PyInstaller antes de empacotar.")
    if platform.machine().lower() not in {"x86_64", "amd64"}:
        raise SystemExit("Esta configuração de distribuição destina-se a x86_64.")
    verify_collected_files(BUNDLE, ROOT / "build" / "InstaFollowAnalyzer" / "COLLECT-00.toc")
    if platform.system() == "Linux":
        # Recusar builds incompatíveis antes de baixar ou preparar o pacote público.
        subprocess.run([sys.executable, str(ROOT / "scripts/audit_linux.py")], check=True)
    for directory in GENERATED_DIRECTORIES:
        path = BUNDLE / directory
        if path.is_symlink():
            raise RuntimeError("Diretório gerado não pode ser um link simbólico.")
        if path.exists():
            shutil.rmtree(path)
    third_party = BUNDLE / "third-party"
    sources = third_party / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    with (ROOT / "pyproject.toml").open("rb") as metadata:
        app_version = tomllib.load(metadata)["project"]["version"]
    qt_version = qVersion()
    pyside_version = version("PySide6")
    python_version = platform.python_version()
    cache = ROOT / "build" / "third-party-cache"
    cache.mkdir(parents=True, exist_ok=True)
    urls = []
    for module in sorted(sources_required()):
        urls.append(
            f"https://download.qt.io/official_releases/qt/"
            f"{'.'.join(qt_version.split('.')[:2])}/{qt_version}/submodules/"
            f"{module}-everywhere-src-{qt_version}.tar.xz"
        )
    urls.extend(
        [
            f"https://download.qt.io/official_releases/QtForPython/pyside6/"
            f"PySide6-{pyside_version}-src/pyside-setup-everywhere-src-{pyside_version}.tar.xz",
            f"https://www.python.org/ftp/python/{python_version}/Python-{python_version}.tar.xz",
        ]
    )
    manifest = {
        "application_version": app_version,
        "python": sys.version,
        "platform": platform.platform(),
        "qt": qt_version,
        "dependencies": {
            name: version(name)
            for name in (
                "PySide6",
                "PySide6_Essentials",
                "shiboken6",
                "PyInstaller",
                "altgraph",
            )
        },
        "native_libraries": sorted(
            str(file.relative_to(BUNDLE))
            for file in BUNDLE.rglob("*")
            if file.is_file() and (".so" in file.name or file.suffix.lower() == ".dll")
        ),
        "sources": [],
    }
    for url in urls:
        target = sources / url.rsplit("/", 1)[1]
        print(f"Fontes correspondentes: {target.name}", flush=True)
        cached = cache / target.name
        digest = download(url, cached)
        shutil.copy2(cached, target)
        manifest["sources"].append({"url": url, "sha256": digest, "file": target.name})
        copy_source_notices(target, third_party / "notices")
    for name in ("PyInstaller", "altgraph"):
        package = distribution(name)
        for file in package.files or []:
            if "license" in str(file).lower() or "copying" in str(file).lower():
                source = Path(package.locate_file(file))
                if source.is_file():
                    target = third_party / "notices" / name / source.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    manifest["native_packages"] = copy_native_notices(
        ROOT / "build" / "InstaFollowAnalyzer" / "COLLECT-00.toc",
        third_party / "notices" / "system-packages",
    )
    manifest["icu_notices"] = copy_icu_notice(BUNDLE, third_party / "notices")
    if platform.system() == "Linux":
        shutil.copy2(ROOT / "build/linux-abi.json", third_party / "linux-abi.json")
    (third_party / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    for name in (
        "README.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
    ):
        shutil.copy2(ROOT / name, BUNDLE / name)
    (third_party / "README.txt").write_text(
        "Fontes correspondentes das bibliotecas não modificadas estão em sources/.\n"
        "Textos de licença e atribuição estão em notices/ e dentro dos arquivos de fontes.\n"
        "Consulte manifest.json para versões, URLs oficiais e hashes SHA-256.\n"
        "As bibliotecas compartilhadas Qt/PySide/Shiboken em _internal podem ser substituídas "
        "por builds modificados com ABI compatível; preserve nomes, arquitetura e dependências.\n"
        "É permitida engenharia reversa para depurar modificações dessas bibliotecas.\n"
        "Instruções upstream de compilação acompanham cada arquivo de fontes.\n",
        encoding="utf-8",
    )
    published_trees = {
        "src": {".py"},
        "tests": {".py"},
        "scripts": {".py"},
        "docs": {".md", ".license"},
        "assets": {".png"},
        ".github": {".yml", ".yaml", ".md"},
    }
    for directory in ("assets", "docs"):
        copy_project_tree(ROOT / directory, BUNDLE / directory, published_trees[directory])
    app_source = BUNDLE / "application-source"
    if app_source.is_symlink():
        raise RuntimeError("Destino de fontes não pode ser um link simbólico.")
    if app_source.exists():
        shutil.rmtree(app_source)
    app_source.mkdir()
    for directory, suffixes in published_trees.items():
        copy_project_tree(ROOT / directory, app_source / directory, suffixes)
    for name in (
        "pyproject.toml",
        "requirements-build.txt",
        "InstaFollowAnalyzer.spec",
        "README.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        ".gitignore",
        "CONTRIBUTING.md",
        "SECURITY.md",
    ):
        shutil.copy2(ROOT / name, app_source / name)
    system = platform.system().lower()
    archive_format = "zip" if system == "windows" else "gztar"
    destination = ROOT / "dist" / f"InstaFollowAnalyzer-{app_version}-{system}-x86_64"
    result = shutil.make_archive(str(destination), archive_format, BUNDLE.parent, BUNDLE.name)
    checksum = Path(result + ".sha256")
    checksum.write_text(f"{sha256_file(Path(result))}  {Path(result).name}\n", encoding="ascii")
    print(f"Pacote completo: {result}")
    print(f"SHA-256: {checksum}")


if __name__ == "__main__":
    main()
