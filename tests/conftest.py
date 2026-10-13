import json
import os
import zipfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def records(*names):
    return [{"string_list_data": [{"value": name}]} for name in names]


@pytest.fixture
def export_data():
    return {
        "connections/followers_and_following/followers_1.json": records(" @Alice ", "bob"),
        "connections/followers_and_following/followers_2.json": records("alice", "carol"),
        "connections/followers_and_following/following.json": {
            "relationships_following": records("alice", "dave"),
        },
    }


@pytest.fixture
def make_export(tmp_path):
    def make(data, zipped=True):
        if zipped:
            path = tmp_path / "export.zip"
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, document in data.items():
                    raw = document if isinstance(document, bytes) else json.dumps(document).encode()
                    archive.writestr(name, raw)
        else:
            path = tmp_path / "export"
            path.mkdir(exist_ok=True)
            for name, document in data.items():
                file = path / name
                file.parent.mkdir(parents=True, exist_ok=True)
                raw = document if isinstance(document, bytes) else json.dumps(document).encode()
                file.write_bytes(raw)
        return path

    return make
