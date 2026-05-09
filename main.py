#!/usr/bin/env python3
"""スクショ窓口 メニューバーアプリ（配布版）"""
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
# 初回セットアップ完了フラグ（同意ダイアログを2回目以降出さないため）
SETUP_FLAG = paths.SUPPORT_DIR / "setup_completed.flag"


def _acquire_lock_or_exit() -> None:
    """既存プロセスが生きていれば終了する。生きていなければPIDを書いてロック取得"""
    paths.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if PID_LOCK.exists():
        try:
            old_pid = int(PID_LOCK.read_text().strip())
            os.kill(old_pid, 0)
            print(f"既に起動中（PID {old_pid}）。新規起動を中止します。")
            sys.exit(0)
        except (ValueError, ProcessLookupError, PermissionError):
            pass
    PID_LOCK.write_text(str(os.getpid()))


def log(msg: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{now} | {msg}"
    print(line)
    paths.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(paths.LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _show_setup_dialog() -> bool:
    """初回起動時の同意ダイアログ。「設定する」=True"""
    msg = (
        "スクショ窓口へようこそ。\\n\\n"
        "アプリの動作のため、次の2点をmacOSに設定します:\\n"
        "・スクリーンショット保存先 → ~/Pictures/スクショ窓口/\\n"
        "・撮影直後の純正プレビュー → 無効（即ファイル保存に切り替え）\\n\\n"
        "メニューの「アンインストール」からいつでも元に戻せます。\\n\\n"
        "設定しますか？"
    )
    result = subprocess.run(
        ["osascript", "-e",
         f'display dialog "{msg}" buttons {{"設定しない", "設定する"}} '
         f'default button "設定する" with title "スクショ窓口 初回設定"'],
        capture_output=True, text=True
    )
    return "設定する" in result.stdout


class ScreenshotWindowApp(rumps.App):
    def __init__(self):
        super().__init__("🖼️", quit_button=None)
        self.menu = [
            rumps.MenuItem("窓口を開く", callback=self.toggle_panel),
            None,
            rumps.MenuItem("保存先フォルダを開く", callback=self.open_folder),
            rumps.MenuItem("保存先設定を確認", callback=self.check_settings),
            None,
            rumps.MenuItem("アンインストール（macOS設定を戻す）", callback=self.uninstall),
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

        # 起動時に古いフラグが残ってたら消す
        if TOGGLE_FLAG.exists():
            try:
                TOGGLE_FLAG.unlink()
            except OSError:
                pass

        # 初回セットアップ：同意ダイアログ
        if not SETUP_FLAG.exists():
            log("初回起動：同意ダイアログを表示")
            if not _show_setup_dialog():
                log("ユーザーが設定を辞退 → アプリ終了")
                if PID_LOCK.exists():
                    try:
                        PID_LOCK.unlink()
                    except OSError:
                        pass
                sys.exit(0)
            # 同意 → 設定実行
            log("初回セットアップ：保存先変更 + 純正プレビュー無効化")
            settings.set_screenshot_location(paths.SCREENSHOT_DIR)
            if settings.get_show_thumbnail():
                settings.set_show_thumbnail(False)
            SETUP_FLAG.write_text("done")
        else:
            # 2回目以降：設定がずれてたら直す（同意ダイアログは出さない）
            current = settings.get_screenshot_location()
            if current != paths.SCREENSHOT_DIR:
                log(f"スクショ保存先を再設定: {current} → {paths.SCREENSHOT_DIR}")
                settings.set_screenshot_location(paths.SCREENSHOT_DIR)
            if settings.get_show_thumbnail():
                log("純正プレビューを無効化")
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

        # トグル要求の監視タイマー開始
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

    def uninstall(self, _):
        """macOS設定を元に戻す。アプリ自体の削除は手動で /Applications から"""
        msg = (
            "macOSの設定を元に戻します:\\n"
            "・スクリーンショット保存先 → デスクトップ\\n"
            "・撮影直後の純正プレビュー → 有効\\n\\n"
            "実行後、アプリを終了します。\\n"
            "アプリ本体は /Applications から手動でゴミ箱へ移動してください。\\n\\n"
            "実行しますか？"
        )
        result = subprocess.run(
            ["osascript", "-e",
             f'display dialog "{msg}" buttons {{"キャンセル", "実行"}} '
             f'default button "キャンセル" with title "アンインストール"'],
            capture_output=True, text=True
        )
        if "実行" not in result.stdout:
            return
        try:
            settings.restore_default()
            settings.set_show_thumbnail(True)
        except Exception as e:
            log(f"アンインストール処理エラー: {e}")
        if SETUP_FLAG.exists():
            try:
                SETUP_FLAG.unlink()
            except OSError:
                pass
        log("アンインストール完了 → アプリ終了")
        self.quit_app(None)

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
    """rumps内部のNSApplicationDelegateにDockクリック検知を注入（クリックでパネルトグル）"""
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
    _app.setup()
    _app.run()


if __name__ == "__main__":
    main()
