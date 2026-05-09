"""スクショインデックスのCRUD（JSONベース）"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import paths


def _load() -> List[Dict]:
    """インデックスJSONを読み込む。なければ空、壊れてれば（型不一致含む）空で復旧"""
    if not paths.INDEX_PATH.exists():
        return []
    try:
        data = json.loads(paths.INDEX_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def _save(entries: List[Dict]) -> None:
    """write→renameでアトミックに書き込み（書き込み中クラッシュでも壊れない）"""
    paths.SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = paths.INDEX_PATH.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(paths.INDEX_PATH)


def add_entry(file_path: str, captured_at: datetime, thumbnail_path: str) -> None:
    """エントリを追加（重複は上書き）"""
    entries = [e for e in _load() if e["path"] != file_path]
    entries.append({
        "path": file_path,
        "captured_at": captured_at.isoformat(),
        "filename": Path(file_path).name,
        "thumbnail": thumbnail_path,
    })
    _save(entries)


def remove_entry(file_path: str) -> None:
    """エントリを削除"""
    entries = [e for e in _load() if e["path"] != file_path]
    _save(entries)


def get_all() -> List[Dict]:
    """全エントリを撮影日時の新しい順で返す"""
    entries = _load()
    return sorted(entries, key=lambda e: e["captured_at"], reverse=True)


def search(query: str) -> List[Dict]:
    """ファイル名・日時文字列でフィルタ（部分一致、大文字小文字無視）"""
    q = query.lower().strip()
    if not q:
        return get_all()
    return [
        e for e in get_all()
        if q in e["filename"].lower() or q in e["captured_at"].lower()
    ]


def find_by_path(file_path: str) -> Optional[Dict]:
    for e in _load():
        if e["path"] == file_path:
            return e
    return None
