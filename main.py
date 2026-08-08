#!/usr/bin/env python3
"""スクショ窓口 メニューバーアプリ（配布版）"""
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
# 初回セットアップ完了フラグ（同意ダイアログを2回目以降出さないため）
SETUP_FLAG = paths.SUPPORT_DIR / "setup_completed.flag"


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


def _show_setup_dialog() -> bool:
    """初回起動時の同意ダイアログ。rumps.alert（NSAlert）でメインスレッド安全。「設定する」=True"""
    response = rumps.alert(
        title="スクショ窓口 初回設定",
        message=(
            "スクショ窓口へようこそ。\n\n"
            "アプリの動作のため、次の2点をmacOSに設定します:\n"
            "・スクリーンショット保存先 → ~/Pictures/スクショ窓口/\n"
            "・撮影直後の純正プレビュー → 無効（即ファイル保存に切り替え）\n\n"
            "メニューの「アンインストール」からいつでも元に戻せます。\n\n"
            "設定しますか？"
        ),
        ok="設定する",
        cancel="設定しない",
    )
    return response == 1


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
            rumps.MenuItem("アンインストール（macOS設定を戻す）", callback=self.uninstall),
            rumps.MenuItem("終了", callback=self.quit_app),
        ]
        self.panel = None
        self.watcher = None
        self._toggle_timer = rumps.Timer(self._check_toggle_flag, 0.5)

    def setup(self):
        # フォルダ準備（致命的：失敗したら終了）
        try:
            paths.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            paths.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            paths.SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log(f"フォルダ準備失敗: {type(e).__name__}: {e}")
            rumps.alert(
                title="スクショ窓口 — 起動エラー",
                message=(
                    f"必要なフォルダの作成に失敗しました。\n\n"
                    f"{type(e).__name__}: {e}\n\n"
                    f"~/Pictures、~/Library/Caches、~/Library/Application Support の書き込み権限を確認してください。"
                ),
            )
            rumps.quit_application()
            return

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
            # 同意 → 設定実行（失敗してもアプリは起動を続ける）
            log("初回セットアップ：保存先変更 + 純正プレビュー無効化")
            try:
                settings.set_screenshot_location(paths.SCREENSHOT_DIR)
                if settings.get_show_thumbnail():
                    settings.set_show_thumbnail(False)
                SETUP_FLAG.write_text("done")
            except Exception as e:
                log(f"初回セットアップの macOS設定変更失敗: {type(e).__name__}: {e}")
                rumps.alert(
                    title="スクショ窓口 — macOS設定の変更に失敗",
                    message=(
                        f"macOSの設定変更でエラーが起きました。\n\n"
                        f"{type(e).__name__}: {e}\n\n"
                        f"アプリ自体は起動しますが、撮影したスクショは自動で窓口に入りません。\n"
                        f"後でメニューの「保存先設定を確認」から状態を見られます。"
                    ),
                )
        else:
            # 2回目以降：設定がずれてたら直す（同意ダイアログは出さない）
            try:
                current = settings.get_screenshot_location()
                if current != paths.SCREENSHOT_DIR:
                    log(f"スクショ保存先を再設定: {current} → {paths.SCREENSHOT_DIR}")
                    settings.set_screenshot_location(paths.SCREENSHOT_DIR)
                if settings.get_show_thumbnail():
                    log("純正プレビューを無効化")
                    settings.set_show_thumbnail(False)
            except Exception as e:
                log(f"macOS設定の同期失敗: {type(e).__name__}: {e}")
                # 致命ではないので続行

        # パネル作成（致命的：失敗したら終了）
        try:
            self.panel = ScreenshotPanel.alloc().init()
        except Exception as e:
            import traceback
            log(f"パネル作成失敗: {type(e).__name__}: {e}")
            log(traceback.format_exc())
            rumps.alert(
                title="スクショ窓口 — 起動エラー",
                message=(
                    f"パネルの初期化に失敗しました。\n\n"
                    f"{type(e).__name__}: {e}\n\n"
                    f"このメッセージを開発者に伝えてください。"
                ),
            )
            rumps.quit_application()
            return

        # ファイル監視開始（非致命：失敗してもメニュー操作は可能）
        try:
            self.watcher = Watcher(
                on_change=self._on_files_changed,
                on_added=self._on_file_added,
            )
            self.watcher.initial_scan()
            self.watcher.start()
        except Exception as e:
            import traceback
            log(f"ファイル監視起動失敗: {type(e).__name__}: {e}")
            log(traceback.format_exc())
            rumps.alert(
                title="スクショ窓口 — 一部機能エラー",
                message=(
                    f"ファイル監視の起動に失敗しました。\n\n"
                    f"{type(e).__name__}: {e}\n\n"
                    f"撮影したスクショの自動取り込みは動きませんが、\n"
                    f"~/Pictures/スクショ窓口/ に手動でファイルを置けば次回起動時に取り込まれます。"
                ),
            )
            self.watcher = None

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

    def confirm_clear_all(self, _):
        """窓口の全エントリをゴミ箱送り（rumps.alert で確認、復元可能）"""
        log("メニュー: 全クリア押下")
        if self.panel is None:
            return
        import index
        try:
            total = len(index.get_all())
        except Exception as e:
            log(f"index.get_all 失敗: {e}")
            rumps.alert(title="スクショ窓口", message=f"インデックス読み込みに失敗しました:\n{e}")
            return
        if total == 0:
            rumps.alert(title="スクショ窓口", message="窓口は既に空です。")
            return
        response = rumps.alert(
            title="全部ゴミ箱に送る",
            message=(
                f"窓口の {total} 件すべてをゴミ箱に送ります。\n"
                f"（macOSのゴミ箱から復元できます）\n\n"
                f"実行しますか？"
            ),
            ok="実行",
            cancel="キャンセル",
        )
        if response != 1:
            return
        try:
            sent = self.panel.delete_all()
            log(f"窓口を全クリア: {sent}件をゴミ箱送り")
        except Exception as e:
            import traceback
            log(f"ERROR delete_all: {type(e).__name__}: {e}")
            log(traceback.format_exc())
            rumps.alert(title="スクショ窓口", message=f"削除中にエラーが発生しました:\n{e}")

    def uninstall(self, _):
        """macOS設定を元に戻す。アプリ自体の削除は手動で /Applications から"""
        response = rumps.alert(
            title="アンインストール",
            message=(
                "macOSの設定を元に戻します:\n"
                "・スクリーンショット保存先 → デスクトップ\n"
                "・撮影直後の純正プレビュー → 有効\n\n"
                "実行後、アプリを終了します。\n"
                "アプリ本体は /Applications から手動でゴミ箱へ移動してください。\n\n"
                "実行しますか？"
            ),
            ok="実行",
            cancel="キャンセル",
        )
        if response != 1:
            return
        try:
            settings.restore_default()
            settings.set_show_thumbnail(True)
        except Exception as e:
            log(f"アンインストール処理エラー: {e}")
            rumps.alert(
                title="スクショ窓口",
                message=(
                    f"macOS設定の復元中にエラーが起きました:\n{e}\n\n"
                    f"設定を手動で戻す場合：\n"
                    f"defaults write com.apple.screencapture location ~/Desktop\n"
                    f"defaults write com.apple.screencapture show-thumbnail -bool true\n"
                    f"killall SystemUIServer"
                ),
            )
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
    # 二重起動防止（致命的：失敗したら exit）
    try:
        _acquire_lock_or_exit()
    except SystemExit:
        raise
    except Exception as e:
        log(f"PIDロック取得失敗: {type(e).__name__}: {e}")
        sys.exit(1)

    # Dockクリックパッチ（非致命：失敗してもメニューバーは使える）
    try:
        _patch_dock_reopen()
    except Exception as e:
        log(f"Dockクリックパッチ失敗（メニューバーから操作可能）: {type(e).__name__}: {e}")

    # アプリ本体（致命的）
    try:
        _app = ScreenshotWindowApp()
        _app.setup()
        _app.run()
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        log(f"未捕捉エラー: {type(e).__name__}: {e}")
        log(traceback.format_exc())
        try:
            rumps.alert(
                title="スクショ窓口 — 致命エラー",
                message=(
                    f"{type(e).__name__}: {e}\n\n"
                    f"ログ: {paths.LOG_PATH}\n"
                    f"このメッセージを開発者に伝えてください。"
                ),
            )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
