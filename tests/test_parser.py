import json
import stat
import zipfile
from dataclasses import replace

import pytest

from instafollow_analyzer.core.models import DataError
from instafollow_analyzer.core.parser import (
    Limits,
    _safe_zip_entry,
    load_export,
    normalize_username,
    parse_relationships,
)

from .conftest import records


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" @Alice.Test_1 ", "alice.test_1"),
        ("a", "a"),
        ("a" * 30, "a" * 30),
        ("a" * 31, None),
        ("John Doe", None),
        ("https://instagram.com/alice/", None),
        ("=cmd", None),
        ("+alice", None),
        ("../alice", None),
        ("álice", None),
        (None, None),
        (123, None),
        ("", None),
        (".alice", None),
        ("a..b", None),
    ],
)
def test_normalize(value, expected):
    assert normalize_username(value) == expected


def test_followers_and_deduplication():
    assert parse_relationships(records(" ALICE ", "alice", "@bob"), "followers") == {"alice", "bob"}


def test_following_value_has_priority():
    document = {
        "relationships_following": [
            {"title": "display_name", "string_list_data": [{"value": "real_user"}]},
            {"title": "title_user", "string_list_data": []},
        ]
    }
    assert parse_relationships(document, "following") == {"real_user", "title_user"}


@pytest.mark.parametrize("kind", ["followers", "following"])
def test_wrappers_and_empty_lists(kind):
    assert parse_relationships({f"relationships_{kind}": []}, kind) == set()
    assert parse_relationships([], kind) == set()


@pytest.mark.parametrize(
    "url",
    [
        "https://www.instagram.com/alice/",
        "https://instagram.com/_u/alice/",
    ],
)
def test_url_fallback(url):
    assert parse_relationships([{"string_list_data": [{"href": url}]}], "followers") == {"alice"}


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/alice/",
        "https://instagram.com.evil.example/alice/",
        "https://instagram.com/p/123/",
        "https://instagram.com/alice/?tracking=1",
        "https://user@instagram.com/alice/",
        "javascript:alert(1)",
        "https://instagram.com:abc/alice/",
        "https://instagram.com/explore/",
    ],
)
def test_reject_non_profile_urls(url):
    with pytest.raises(DataError):
        parse_relationships([{"string_list_data": [{"href": url}]}], "followers")


@pytest.mark.parametrize(
    "document",
    [
        {},
        {"unknown": []},
        "text",
        None,
        [123],
        [{}],
        [{"title": "DisplayName"}],
        [{"string_list_data": {}}],
        [{"string_list_data": ["alice"]}],
        records("John Doe"),
        records("alice") + [{}],
    ],
)
def test_unknown_structure_is_never_silently_skipped(document):
    with pytest.raises(DataError):
        parse_relationships(document, "followers")


@pytest.mark.parametrize("zipped", [True, False])
def test_nested_export_with_split_followers(make_export, export_data, zipped):
    messages = []
    source = make_export(export_data, zipped)
    before = sorted(p.name for p in source.parent.iterdir())
    data = load_export(source, progress=messages.append)
    assert data.followers == {"alice", "bob", "carol"}
    assert data.following == {"alice", "dave"}
    assert len(messages) == 4
    assert sorted(p.name for p in source.parent.iterdir()) == before


@pytest.mark.parametrize("name", ["followers_1.json", "following.json"])
def test_missing_list(make_export, name):
    with pytest.raises(DataError, match="não encontrada"):
        load_export(make_export({name: []}))


@pytest.mark.parametrize("raw", [b"", b"not-json", b"[", b"\xff\xfe", b"[" * 2000])
@pytest.mark.parametrize("zipped", [True, False])
def test_invalid_json(make_export, raw, zipped):
    with pytest.raises(DataError, match="JSON"):
        load_export(make_export({"followers_1.json": raw, "following.json": []}, zipped))


def test_corrupt_zip(tmp_path):
    source = tmp_path / "bad.zip"
    source.write_bytes(b"not-a-zip")
    with pytest.raises(DataError, match="corrompido"):
        load_export(source)


def test_empty_folder(tmp_path):
    with pytest.raises(DataError, match="não encontrada"):
        load_export(tmp_path)


def test_empty_lists_are_valid(make_export):
    result = load_export(make_export({"followers.json": [], "following.json": []}))
    assert result.followers == result.following == frozenset()


def test_utf8_bom(make_export):
    result = load_export(
        make_export(
            {
                "followers_1.json": b"\xef\xbb\xbf" + json.dumps(records("alice")).encode(),
                "following.json": [],
            }
        )
    )
    assert result.followers == {"alice"}


@pytest.mark.parametrize(
    "names",
    [
        ["followers_2.json", "following.json"],
        ["followers_1.json", "followers_3.json", "following.json"],
        ["followers.json", "followers_1.json", "following.json"],
        ["a/followers_1.json", "a/following.json", "b/following.json"],
        ["a/followers_1.json", "b/following.json"],
    ],
)
def test_incomplete_or_ambiguous_export(make_export, names):
    with pytest.raises(DataError):
        load_export(make_export(dict.fromkeys(names, [])))


@pytest.mark.parametrize(
    "name",
    [
        "../bad.txt",
        "a/../bad.txt",
        "/bad.txt",
        "C:/bad.txt",
        "C:bad.txt",
        "C:\\bad.txt",
        "a\\bad.txt",
        "\\\\host\\share\\bad.txt",
        "followers_1.json\x00/../bad.txt",
    ],
)
def test_unsafe_paths(make_export, name):
    source = make_export({"followers_1.json": [], "following.json": []})
    # O escritor padrão normaliza barras invertidas no Windows. Preservar o
    # nome literal nos cabeçalhos para testar um ZIP realmente malicioso em todo SO.
    with zipfile.ZipFile(source, "a") as archive:
        info = zipfile.ZipInfo(name)
        info.filename = name
        archive.writestr(info, b"")
    with zipfile.ZipFile(source) as archive:
        assert archive.infolist()[-1].orig_filename == name
    with pytest.raises(DataError, match="inseguros"):
        load_export(source)


@pytest.mark.parametrize("name", ["a\\bad.txt", "followers_1.json\x00/../bad.txt"])
def test_zip_validation_checks_original_name_before_normalization(name):
    info = zipfile.ZipInfo(name)
    # Exercitar no Linux também o estado produzido pelo ZipInfo no Windows.
    info.filename = name.split("\x00", 1)[0].replace("\\", "/")
    with pytest.raises(DataError, match="inseguros"):
        _safe_zip_entry(info)


def test_zip_symlink(tmp_path):
    source = tmp_path / "links.zip"
    with zipfile.ZipFile(source, "w") as archive:
        info = zipfile.ZipInfo("followers_1.json")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "outside")
        archive.writestr("following.json", "[]")
    with pytest.raises(DataError, match="inseguros"):
        load_export(source)


@pytest.mark.parametrize("zipped", [True, False])
@pytest.mark.parametrize(
    "overrides",
    [
        {"max_json_bytes": 2},
        {"max_total_json_bytes": 3},
        {"max_entries": 1},
    ],
)
def test_read_limits(make_export, export_data, zipped, overrides):
    source = make_export(export_data, zipped)
    with pytest.raises(DataError):
        load_export(source, replace(Limits(), **overrides))


def test_archive_size_limit(make_export, export_data):
    with pytest.raises(DataError, match="grande"):
        load_export(make_export(export_data), replace(Limits(), max_archive_bytes=1))


def test_zip_bomb(make_export):
    source = make_export({"followers_1.json": b" " * 500_000, "following.json": []})
    with pytest.raises(DataError, match="compressão"):
        load_export(source)


def test_symlink_folder_file(tmp_path, make_export):
    source = make_export({"following.json": []}, zipped=False)
    try:
        (source / "followers_1.json").symlink_to(source / "following.json")
    except OSError:
        pytest.skip("Criação de symlinks não permitida neste sistema")
    with pytest.raises(DataError, match="simbólicos"):
        load_export(source)


def test_unsupported_input(tmp_path):
    with pytest.raises(DataError, match="Selecione"):
        load_export(tmp_path / "missing.zip")


def test_permission_error_is_friendly(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("private path")

    monkeypatch.setattr("instafollow_analyzer.core.parser.os.walk", denied)
    with pytest.raises(DataError, match="Permissão") as error:
        load_export(tmp_path)
    assert "private path" not in str(error.value)


def test_central_directory_limit_before_zipfile(make_export, export_data):
    source = make_export(export_data)
    with pytest.raises(DataError, match="Diretório"):
        load_export(source, replace(Limits(), max_directory_bytes=1))


def test_incomplete_entry_in_otherwise_valid_record():
    with pytest.raises(DataError):
        parse_relationships(
            [
                {"string_list_data": [{"value": "alice"}, {}]},
            ],
            "followers",
        )


def test_zip64_rejected_before_loading_directory(make_export):
    source = make_export({"followers_1.json": [], "following.json": []})
    raw = bytearray(source.read_bytes())
    footer = raw.rfind(b"PK\x05\x06")
    raw[footer + 10 : footer + 12] = b"\xff\xff"
    raw[footer + 8 : footer + 10] = b"\xff\xff"
    source.write_bytes(raw)
    with pytest.raises(DataError, match="ZIP64"):
        load_export(source)


def test_encrypted_zip_flag_rejected(make_export):
    source = make_export({"followers_1.json": [], "following.json": []})
    raw = bytearray(source.read_bytes())
    directory = raw.index(b"PK\x01\x02")
    raw[directory + 8 : directory + 10] = b"\x01\x00"
    source.write_bytes(raw)
    with pytest.raises(DataError, match="senha"):
        load_export(source)


def test_zip_crc_corruption_rejected(tmp_path):
    source = tmp_path / "bad-crc.zip"
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("followers_1.json", "[]")
        archive.writestr("following.json", "[]")
    raw = bytearray(source.read_bytes())
    data_offset = raw.index(b"[]")
    raw[data_offset] = ord("{")
    source.write_bytes(raw)
    with pytest.raises(DataError, match="corrompido"):
        load_export(source)
