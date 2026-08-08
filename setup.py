"""配布用 py2app 設定（フルビルド：Python本体・依存ライブラリすべて同梱）"""
from setuptools import setup

APP = ['main.py']
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'icon.icns',
    'plist': {
        'CFBundleName': 'スクショ窓口',
        'CFBundleDisplayName': 'スクショ窓口',
        # 社長専用版と衝突しないように Bundle ID を分ける
        'CFBundleIdentifier': 'com.shimesapo.screenshot-window-dist',
        'CFBundleVersion': '1.1',
        'CFBundleShortVersionString': '1.1',
        'LSUIElement': False,  # Dockにも表示（メニューバーアイコンも維持）
        'NSAppleEventsUsageDescription': '通知ダイアログを表示します',
        'NSHumanReadableCopyright': '© 2026 shimesapo',
    },
    'packages': ['rumps'],
    'includes': ['PIL', 'watchdog', 'objc'],
}

setup(
    app=APP,
    name='スクショ窓口',
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
