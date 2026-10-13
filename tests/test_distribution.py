"""Regressões de privacidade do empacotamento; nenhum download ou build em testes."""

import pytest

from scripts.audit_linux import audit_bundle, required_versions
from scripts.check_bundle import check_archive_checksum, check_windows_executable
from scripts.package import (
    collected_path_key,
    copy_icu_notice,
    copy_project_tree,
    copy_source_notices,
    referenced_common_licenses,
    verify_collected_files,
)


def test_sources_exclude_personal_files_and_stale_copies(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    for name in (
        "module.py",
        "followers_1.json",
        "export.zip",
        ".env",
        "private.key",
        ".hidden.py",
    ):
        (source / name).write_text("ficticio", encoding="utf-8")
    cache = source / "__pycache__"
    cache.mkdir()
    (cache / "cached.py").write_text("ficticio")
    destination = tmp_path / "published"
    destination.mkdir()
    (destination / "old-private.json").write_text("ficticio")
    copy_project_tree(source, destination, {".py"})
    assert sorted(file.name for file in destination.iterdir()) == ["module.py"]


def test_sources_do_not_follow_links(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    outside = tmp_path / "private.py"
    outside.write_text("ficticio")
    try:
        (source / "external.py").symlink_to(outside)
    except OSError:
        pytest.skip("Links simbólicos indisponíveis")
    destination = tmp_path / "published"
    copy_project_tree(source, destination, {".py"})
    assert not list(destination.iterdir())


@pytest.fixture
def collected_bundle(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "_internal").mkdir(parents=True)
    (bundle / "InstaFollowAnalyzer").write_bytes(b"ficticio")
    (bundle / "_internal/runtime.so").write_bytes(b"ficticio")
    inventory = tmp_path / "COLLECT-00.toc"
    inventory.write_text(
        repr(
            (
                [
                    ("InstaFollowAnalyzer", "build/executable", "EXECUTABLE"),
                    ("runtime.so", "build/runtime.so", "BINARY"),
                ],
            )
        )
    )
    return bundle, inventory


def test_reject_unexpected_export_inside_bundle(collected_bundle):
    bundle, inventory = collected_bundle
    verify_collected_files(bundle, inventory)
    (bundle / "_internal/followers.json").write_text("[]")
    with pytest.raises(RuntimeError, match="extras"):
        verify_collected_files(bundle, inventory)


def test_reject_missing_runtime_file(collected_bundle):
    bundle, inventory = collected_bundle
    (bundle / "_internal/runtime.so").unlink()
    with pytest.raises(RuntimeError, match="incompleto"):
        verify_collected_files(bundle, inventory)


def test_missing_build_inventory_fails_closed(tmp_path):
    with pytest.raises(RuntimeError, match="Inventário"):
        verify_collected_files(tmp_path, tmp_path / "missing.toc")


def test_windows_toc_nested_separators_and_case(collected_bundle, monkeypatch):
    bundle, inventory = collected_bundle
    monkeypatch.setattr("scripts.package.platform.system", lambda: "Windows")
    (bundle / "_internal/PySide6").mkdir()
    (bundle / "_internal/PySide6/QtCore.pyd").write_bytes(b"ficticio")
    inventory.write_text(
        repr(
            (
                [
                    ("instafollowanalyzer", r"D:\build\app.exe", "EXECUTABLE"),
                    ("RUNTIME.SO", r"D:\venv\runtime.so", "BINARY"),
                    (r"PySide6\qtcore.PYD", r"D:\venv\QtCore.pyd", "EXTENSION"),
                ],
            )
        )
    )
    verify_collected_files(bundle, inventory)
    (bundle / "_internal/runtime.so").unlink()
    with pytest.raises(RuntimeError, match="ausentes=1"):
        verify_collected_files(bundle, inventory)


@pytest.mark.parametrize("name", ["RUNTIME.SO", r"sub\runtime.so"])
def test_linux_does_not_fold_case_or_backslashes(collected_bundle, monkeypatch, name):
    bundle, inventory = collected_bundle
    monkeypatch.setattr("scripts.package.platform.system", lambda: "Linux")
    if "\\" in name:
        (bundle / "_internal/sub").mkdir()
        (bundle / "_internal/runtime.so").rename(bundle / "_internal/sub/runtime.so")
    inventory.write_text(
        repr(
            (
                [
                    ("InstaFollowAnalyzer", "/build/app", "EXECUTABLE"),
                    (name, "/build/runtime", "BINARY"),
                ],
            )
        )
    )
    with pytest.raises(RuntimeError, match="ausentes=1; inesperados=1"):
        verify_collected_files(bundle, inventory)


def test_mismatch_diagnostics_are_bounded_and_redact_unknown_names(collected_bundle, monkeypatch):
    bundle, inventory = collected_bundle
    monkeypatch.setattr("scripts.package.platform.system", lambda: "Windows")
    for index in range(30):
        (bundle / "_internal" / f"private-account-{index:02}.json").write_text("private-content")
    (bundle / "_internal/runtime.so").unlink()
    with pytest.raises(RuntimeError) as error:
        verify_collected_files(bundle, inventory)
    message = str(error.value)
    assert "Esperados=2; encontrados=31; ausentes=1; inesperados=30" in message
    assert "_internal/runtime.so" in message
    assert message.count("nome redigido sha256=") == 12
    assert "private-account" not in message
    assert "private-content" not in message
    assert "build/executable" not in message
    assert len(message) < 5000


@pytest.mark.parametrize(
    "name",
    [
        "../outside.dll",
        r"a\..\outside.dll",
        "/outside.dll",
        r"C:\outside.dll",
        "C:outside.dll",
        r"\\host\share\outside.dll",
        "bad\x00.dll",
        "a/./../outside.dll",
    ],
)
def test_collected_paths_reject_unsafe_destinations(name):
    for windows in (True, False):
        with pytest.raises(RuntimeError, match="inseguro"):
            collected_path_key(name, windows=windows)


def test_collected_paths_only_normalize_safe_relative_aliases():
    assert collected_path_key(r"PySide6\./QtCore.pyd", windows=True) == "pyside6/qtcore.pyd"
    assert collected_path_key("PySide6//./QtCore.pyd", windows=False) == "PySide6/QtCore.pyd"


def test_windows_toc_collision_is_rejected(collected_bundle, monkeypatch):
    bundle, inventory = collected_bundle
    monkeypatch.setattr("scripts.package.platform.system", lambda: "Windows")
    inventory.write_text(
        repr(
            (
                [
                    ("runtime.so", "source-a", "BINARY"),
                    ("RUNTIME.SO", "source-b", "BINARY"),
                ],
            )
        )
    )
    with pytest.raises(RuntimeError, match="Colisão"):
        verify_collected_files(bundle, inventory)


def test_unknown_toc_kind_is_not_silently_ignored(collected_bundle):
    bundle, inventory = collected_bundle
    inventory.write_text(repr(([("runtime.so", "source", "UNKNOWN")],)))
    with pytest.raises(RuntimeError, match="não suportado"):
        verify_collected_files(bundle, inventory)


def test_external_pkg_uses_bundle_root(collected_bundle):
    import ast

    bundle, inventory = collected_bundle
    records = ast.literal_eval(inventory.read_text())[0]
    records.append(("application.pkg", "source", "PKG"))
    inventory.write_text(repr((records,)))
    (bundle / "application.pkg").write_bytes(b"ficticio")
    verify_collected_files(bundle, inventory)


def test_external_symlink_remains_rejected(collected_bundle, tmp_path):
    bundle, inventory = collected_bundle
    outside = tmp_path / "outside.so"
    outside.write_bytes(b"ficticio")
    runtime = bundle / "_internal/runtime.so"
    runtime.unlink()
    try:
        runtime.symlink_to(outside)
    except OSError:
        pytest.skip("Links simbólicos indisponíveis")
    with pytest.raises(RuntimeError, match="link externo"):
        verify_collected_files(bundle, inventory)


def test_glibc_requirements_exclude_exported_definitions():
    output = """Version definition section '.gnu.version_d':
    Name: GLIBC_2.99
Version needs section '.gnu.version_r':
    Name: GLIBC_2.9
    Name: GLIBC_2.43
    Name: GLIBC_PRIVATE
    Name: GLIBCXX_3.4.30
"""
    assert required_versions(output) == {"GLIBC_2.9", "GLIBC_2.43", "GLIBC_PRIVATE"}


@pytest.mark.parametrize(
    "requirement, compatible", [("2.9", True), ("2.35", True), ("2.43", False), ("PRIVATE", False)]
)
def test_linux_abi_rejects_newer_and_unclassified_requirements(
    tmp_path, monkeypatch, requirement, compatible
):
    from types import SimpleNamespace

    (tmp_path / "InstaFollowAnalyzer").write_bytes(b"\x7fELFficticio")
    monkeypatch.setattr("scripts.audit_linux.shutil.which", lambda _: "readelf")
    monkeypatch.setattr(
        "scripts.audit_linux.subprocess.run",
        lambda *a, **k: SimpleNamespace(
            stdout=f"Version needs section\n Name: GLIBC_{requirement}"
        ),
    )
    assert audit_bundle(tmp_path)["compatible_symbol_versions"] is compatible


def test_referenced_license_texts_include_version_without_sentence_punctuation():
    assert referenced_common_licenses(
        "See /usr/share/common-licenses/LGPL-2.1.\n"
        "and `/usr/share/common-licenses/GPL-3`, /usr/share/common-licenses/GPL-3."
    ) == {"LGPL-2.1", "GPL-3"}


@pytest.mark.parametrize("machine, subsystem", [(0x8664, 2), (0x14C, 2), (0x8664, 3)])
def test_windows_pe_requires_x64_gui(tmp_path, machine, subsystem):
    import struct

    data = bytearray(256)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 64)
    data[64:68] = b"PE\0\0"
    struct.pack_into("<H", data, 68, machine)
    struct.pack_into("<H", data, 88, 0x20B)
    struct.pack_into("<H", data, 156, subsystem)
    executable = tmp_path / "ficticio.exe"
    executable.write_bytes(data)
    if machine == 0x8664 and subsystem == 2:
        check_windows_executable(executable)
    else:
        with pytest.raises(SystemExit, match="GUI"):
            check_windows_executable(executable)


def test_qt_spdx_license_directory_is_preserved(tmp_path):
    import io
    import tarfile

    archive = tmp_path / "ficticio.tar.xz"
    with tarfile.open(archive, "w:xz") as source:
        for name in ("qt/LICENSES/LGPL-3.0-only.txt", "qt/../outside/LICENSE"):
            info = tarfile.TarInfo(name)
            info.size = len(b"ficticio")
            source.addfile(info, io.BytesIO(b"ficticio"))
    destination = tmp_path / "notices"
    copy_source_notices(archive, destination)
    assert (destination / "qt/LICENSES/LGPL-3.0-only.txt").read_bytes() == b"ficticio"
    assert not (tmp_path / "outside").exists()


def test_unknown_vendored_icu_requires_license_review(tmp_path):
    (tmp_path / "libicuuc.so.99").write_bytes(b"ficticio")
    with pytest.raises(RuntimeError, match="ICU 99"):
        copy_icu_notice(tmp_path, tmp_path / "notices")


def test_archive_checksum_rejects_tampering(tmp_path):
    from scripts.package import sha256_file

    archive = tmp_path / "ficticio.zip"
    archive.write_bytes(b"ficticio")
    archive.with_suffix(".zip.sha256").write_text(f"{sha256_file(archive)}  {archive.name}\n")
    check_archive_checksum(archive)
    archive.write_bytes(b"alterado")
    with pytest.raises(SystemExit, match="não corresponde"):
        check_archive_checksum(archive)


@pytest.mark.parametrize("checksum", [None, "invalido", "0" * 64 + "  outro.zip\n"])
def test_archive_checksum_requires_correct_sidecar(tmp_path, checksum):
    archive = tmp_path / "ficticio.zip"
    archive.write_bytes(b"ficticio")
    if checksum is not None:
        archive.with_suffix(".zip.sha256").write_text(checksum)
    with pytest.raises(SystemExit, match="ausente/inválido"):
        check_archive_checksum(archive)
