import sys
import time
from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def thumb_module(tmp_path, monkeypatch):
    monkeypatch.setenv("SW_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("SW_SUPPORT_DIR", str(tmp_path / "support"))
    monkeypatch.setenv("SW_SCREENSHOT_DIR", str(tmp_path / "shots"))
    sys.path.insert(0, str(Path(__file__).parent.parent))
    for m in list(sys.modules):
        if m in ("paths", "thumbnail"):
            del sys.modules[m]
    import thumbnail
    return thumbnail


def _make_png(path: Path, size=(800, 600), color=(200, 100, 50)):
    img = Image.new("RGB", size, color)
    img.save(path)


def test_generate_creates_thumbnail(thumb_module, tmp_path):
    src = tmp_path / "shot.png"
    _make_png(src)
    out = thumb_module.generate(src)
    assert out.exists()
    with Image.open(out) as img:
        # 横幅は最大320px
        assert img.size[0] <= 320
        assert img.size[1] <= 240


def test_generate_keeps_aspect_ratio(thumb_module, tmp_path):
    src = tmp_path / "shot.png"
    _make_png(src, size=(1600, 400))  # 4:1
    out = thumb_module.generate(src)
    with Image.open(out) as img:
        ratio = img.size[0] / img.size[1]
        assert abs(ratio - 4.0) < 0.1


def test_cache_hit_avoids_regeneration(thumb_module, tmp_path):
    src = tmp_path / "shot.png"
    _make_png(src)
    out1 = thumb_module.generate(src)
    mtime1 = out1.stat().st_mtime
    out2 = thumb_module.generate(src)
    assert out1 == out2
    assert out2.stat().st_mtime == mtime1  # 再生成されてない


def test_regenerate_when_source_modified(thumb_module, tmp_path):
    src = tmp_path / "shot.png"
    _make_png(src, color=(200, 100, 50))
    out1 = thumb_module.generate(src)
    mtime1 = out1.stat().st_mtime
    time.sleep(0.05)  # mtime解像度のため
    _make_png(src, color=(50, 100, 200))  # ソース書き換え
    out2 = thumb_module.generate(src)
    assert out2.stat().st_mtime > mtime1  # 再生成されている


def test_corrupted_file_returns_placeholder(thumb_module, tmp_path):
    src = tmp_path / "broken.png"
    src.write_bytes(b"not an image")
    out = thumb_module.generate(src)
    assert out.exists()
    # プレースホルダはPNGとして開ける
    with Image.open(out) as img:
        assert img.size[0] > 0


def test_cleanup_removes_thumbnail(thumb_module, tmp_path):
    src = tmp_path / "shot.png"
    _make_png(src)
    out = thumb_module.generate(src)
    assert out.exists()
    thumb_module.cleanup(src)
    assert not out.exists()
