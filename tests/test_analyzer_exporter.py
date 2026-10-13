import csv

import pytest

from instafollow_analyzer.core.analyzer import analyze
from instafollow_analyzer.core.exporter import export_all, export_category, export_rows
from instafollow_analyzer.core.models import DataError, Relationships
from instafollow_analyzer.core.parser import load_export


@pytest.fixture
def analysis():
    return analyze(Relationships(frozenset({"alice", "bob"}), frozenset({"alice", "carol"})))


def test_set_comparison(analysis):
    assert analysis.not_following_back == {"carol"}
    assert analysis.not_followed_back == {"bob"}
    assert analysis.mutual == {"alice"}
    assert analysis.followers == {"alice", "bob"}
    assert analysis.following == {"alice", "carol"}


def test_empty_comparison():
    result = analyze(Relationships(frozenset(), frozenset()))
    assert not any(result.categories().values())


def test_export_csv(tmp_path, analysis):
    destination = tmp_path / "resultado.csv"
    assert export_all(analysis, destination) == 3
    with destination.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["usuario"] for row in rows] == ["carol", "bob", "alice"]
    assert rows[0]["perfil"] == "https://www.instagram.com/carol/"
    assert rows[0]["categoria"] == "Não me seguem de volta"


def test_export_txt(tmp_path, analysis):
    destination = tmp_path / "resultado.txt"
    assert export_category(analysis, "seguimento_mutuo", destination) == 1
    text = destination.read_text(encoding="utf-8")
    assert "alice\thttps://www.instagram.com/alice/" in text
    assert "bob" not in text


def test_sorted_unicode_destination(tmp_path):
    destination = tmp_path / "conexões.csv"
    result = analyze(Relationships(frozenset(), frozenset({"zoe", "ana"})))
    export_category(result, "nao_me_seguem_de_volta", destination)
    text = destination.read_text(encoding="utf-8-sig")
    assert text.index("ana") < text.index("zoe")


def test_invalid_extension_and_category(tmp_path, analysis):
    with pytest.raises(DataError, match="terminado"):
        export_all(analysis, tmp_path / "output.json")
    with pytest.raises(DataError, match="categoria"):
        export_category(analysis, "unknown", tmp_path / "output.csv")


def test_write_failure(tmp_path, analysis):
    with pytest.raises(DataError, match="salvar"):
        export_all(analysis, tmp_path / "missing" / "output.csv")


def test_atomic_write_preserves_original(tmp_path, analysis, monkeypatch):
    destination = tmp_path / "output.csv"
    destination.write_text("original")

    def denied(*args):
        raise PermissionError("private path")

    monkeypatch.setattr("instafollow_analyzer.core.exporter.os.replace", denied)
    with pytest.raises(DataError):
        export_all(analysis, destination)
    assert destination.read_text() == "original"
    assert list(tmp_path.iterdir()) == [destination]


@pytest.mark.parametrize("username", ["=HYPERLINK()", "+cmd", "@formula", "a\nb"])
def test_reject_spreadsheet_injection(tmp_path, username):
    with pytest.raises(DataError):
        export_rows([("seguimento_mutuo", username)], tmp_path / "safe.csv")
    assert not list(tmp_path.iterdir())


def test_end_to_end(make_export, export_data, tmp_path):
    result = analyze(load_export(make_export(export_data)))
    assert result.mutual == {"alice"}
    assert export_all(result, tmp_path / "result.txt") == 4
