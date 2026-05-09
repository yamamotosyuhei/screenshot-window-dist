"""macOSスクショ保存先（com.apple.screencapture location）の取得・設定・復元"""
import subprocess
from pathlib import Path
from typing import Optional


def get_screenshot_location() -> Optional[Path]:
    """現在の保存先を取得。未設定なら None"""
    result = subprocess.run(
        ["defaults", "read", "com.apple.screencapture", "location"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip()).expanduser()


def set_screenshot_location(target: Path) -> None:
    """保存先を target に変更し、SystemUIServer をリロード"""
    subprocess.run(
        ["defaults", "write", "com.apple.screencapture", "location", str(target)],
        check=True,
    )
    subprocess.run(["killall", "SystemUIServer"], check=False)


def ensure_screenshot_location(target: Path) -> None:
    """フォルダを作成し、保存先を target に設定（既に同じなら何もしない）"""
    target.mkdir(parents=True, exist_ok=True)
    current = get_screenshot_location()
    if current != target:
        set_screenshot_location(target)


def restore_default() -> None:
    """保存先をデスクトップに戻す（アンインストール時用）"""
    set_screenshot_location(Path.home() / "Desktop")


def set_show_thumbnail(enabled: bool) -> None:
    """macOSスクショ撮影直後のサムネイルプレビュー表示を切り替える。
    False にすると撮影 → 即ファイル保存 になる（プレビュー待ちの遅延が消える）"""
    value = "true" if enabled else "false"
    subprocess.run(
        ["defaults", "write", "com.apple.screencapture", "show-thumbnail", "-bool", value],
        check=True,
    )
    subprocess.run(["killall", "SystemUIServer"], check=False)


def get_show_thumbnail() -> bool:
    """現在の show-thumbnail 設定を取得。未設定（macOSデフォルト）は True"""
    result = subprocess.run(
        ["defaults", "read", "com.apple.screencapture", "show-thumbnail"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return True
    return result.stdout.strip() == "1"
