#!/usr/bin/env python3
"""スクショ窓口 メニューバーアプリ"""
import fcntl
import os
import subprocess
import sys
from datetime import datetime

import rumps

import paths
import settings
from watcher import Watcher
from panel import ScreenshotPanel

# BTTなど外部からのトグル要求はこのファイルが作成される＝アプリ側で検知
TOGGLE_FLAG = paths.CACHE_DIR / ".toggle_request"
# 二重起動防止用のPIDロックファイル
PID_LOCK = paths.CACHE_DIR / ".pid"
_lock_fd = None  # flockを保持し続けるためのfd（プロセス生存中は開いたままにする）


def _acquire_lock_or_exit() -> None:
    """flockで二重起動を防ぐ。前のプロセスが死ねばOSがロックを自動解放するため、
    PID再利用やクラッシュ残骸での誤判定（開いた瞬間に落ちる）を起こさない。"""
    global _lock_fd
    paths.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _lock_fd = open(PID_LOCK, "a+")
    try:
        fcntl.flock(_lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        _lock_fd.seek(0)
        running_pid = _lock_fd.read().strip()
        print(f"既に起動中（PID {running_pid}）。新規起動を中止します。")
        sys.exit(0)
    _lock_fd.seek(0)
    _lock_fd.truncate()
    _lock_fd.write(str(os.getpid()))
    _lock_fd.flush()


def log(msg: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{now} | {msg}"
    print(line)
    paths.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(paths.LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


class ScreenshotWindowApp(rumps.App):
    def __init__(self):
        super().__init__("🖼️", quit_button=None)
        self.menu = [
            rumps.MenuItem("窓口を開く", callback=self.toggle_panel),
            None,
            rumps.MenuItem("保存先フォルダを開く", callback=self.open_folder),
            rumps.MenuItem("保存先設定を確認", callback=self.check_settings),
            None,
            rumps.MenuItem("窓口を全部ゴミ箱に送る", callback=self.confirm_clear_all),
            None,
            rumps.MenuItem("終了", callback=self.quit_app),
        ]
        self.panel = None
        self.watcher = None
        self._toggle_timer = rumps.Timer(self._check_toggle_flag, 0.5)

    def setup(self):
        # フォルダ準備
        paths.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        paths.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        paths.SUPPORT_DIR.mkdir(parents=True, exist_ok=True)

        # 起動時に古いフラグが残ってたら消す（前回終了時の取りこぼし対策）
        if TOGGLE_FLAG.exists():
            try:
                TOGGLE_FLAG.unlink()
            except OSError:
                pass

        # macOSスクショ保存先を窓口フォルダに設定（変更されてれば）
        current = settings.get_screenshot_location()
        if current != paths.SCREENSHOT_DIR:
            log(f"スクショ保存先を変更: {current} → {paths.SCREENSHOT_DIR}")
            settings.set_screenshot_location(paths.SCREENSHOT_DIR)

        # macOS純正の撮影直後プレビューを無効化（即ファイル保存→窓口に即反映するため）
        if settings.get_show_thumbnail():
            log("macOS純正プレビューを無効化")
            settings.set_show_thumbnail(False)

        # パネル作成
        self.panel = ScreenshotPanel.alloc().init()

        # ファイル監視開始
        self.watcher = Watcher(
            on_change=self._on_files_changed,
            on_added=self._on_file_added,
        )
        self.watcher.initial_scan()
        self.watcher.start()

        # トグル要求の監視タイマー開始（メインスレッドで動く）
        self._toggle_timer.start()

        log("スクショ窓口 起動完了")

    def _check_toggle_flag(self, _):
        """0.5秒ごとに呼ばれる。BTT等が touch したフラグファイルを検知してトグル"""
        if not TOGGLE_FLAG.exists():
            return
        try:
            TOGGLE_FLAG.unlink()
        except OSError:
            pass
        log("トグル要求検知 → パネルトグル")
        self.toggle_panel(None)

    def _on_files_changed(self):
        """watcher からのコールバック → パネルが開いてれば再描画"""
        if self.panel and self.panel.is_panel_visible():
            # メインスレッドで refresh を呼ぶ必要がある
            from AppKit import NSOperationQueue
            NSOperationQueue.mainQueue().addOperationWithBlock_(
                lambda: self.panel.refresh_panel(self.panel.search_field.stringValue())
            )

    def _on_file_added(self, file_path: str):
        """新規ファイル追加時 → 撮影直後フローティング通知をメインスレッドで表示"""
        if self.panel:
            from AppKit import NSOperationQueue
            NSOperationQueue.mainQueue().addOperationWithBlock_(
                lambda: self.panel.show_notification(file_path)
            )

    def toggle_panel(self, _=None):
        if self.panel:
            self.panel.toggle_panel()

    def open_folder(self, _):
        subprocess.Popen(["open", str(paths.SCREENSHOT_DIR)])

    def check_settings(self, _):
        current = settings.get_screenshot_location()
        msg = f"現在の保存先: {current}\\n窓口フォルダ: {paths.SCREENSHOT_DIR}"
        if current == paths.SCREENSHOT_DIR:
            msg += "\\n\\n✓ 一致しています"
        else:
            msg += "\\n\\n⚠ 一致していません。次回起動時に自動修正されます"
        subprocess.Popen([
            "osascript", "-e",
            f'display dialog "{msg}" buttons {{"OK"}} default button "OK"'
        ])

    def confirm_clear_all(self, _):
        """窓口の全エントリをゴミ箱送り（alert_front で確認、復元可能）"""
        log("メニュー: 全クリア押下")
        if self.panel is None:
            return
        import index
        from panel import alert_front
        total = len(index.get_all())
        if total == 0:
            alert_front("スクショ窓口", "窓口は既に空です。", panel_window=self.panel.window)
            return
        # 確認中だけパネルを通常レベルに下げる＝ダイアログがパネルの裏に隠れない。戻り値: 1=OK(実行), 0=Cancel
        response = alert_front(
            title="全部ゴミ箱に送る",
            message=(
                f"窓口の {total} 件すべてをゴミ箱に送ります。\n"
                f"（macOSのゴミ箱から復元できます）\n\n"
                f"実行しますか？"
            ),
            ok="実行",
            cancel="キャンセル",
            panel_window=self.panel.window,
        )
        log(f"DBG clear-all alert response={response}")
        if response != 1:
            return
        try:
            sent = self.panel.delete_all()
            log(f"窓口を全クリア: {sent}件をゴミ箱送り")
        except Exception as e:
            import traceback
            log(f"ERROR delete_all: {type(e).__name__}: {e}")
            log(traceback.format_exc())

    def quit_app(self, _):
        if self.watcher:
            self.watcher.stop()
        try:
            if PID_LOCK.exists():
                PID_LOCK.unlink()
        except OSError:
            pass
        log("スクショ窓口 停止")
        rumps.quit_application()


_app = None


def _patch_dock_reopen():
    """rumps内部のNSApplicationDelegateクラスにDockクリック検知を注入"""
    import rumps.rumps as _rumps_internal

    def applicationShouldHandleReopen_hasVisibleWindows_(self, app, has_visible_windows):
        if _app is not None and _app.panel is not None:
            _app.panel.toggle_panel()
        return False

    _rumps_internal.NSApp.applicationShouldHandleReopen_hasVisibleWindows_ = (
        applicationShouldHandleReopen_hasVisibleWindows_
    )


def main():
    global _app
    _acquire_lock_or_exit()
    _patch_dock_reopen()
    _app = ScreenshotWindowApp()
    # NSPanel生成はメインスレッド必須なので run() 前に同期実行
    _app.setup()
    _app.run()


if __name__ == "__main__":
    main()
