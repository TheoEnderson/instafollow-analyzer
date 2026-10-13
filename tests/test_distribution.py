"""Regressões de privacidade do empacotamento; nenhum download ou build em testes."""

import pytest

from scripts.audit_linux import audit_bundle, required_versions
from scripts.check_bundle import check_archive_checksum, check_windows_executable
from scripts.package import (
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
