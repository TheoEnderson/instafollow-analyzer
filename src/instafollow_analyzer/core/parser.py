"""Leitura limitada e estrita de ZIPs/pastas; nenhum arquivo é extraído."""

import json
import os
import re
import stat
import struct
import zipfile
import zlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from .models import DataError, Relationships

Progress = Callable[[str], None]
_NAME = re.compile(r"[a-z0-9_.]{1,30}", re.ASCII)
_FILE = re.compile(r"^(followers(?:_(\d+))?|following)\.json$", re.IGNORECASE)
_RESERVED = {"p", "reel", "reels", "stories", "explore", "accounts", "direct", "about"}


@dataclass(frozen=True)
class Limits:
    max_entries: int = 50_000
    max_json_bytes: int = 32 * 1024 * 1024
    max_total_json_bytes: int = 128 * 1024 * 1024
    max_archive_bytes: int = 4 * 1024 * 1024 * 1024
    max_ratio: int = 250
    max_directory_bytes: int = 8 * 1024 * 1024


DEFAULT_LIMITS = Limits()


def normalize_username(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    name = value.strip().lower()
    if name.startswith("@"):
        name = name[1:]
    if not _NAME.fullmatch(name) or name.startswith(".") or name.endswith("."):
        return None
    if ".." in name:
        return None
    return name


def _from_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        url = urlsplit(value)
        if url.scheme != "https" or url.hostname not in {"instagram.com", "www.instagram.com"}:
            return None
        if url.username or url.password or url.port not in {None, 443} or url.query or url.fragment:
            return None
        parts = url.path.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "_u":
            parts = parts[1:]
        if len(parts) != 1 or parts[0].lower() in _RESERVED:
            return None
        return normalize_username(parts[0])
    except ValueError:
        return None


def parse_relationships(document: object, kind: str) -> set[str]:
    """Aceita listas oficiais ou seus wrappers conhecidos; rejeita linhas inválidas."""
    if kind not in {"followers", "following"}:
        raise ValueError("Tipo de relação inválido")
    if isinstance(document, dict):
        key = f"relationships_{kind}"
        if key not in document:
            raise DataError("Estrutura JSON desconhecida. Exporte seguidores e seguindo em JSON.")
        document = document[key]
    if not isinstance(document, list):
        raise DataError(
            "A lista de relações possui um formato incompatível. Gere outra exportação."
        )
    usernames: set[str] = set()
    for record in document:
        if not isinstance(record, dict):
            raise DataError(
                "Há registros incompatíveis no JSON. Gere uma nova exportação completa."
            )
        entries = record.get("string_list_data")
        if entries is None:
            entries = []
        if not isinstance(entries, list) or any(not isinstance(item, dict) for item in entries):
            raise DataError("Há registros incompatíveis no JSON. Gere outra exportação.")
        # value é prioritário. title só é usado para following, onde é um username conhecido.
        names: set[str] = set()
        for entry in entries:
            value = entry.get("value")
            name = normalize_username(value)
            if value not in (None, "") and name is None:
                raise DataError("Nome de usuário incompatível no JSON. Gere outra exportação.")
            name = name or _from_url(entry.get("href"))
            if name:
                names.add(name)
            else:
                raise DataError("Registro sem usuário válido. Gere outra exportação completa.")
        if not names and kind == "following":
            name = normalize_username(record.get("title"))
            if name:
                names.add(name)
        if not names:
            raise DataError(
                "Um registro não contém nome de usuário válido. A análise foi cancelada."
            )
        usernames.update(names)
    return usernames


def _classify(name: str) -> str | None:
    match = _FILE.fullmatch(PurePosixPath(name).name)
    if not match:
        return None
    return "following" if match[1].lower() == "following" else "followers"


def _validate_inventory(names: list[str]) -> None:
    followers = [name for name in names if _classify(name) == "followers"]
    following = [name for name in names if _classify(name) == "following"]
    if not followers or not following:
        missing = "seguidores" if not followers else "seguindo"
        raise DataError(
            f"Lista de {missing} não encontrada. Selecione a exportação completa em JSON, "
            "incluindo seguidores e seguindo (período: todo o tempo)."
        )
    parents = {str(PurePosixPath(name).parent) for name in names}
    if len(following) != 1 or len(parents) != 1 or len(set(names)) != len(names):
        raise DataError("Listas ambíguas ou de várias contas. Importe a pasta de uma única conta.")
    parts = [_FILE.fullmatch(PurePosixPath(name).name)[2] for name in followers]
    if None in parts:
        if len(parts) != 1:
            raise DataError("Listas de seguidores sobrepostas. Importe uma única exportação.")
    else:
        numbers = sorted(int(part) for part in parts)
        if numbers != list(range(1, len(numbers) + 1)):
            raise DataError("Faltam partes da lista de seguidores. Baixe a exportação completa.")


def _decode(raw: bytes, kind: str) -> set[str]:
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise DataError(
            "JSON inválido ou vazio. Gere uma nova exportação no formato JSON."
        ) from exc
    try:
        return parse_relationships(data, kind)
    except RecursionError as exc:
        raise DataError("JSON excessivamente complexo. Gere uma nova exportação.") from exc


def _safe_zip_entry(info: zipfile.ZipInfo) -> None:
    # ZipInfo normaliza separadores conforme o SO e trunca NUL em filename.
    # Validar o nome original evita que essa normalização esconda entradas inseguras.
    name = info.orig_filename
    path = PurePosixPath(name)
    mode = info.external_attr >> 16
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in name
        or ":" in name
        or "\x00" in name
        or stat.S_ISLNK(mode)
    ):
        raise DataError("ZIP contém caminhos inseguros. Use o arquivo oficial sem modificações.")
    if info.flag_bits & 1:
        raise DataError("ZIP protegido por senha não é suportado. Use a exportação oficial.")


def _preflight_zip(path: Path, limits: Limits) -> None:
    """Limita o diretório central antes de ZipFile alocá-lo em memória."""
    with path.open("rb") as stream:
        stream.seek(max(0, path.stat().st_size - 65_557))
        tail = stream.read(65_557)
    offset = tail.rfind(b"PK\x05\x06")
    if offset < 0 or len(tail) - offset < 22:
        raise zipfile.BadZipFile()
    _, disk, directory_disk, disk_count, count, size, start, comment = struct.unpack_from(
        "<4s4H2LH",
        tail,
        offset,
    )
    if offset + 22 + comment != len(tail):
        raise zipfile.BadZipFile()
    if disk or directory_disk or disk_count != count:
        raise DataError("ZIP dividido em volumes não é suportado. Exporte apenas as relações.")
    if count == 0xFFFF or size == 0xFFFFFFFF or start == 0xFFFFFFFF:
        raise DataError("ZIP64 não é suportado nesta versão. Exporte apenas seguidores e seguindo.")
    if count > limits.max_entries or size > limits.max_directory_bytes:
        raise DataError("Diretório do ZIP muito grande. Exporte apenas seguidores e seguindo.")


def _read_zip(path: Path, limits: Limits, progress: Progress) -> Relationships:
    if path.stat().st_size > limits.max_archive_bytes:
        raise DataError("ZIP muito grande (limite: 4 GiB). Exporte apenas seguidores e seguindo.")
    _preflight_zip(path, limits)
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > limits.max_entries:
            raise DataError("ZIP contém arquivos demais. Exporte apenas seguidores e seguindo.")
        relevant = []
        for info in entries:
            _safe_zip_entry(info)
            if not info.is_dir() and _classify(info.filename):
                relevant.append(info)
        _validate_inventory([entry.filename for entry in relevant])
        total = 0
        result: dict[str, set[str]] = {"followers": set(), "following": set()}
        for i, info in enumerate(relevant, 1):
            total += info.file_size
            if info.file_size > limits.max_json_bytes or total > limits.max_total_json_bytes:
                raise DataError(
                    "JSON excede o limite seguro de leitura (32 MiB/arquivo, 128 MiB total)."
                )
            if info.file_size > max(info.compress_size, 1) * limits.max_ratio:
                raise DataError("ZIP tem compressão excessiva e foi recusado por segurança.")
            progress(f"Lendo lista {i} de {len(relevant)}…")
            with archive.open(info) as stream:
                raw = stream.read(limits.max_json_bytes + 1)
            if len(raw) > limits.max_json_bytes:
                raise DataError("JSON excede o limite seguro de leitura.")
            kind = _classify(info.filename)
            result[kind].update(_decode(raw, kind))
        return Relationships(frozenset(result["followers"]), frozenset(result["following"]))


def _read_folder(path: Path, limits: Limits, progress: Progress) -> Relationships:
    relevant: list[Path] = []
    count = 0

    def walk_error(error: OSError) -> None:
        raise error

    for root, dirs, files in os.walk(path, followlinks=False, onerror=walk_error):
        count += len(dirs) + len(files)
        if count > limits.max_entries:
            raise DataError("Pasta contém arquivos demais. Selecione apenas a pasta de relações.")
        dirs[:] = [name for name in dirs if not (Path(root) / name).is_symlink()]
        for name in files:
            if _classify(name):
                file = Path(root) / name
                if file.is_symlink() or not file.is_file():
                    raise DataError("Links simbólicos não são aceitos como arquivos de relações.")
                relevant.append(file)
    _validate_inventory([file.relative_to(path).as_posix() for file in relevant])
    total = 0
    result: dict[str, set[str]] = {"followers": set(), "following": set()}
    for i, file in enumerate(relevant, 1):
        size = file.stat().st_size
        total += size
        if size > limits.max_json_bytes or total > limits.max_total_json_bytes:
            raise DataError(
                "JSON excede o limite seguro de leitura (32 MiB/arquivo, 128 MiB total)."
            )
        progress(f"Lendo lista {i} de {len(relevant)}…")
        with file.open("rb") as stream:
            raw = stream.read(limits.max_json_bytes + 1)
        if len(raw) > limits.max_json_bytes:
            raise DataError("JSON excede o limite seguro de leitura.")
        kind = _classify(file.name)
        result[kind].update(_decode(raw, kind))
    return Relationships(frozenset(result["followers"]), frozenset(result["following"]))


def load_export(
    source: str | Path,
    limits: Limits = DEFAULT_LIMITS,
    progress: Progress = lambda _: None,
) -> Relationships:
    """Valida ambas as listas antes de retornar; erros não expõem caminhos nem registros."""
    path = Path(source)
    try:
        progress("Validando exportação…")
        if path.is_symlink():
            raise DataError("Selecione um arquivo ou pasta real, em vez de um link simbólico.")
        if path.is_dir():
            return _read_folder(path, limits, progress)
        if not path.is_file() or path.suffix.lower() != ".zip":
            raise DataError("Selecione um arquivo ZIP ou uma pasta contendo os JSON extraídos.")
        return _read_zip(path, limits, progress)
    except DataError:
        raise
    except PermissionError as exc:
        raise DataError(
            "Permissão de leitura negada. Escolha uma pasta acessível ao seu usuário."
        ) from exc
    except (zipfile.BadZipFile, EOFError, zlib.error) as exc:
        raise DataError(
            "ZIP inválido ou corrompido. Baixe novamente a exportação oficial."
        ) from exc
    except (OSError, RuntimeError, NotImplementedError, ValueError) as exc:
        raise DataError(
            "Não foi possível ler a exportação. Verifique o arquivo e tente novamente."
        ) from exc
