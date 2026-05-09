"""スクショ窓口で使うパス定数。テスト時は環境変数で上書き可能"""
import os
from pathlib import Path

HOME = Path.home()

# テスト時に環境変数で上書き可能
def _resolve(env_key: str, default: Path) -> Path:
    val = os.environ.get(env_key)
    return Path(val) if val else default

SCREENSHOT_DIR = _resolve("SW_SCREENSHOT_DIR", HOME / "Pictures" / "スクショ窓口")
CACHE_DIR = _resolve("SW_CACHE_DIR", HOME / "Library" / "Caches" / "スクショ窓口")
SUPPORT_DIR = _resolve("SW_SUPPORT_DIR", HOME / "Library" / "Application Support" / "スクショ窓口")
INDEX_PATH = SUPPORT_DIR / "index.json"
LOG_PATH = HOME / "bin" / "screenshot_window.log"
