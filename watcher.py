"""watchdog で保存先フォルダを監視し、インデックスとサムネを同期する"""
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Callable, Optional, Set

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import paths
import index
import thumbnail

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".heic", ".gif", ".tiff"}


class ScreenshotHandler(FileSystemEventHandler):
    def __init__(
        self,
        on_change: Optional[Callable[[], None]] = None,
        on_added: Optional[Callable[[str], None]] = None,
    ):
        super().__init__()
        self._on_change = on_change
        self._on_added = on_added
        # 自分で削除したファイルパスのセット（FSEventsの自己ループ防止）
        self._suppress: Set[str] = set()
        self._lock = Lock()

    def suppress_next_delete(self, file_path: str) -> None:
        with self._lock:
            self._suppress.add(file_path)

    def _ingest(self, file_path: str) -> None:
        """新規ファイルをインデックスとサムネに登録（idempotent）"""
        src = Path(file_path)
        # 隠しファイル（macOS screencapture の一時ファイルなど）はスキップ
        if src.name.startswith("."):
            return
        if src.suffix.lower() not in IMAGE_EXTS:
            return
        if not src.exists():
            return
        # 既に登録済みなら何もしない（重複イベント対策）
        if index.find_by_path(str(src)):
            return
        captured_at = datetime.fromtimestamp(src.stat().st_mtime)
        thumb = thumbnail.generate(src)
        index.add_entry(str(src), captured_at, str(thumb))
        if self._on_added:
            self._on_added(str(src))
        if self._on_change:
            self._on_change()

    def on_created(self, event):
        if event.is_directory:
            return
        self._ingest(event.src_path)

    def on_moved(self, event):
        """macOS screencapture は temp ファイル → rename で保存するので必須"""
        if event.is_directory:
            return
        self._ingest(event.dest_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        src_path = event.src_path
        with self._lock:
            if src_path in self._suppress:
                self._suppress.discard(src_path)
                return
        if Path(src_path).suffix.lower() not in IMAGE_EXTS:
            return
        index.remove_entry(src_path)
        thumbnail.cleanup(Path(src_path))
        if self._on_change:
            self._on_change()


class Watcher:
    def __init__(
        self,
        on_change: Optional[Callable[[], None]] = None,
        on_added: Optional[Callable[[str], None]] = None,
    ):
        paths.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        self.handler = ScreenshotHandler(on_change=on_change, on_added=on_added)
        self.observer = Observer()
        self.observer.schedule(self.handler, str(paths.SCREENSHOT_DIR), recursive=False)

    def start(self) -> None:
        self.observer.start()

    def stop(self) -> None:
        self.observer.stop()
        self.observer.join(timeout=5)

    def initial_scan(self) -> None:
        """起動時の全件スキャン：保存先のファイルをインデックスに反映"""
        existing_paths = {e["path"] for e in index.get_all()}
        for f in paths.SCREENSHOT_DIR.iterdir():
            if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
                if str(f) not in existing_paths:
                    captured_at = datetime.fromtimestamp(f.stat().st_mtime)
                    thumb = thumbnail.generate(f)
                    index.add_entry(str(f), captured_at, str(thumb))
        # インデックスに残っているが消えてるファイルを掃除
        for entry in index.get_all():
            if not Path(entry["path"]).exists():
                index.remove_entry(entry["path"])
                thumbnail.cleanup(Path(entry["path"]))
