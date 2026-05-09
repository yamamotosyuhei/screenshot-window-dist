import os
import json
import sys
import tempfile
from pathlib import Path
from datetime import datetime

import pytest

# テスト用に環境変数で支援ディレクトリを差し替えてから import
@pytest.fixture
def tmp_index(tmp_path, monkeypatch):
    monkeypatch.setenv("SW_SUPPORT_DIR", str(tmp_path))
    monkeypatch.setenv("SW_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("SW_SCREENSHOT_DIR", str(tmp_path / "shots"))
    sys.path.insert(0, str(Path(__file__).parent.parent))
    # importを毎回作り直すためにsys.modulesから消す
    for m in list(sys.modules):
        if m in ("paths", "index"):
            del sys.modules[m]
    import index as idx
    return idx


def test_add_and_get_all(tmp_index):
    tmp_index.add_entry("/tmp/a.png", datetime(2026, 5, 8, 0, 12), "/tmp/cache/a.png")
    tmp_index.add_entry("/tmp/b.png", datetime(2026, 5, 8, 0, 15), "/tmp/cache/b.png")
    entries = tmp_index.get_all()
    assert len(entries) == 2
    # 新しい順
    assert entries[0]["path"] == "/tmp/b.png"
    assert entries[1]["path"] == "/tmp/a.png"


def test_remove_entry(tmp_index):
    tmp_index.add_entry("/tmp/a.png", datetime(2026, 5, 8, 0, 12), "/tmp/cache/a.png")
    tmp_index.add_entry("/tmp/b.png", datetime(2026, 5, 8, 0, 15), "/tmp/cache/b.png")
    tmp_index.remove_entry("/tmp/a.png")
    entries = tmp_index.get_all()
    assert len(entries) == 1
    assert entries[0]["path"] == "/tmp/b.png"


def test_search_by_filename(tmp_index):
    tmp_index.add_entry("/tmp/screenshot_2026.png", datetime(2026, 5, 8), "/c/a.png")
    tmp_index.add_entry("/tmp/photo.jpg", datetime(2026, 5, 8), "/c/b.png")
    results = tmp_index.search("screenshot")
    assert len(results) == 1
    assert results[0]["path"] == "/tmp/screenshot_2026.png"


def test_search_by_date_string(tmp_index):
    tmp_index.add_entry("/tmp/a.png", datetime(2026, 5, 8, 12), "/c/a.png")
    tmp_index.add_entry("/tmp/b.png", datetime(2026, 5, 7, 12), "/c/b.png")
    results = tmp_index.search("2026-05-08")
    assert len(results) == 1
    assert results[0]["path"] == "/tmp/a.png"


def test_load_recovers_from_corrupted_json(tmp_index, tmp_path):
    # 一度有効なエントリを書く → ファイルを破壊 → 空に復旧
    tmp_index.add_entry("/tmp/a.png", datetime(2026, 5, 8), "/c/a.png")
    assert len(tmp_index.get_all()) == 1
    tmp_path.joinpath("index.json").write_text("not a json {{{")
    assert tmp_index.get_all() == []  # 空で復旧する


def test_load_recovers_from_wrong_shape_json(tmp_index, tmp_path):
    # JSONとして有効だがリストでない → 空に復旧
    tmp_path.joinpath("index.json").write_text('{"oops": "object"}')
    assert tmp_index.get_all() == []


def test_persist_across_reload(tmp_index, monkeypatch):
    tmp_index.add_entry("/tmp/x.png", datetime(2026, 5, 8), "/c/x.png")
    # importし直しても残ってる
    for m in list(sys.modules):
        if m in ("paths", "index"):
            del sys.modules[m]
    import index as idx2
    entries = idx2.get_all()
    assert len(entries) == 1
    assert entries[0]["path"] == "/tmp/x.png"
