import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from settings import (
    get_screenshot_location,
    set_screenshot_location,
    ensure_screenshot_location,
    restore_default,
)


def test_get_screenshot_location_returns_path():
    """defaults read の結果が Path で返る"""
    mock_result = MagicMock(stdout="/Users/test/Desktop\n", returncode=0)
    with patch("settings.subprocess.run", return_value=mock_result):
        result = get_screenshot_location()
    assert result == Path("/Users/test/Desktop")


def test_get_screenshot_location_returns_none_when_unset():
    """defaults read で未設定の場合 None"""
    mock_result = MagicMock(stdout="", returncode=1)
    with patch("settings.subprocess.run", return_value=mock_result):
        result = get_screenshot_location()
    assert result is None


def test_set_screenshot_location_writes_and_reloads():
    """set すると defaults write と SystemUIServer の再起動が走る"""
    target = Path("/Users/test/Pictures/スクショ窓口")
    with patch("settings.subprocess.run") as mock_run:
        set_screenshot_location(target)
    assert mock_run.call_count >= 2
    write_call = mock_run.call_args_list[0]
    assert "defaults" in write_call.args[0]
    assert "write" in write_call.args[0]
    assert str(target) in write_call.args[0]


def test_ensure_screenshot_location_creates_dir_and_sets(tmp_path):
    """ensure が呼ばれるとフォルダ作成 + defaults 設定"""
    target = tmp_path / "sw_test_ensure"
    with patch("settings.subprocess.run") as mock_run:
        ensure_screenshot_location(target)
    assert target.exists()
    assert mock_run.called


def test_restore_default_sets_desktop():
    """restore_default は ~/Desktop に保存先を戻す"""
    with patch("settings.subprocess.run") as mock_run:
        restore_default()
    write_call = mock_run.call_args_list[0]
    assert str(Path.home() / "Desktop") in write_call.args[0]
