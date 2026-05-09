"""Pillowでサムネ生成・キャッシュ管理"""
import hashlib
import sys
from pathlib import Path
from PIL import Image, ImageDraw

import paths

THUMB_MAX_SIZE = (320, 240)  # Retina想定で大きめ

# Pillow 9.1+ は Image.Resampling.LANCZOS、9.0以前は Image.LANCZOS
try:
    _RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:
    _RESAMPLE = Image.LANCZOS


def _cache_path(src: Path) -> Path:
    """キャッシュファイルのパス。同名ファイル衝突回避のためフルパスでハッシュ"""
    digest = hashlib.md5(str(src.resolve()).encode()).hexdigest()[:12]
    return paths.CACHE_DIR / f"{src.stem}_{digest}.png"


def generate(src: Path) -> Path:
    """サムネを生成（または既存キャッシュを返す）"""
    paths.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out = _cache_path(src)

    if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
        return out

    try:
        with Image.open(src) as img:
            img.thumbnail(THUMB_MAX_SIZE, _RESAMPLE)
            img.save(out, "PNG")
    except Exception as e:
        sys.stderr.write(f"[thumbnail] failed for {src}: {type(e).__name__}: {e}\n")
        _make_placeholder(out)

    return out


def cleanup(src: Path) -> None:
    """サムネキャッシュを削除"""
    out = _cache_path(src)
    if out.exists():
        out.unlink()


def _make_placeholder(out: Path) -> None:
    """サムネ生成失敗時のプレースホルダ画像（?マーク）"""
    img = Image.new("RGB", THUMB_MAX_SIZE, (60, 60, 60))
    draw = ImageDraw.Draw(img)
    # シンプルに ? を中央に描画
    draw.text(
        (THUMB_MAX_SIZE[0] // 2 - 10, THUMB_MAX_SIZE[1] // 2 - 20),
        "?",
        fill=(180, 180, 180),
    )
    img.save(out, "PNG")
