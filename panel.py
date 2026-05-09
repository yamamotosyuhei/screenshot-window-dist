"""PyObjC NSPanel：サムネ3列グリッド・検索・ドラッグ&ドロップ・削除UI"""
import objc
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict

from AppKit import (
    NSPanel, NSView, NSImageView, NSImage, NSTextField, NSButton,
    NSScrollView, NSColor, NSMakeRect, NSSize,
    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable, NSWindowStyleMaskResizable,
    NSWindowStyleMaskHUDWindow, NSWindowStyleMaskUtilityWindow,
    NSWindowStyleMaskBorderless,
    NSBackingStoreBuffered, NSPasteboard,
    NSDragOperationCopy,
    NSTrackingArea, NSTrackingMouseEnteredAndExited, NSTrackingActiveInKeyWindow,
    NSBezierPath, NSFont, NSAttributedString, NSWorkspace,
    NSTextAlignmentCenter,
    NSEvent, NSScreen,
)
from Foundation import NSObject, NSURL, NSArray, NSMakePoint

import index

PANEL_WIDTH = 500
PANEL_HEIGHT = 600
THUMB_SIZE = NSSize(140, 105)
LABEL_HEIGHT = 16
CELL_HEIGHT = THUMB_SIZE.height + LABEL_HEIGHT  # サムネ + 日時ラベル
GRID_GAP = 10
GRID_PADDING = 12
COLUMNS = 3
SEARCH_BAR_HEIGHT = 36
TOP_BUTTON_HEIGHT = 32  # 一括削除ボタン用


class DraggableImageView(NSImageView):
    """ドラッグ&ドロップ + ホバー削除ボタン + ダブルクリック Quick Look"""

    def initWithFilePath_(self, file_path):
        self = objc.super(DraggableImageView, self).initWithFrame_(
            NSMakeRect(0, 0, THUMB_SIZE.width, THUMB_SIZE.height)
        )
        if self is None:
            return None
        self._file_path = file_path
        self._hover = False
        opts = NSTrackingMouseEnteredAndExited | NSTrackingActiveInKeyWindow
        ta = NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
            self.bounds(), opts, self, None
        )
        self.addTrackingArea_(ta)
        return self

    def mouseEntered_(self, event):
        self._hover = True
        self.setNeedsDisplay_(True)
        panel = self.window().delegate()
        if panel is not None and hasattr(panel, "show_preview"):
            panel.show_preview(self._file_path)

    def mouseExited_(self, event):
        self._hover = False
        self.setNeedsDisplay_(True)
        panel = self.window().delegate()
        if panel is not None and hasattr(panel, "hide_preview"):
            panel.hide_preview()

    def drawRect_(self, rect):
        objc.super(DraggableImageView, self).drawRect_(rect)

        # 選択中なら青枠
        panel = self.window().delegate()
        if panel is not None and hasattr(panel, "is_path_selected"):
            if panel.is_path_selected(self._file_path):
                NSColor.colorWithCalibratedRed_green_blue_alpha_(0.25, 0.6, 1.0, 1.0).set()
                border = NSBezierPath.bezierPathWithRect_(self.bounds())
                border.setLineWidth_(4)
                border.stroke()

        # ホバー時の × ボタン
        if not self._hover:
            return
        btn_size = 20
        btn_x = self.bounds().size.width - btn_size - 4
        btn_y = self.bounds().size.height - btn_size - 4
        NSColor.colorWithCalibratedWhite_alpha_(0.0, 0.7).set()
        NSBezierPath.bezierPathWithOvalInRect_(
            NSMakeRect(btn_x, btn_y, btn_size, btn_size)
        ).fill()
        font = NSFont.boldSystemFontOfSize_(14)
        attrs = {"NSFont": font, "NSColor": NSColor.whiteColor()}
        NSAttributedString.alloc().initWithString_attributes_("×", attrs).drawAtPoint_(
            NSMakePoint(btn_x + 5, btn_y + 1)
        )

    def mouseDown_(self, event):
        loc = self.convertPoint_fromView_(event.locationInWindow(), None)
        btn_size = 20
        btn_x = self.bounds().size.width - btn_size - 4
        btn_y = self.bounds().size.height - btn_size - 4
        if (btn_x <= loc.x <= btn_x + btn_size and
            btn_y <= loc.y <= btn_y + btn_size):
            self._delete_clicked()
            return
        if event.clickCount() == 2:
            subprocess.Popen(["qlmanage", "-p", self._file_path])
            return
        # シングルクリック → 選択処理（modifier に応じて単独/トグル/追加）
        panel = self.window().delegate()
        if panel is not None and hasattr(panel, "handle_thumbnail_click"):
            panel.handle_thumbnail_click(self._file_path, int(event.modifierFlags()))

    def mouseDragged_(self, event):
        # 複数選択中で、ドラッグ元が選択に含まれていれば全パスを送る
        panel = self.window().delegate()
        paths_to_drag = [self._file_path]
        if panel is not None and hasattr(panel, "get_selected_paths"):
            selected = panel.get_selected_paths()
            if self._file_path in selected and len(selected) > 1:
                paths_to_drag = selected
        urls = [NSURL.fileURLWithPath_(p) for p in paths_to_drag]
        pasteboard = NSPasteboard.pasteboardWithName_("NSDragPboard")
        pasteboard.clearContents()
        pasteboard.writeObjects_(NSArray.arrayWithArray_(urls))
        image = self.image()
        self.dragImage_at_offset_event_pasteboard_source_slideBack_(
            image, NSMakePoint(0, 0), NSSize(0, 0), event, pasteboard, self, True
        )

    def draggingSourceOperationMaskForLocal_(self, is_local):
        return NSDragOperationCopy

    @objc.python_method
    def _delete_clicked(self):
        # ×を押されたサムネが複数選択に含まれていれば、選択中の全部を削除
        panel = self.window().delegate()
        if panel is not None and hasattr(panel, "get_selected_paths"):
            selected = panel.get_selected_paths()
            if self._file_path in selected and len(selected) > 1 and hasattr(panel, "delete_selected"):
                panel.delete_selected()
                return
        # 単独削除
        from pathlib import Path as _Path
        import index as _index
        if _Path(self._file_path).exists():
            url = NSURL.fileURLWithPath_(self._file_path)
            NSWorkspace.sharedWorkspace().recycleURLs_completionHandler_([url], None)
        _index.remove_entry(self._file_path)
        if panel and hasattr(panel, "refresh_panel"):
            panel.refresh_panel(panel.search_field.stringValue())


class ScreenshotPanel(NSObject):
    """サムネグリッド表示用のNSPanel"""

    def init(self):
        self = objc.super(ScreenshotPanel, self).init()
        if self is None:
            return None

        # HUD + Utility でダークな半透明パネル
        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskResizable
            | NSWindowStyleMaskHUDWindow
            | NSWindowStyleMaskUtilityWindow
        )
        self.window = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, PANEL_WIDTH, PANEL_HEIGHT),
            style,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("スクショ窓口")
        self.window.setLevel_(25)  # NSStatusWindowLevel: メニューバーと同じ高さで前面固定
        self.window.setHidesOnDeactivate_(False)  # 他アプリにフォーカスが移っても隠れない
        self.window.setReleasedWhenClosed_(False)
        self.window.setDelegate_(self)

        content = self.window.contentView()

        # 一括削除ボタン（最上段）
        button_y = PANEL_HEIGHT - TOP_BUTTON_HEIGHT - 4
        self.clear_all_button = NSButton.alloc().initWithFrame_(
            NSMakeRect(GRID_PADDING, button_y, PANEL_WIDTH - 2 * GRID_PADDING, TOP_BUTTON_HEIGHT - 4)
        )
        self.clear_all_button.setTitle_("🗑  窓口を全部ゴミ箱に送る")
        self.clear_all_button.setBezelStyle_(1)  # NSBezelStyleRounded
        self.clear_all_button.setTarget_(self)
        self.clear_all_button.setAction_("clearAllClicked:")
        content.addSubview_(self.clear_all_button)

        # 検索ボックス（ボタンの下）
        search_y = PANEL_HEIGHT - TOP_BUTTON_HEIGHT - SEARCH_BAR_HEIGHT - 6
        self.search_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(GRID_PADDING, search_y, PANEL_WIDTH - 2 * GRID_PADDING, 28)
        )
        self.search_field.setPlaceholderString_("🔍 検索（ファイル名・日付）")
        self.search_field.setDelegate_(self)
        content.addSubview_(self.search_field)

        # スクロールビュー（ボタン+検索バーの下、下端まで）
        scroll_height = PANEL_HEIGHT - TOP_BUTTON_HEIGHT - SEARCH_BAR_HEIGHT - 12
        self.scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(0, 0, PANEL_WIDTH, scroll_height)
        )
        self.scroll.setHasVerticalScroller_(True)
        self.scroll.setBorderType_(0)
        content.addSubview_(self.scroll)

        # グリッドビュー
        self.grid = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, PANEL_WIDTH, 0))
        self.scroll.setDocumentView_(self.grid)

        # ホバープレビュー用ウィンドウ（最初の表示時に遅延生成）
        self._preview_window = None
        # 撮影通知ウィンドウ
        self._notif_window = None
        self._notif_seq = 0  # 連続撮影時に古いタイマーを無効化するためのシーケンス
        # 複数選択中のファイルパス
        self._selected_paths = set()

        self.refresh_panel()
        return self

    @objc.python_method
    def refresh_panel(self, query: str = ""):
        """インデックスからサムネを並べ直す"""
        # ホバープレビューを閉じる（サムネ破棄でmouseExited_が発火しないケース対応）
        self.hide_preview()
        # 既存ビューをクリア
        for sub in list(self.grid.subviews()):
            sub.removeFromSuperview()

        entries = index.search(query) if query else index.get_all()
        # 既に存在しなくなったパスを選択から除外
        existing_paths = {e["path"] for e in entries}
        self._selected_paths &= existing_paths
        rows = (len(entries) + COLUMNS - 1) // COLUMNS
        grid_height = rows * (CELL_HEIGHT + GRID_GAP) + GRID_PADDING * 2
        self.grid.setFrame_(NSMakeRect(0, 0, PANEL_WIDTH, max(grid_height, 100)))

        for i, entry in enumerate(entries):
            col = i % COLUMNS
            row = i // COLUMNS
            x = GRID_PADDING + col * (THUMB_SIZE.width + GRID_GAP)
            cell_top = grid_height - GRID_PADDING - row * (CELL_HEIGHT + GRID_GAP)
            thumb_y = cell_top - THUMB_SIZE.height
            label_y = thumb_y - LABEL_HEIGHT
            self._add_thumbnail(entry, x, thumb_y, label_y)

    @objc.python_method
    def _add_thumbnail(self, entry: Dict, x: float, thumb_y: float, label_y: float):
        # サムネ本体
        thumb_path = entry["thumbnail"]
        view = DraggableImageView.alloc().initWithFilePath_(entry["path"])
        view.setFrame_(NSMakeRect(x, thumb_y, THUMB_SIZE.width, THUMB_SIZE.height))
        img = NSImage.alloc().initWithContentsOfFile_(thumb_path)
        if img:
            view.setImage_(img)
        view.setImageScaling_(2)  # NSImageScaleProportionallyDown
        self.grid.addSubview_(view)

        # 撮影日時ラベル（"05/08 14:17" 形式）
        label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(x, label_y, THUMB_SIZE.width, LABEL_HEIGHT)
        )
        label.setStringValue_(_format_captured_at(entry.get("captured_at", "")))
        label.setEditable_(False)
        label.setSelectable_(False)
        label.setBordered_(False)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setFont_(NSFont.systemFontOfSize_(10))
        label.setTextColor_(NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.65))
        label.setAlignment_(NSTextAlignmentCenter)
        self.grid.addSubview_(label)

    def controlTextDidChange_(self, notification):
        """検索ボックス入力時のコールバック（NSTextField delegate）"""
        query = self.search_field.stringValue()
        self.refresh_panel(query)

    def clearAllClicked_(self, sender):
        """一括削除ボタン（NSButton action）"""
        self.confirm_and_delete_all()

    @objc.python_method
    def confirm_and_delete_all(self) -> None:
        """rumps.alert で確認 → delete_all（ゴミ箱送り、復元可能）"""
        import rumps as _rumps
        total = len(index.get_all())
        if total == 0:
            _rumps.alert(title="スクショ窓口", message="窓口は既に空です。")
            return
        response = _rumps.alert(
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
        self.delete_all()

    @objc.python_method
    def show_panel(self):
        from AppKit import NSApp
        self.refresh_panel(self.search_field.stringValue())
        self.window.center()
        NSApp.activateIgnoringOtherApps_(True)
        self.window.makeKeyAndOrderFront_(None)
        self.window.orderFrontRegardless()

    @objc.python_method
    def hide_panel(self):
        self.window.orderOut_(None)

    @objc.python_method
    def is_panel_visible(self) -> bool:
        return bool(self.window.isVisible())

    @objc.python_method
    def toggle_panel(self):
        if self.is_panel_visible():
            self.hide_panel()
        else:
            self.show_panel()

    @objc.python_method
    def show_preview(self, file_path: str) -> None:
        """マウスホバー時に原寸寄りの画像を別ウィンドウで表示"""
        img = NSImage.alloc().initWithContentsOfFile_(file_path)
        if img is None:
            return

        # 表示サイズ：最大 700x525 にアスペクト比維持で収める（拡大はしない）
        img_size = img.size()
        if img_size.width <= 0 or img_size.height <= 0:
            return
        max_w, max_h = 700.0, 525.0
        ratio = min(max_w / img_size.width, max_h / img_size.height, 1.0)
        new_w = max(int(img_size.width * ratio), 1)
        new_h = max(int(img_size.height * ratio), 1)

        # プレビューウィンドウを遅延生成
        if self._preview_window is None:
            self._preview_window = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(0, 0, new_w, new_h),
                NSWindowStyleMaskBorderless,
                NSBackingStoreBuffered,
                False,
            )
            self._preview_window.setLevel_(26)  # メインパネル(25)より上
            self._preview_window.setHidesOnDeactivate_(False)
            self._preview_window.setIgnoresMouseEvents_(True)  # クリックは下のサムネに通す
            self._preview_window.setHasShadow_(True)
            self._preview_window.setOpaque_(False)
            self._preview_window.setBackgroundColor_(NSColor.clearColor())

        # 画像ビューを毎回作り直してセット
        iv = NSImageView.alloc().initWithFrame_(NSMakeRect(0, 0, new_w, new_h))
        iv.setImage_(img)
        iv.setImageScaling_(2)  # NSImageScaleProportionallyDown
        self._preview_window.setContentSize_(NSSize(new_w, new_h))
        self._preview_window.setContentView_(iv)

        # マウス位置の右下に配置。画面端では反対側にフリップ
        mouse = NSEvent.mouseLocation()
        screen = NSScreen.mainScreen()
        sf = screen.frame() if screen else NSMakeRect(0, 0, 1920, 1080)

        x = mouse.x + 16
        y = mouse.y - new_h - 16
        if x + new_w > sf.origin.x + sf.size.width:
            x = mouse.x - new_w - 16
        if y < sf.origin.y:
            y = mouse.y + 16

        self._preview_window.setFrameOrigin_(NSMakePoint(x, y))
        self._preview_window.orderFront_(None)

    @objc.python_method
    def hide_preview(self) -> None:
        if self._preview_window is not None:
            self._preview_window.orderOut_(None)

    @objc.python_method
    def is_path_selected(self, file_path: str) -> bool:
        return file_path in self._selected_paths

    @objc.python_method
    def get_selected_paths(self) -> list:
        return list(self._selected_paths)

    @objc.python_method
    def clear_selection(self) -> None:
        if not self._selected_paths:
            return
        self._selected_paths.clear()
        for sub in list(self.grid.subviews()):
            sub.setNeedsDisplay_(True)

    @objc.python_method
    def handle_thumbnail_click(self, file_path: str, modifier_flags: int) -> None:
        """サムネクリック時：modifier に応じて選択状態を更新"""
        NSEventModifierFlagShift = 1 << 17
        NSEventModifierFlagCommand = 1 << 20
        has_cmd = bool(modifier_flags & NSEventModifierFlagCommand)
        has_shift = bool(modifier_flags & NSEventModifierFlagShift)

        if has_cmd:
            # Cmd+クリック：トグル
            if file_path in self._selected_paths:
                self._selected_paths.discard(file_path)
            else:
                self._selected_paths.add(file_path)
        elif has_shift:
            # Shift+クリック：追加（範囲選択は簡易的に追加扱い）
            self._selected_paths.add(file_path)
        else:
            # 通常クリック：単独選択
            self._selected_paths.clear()
            self._selected_paths.add(file_path)

        # 全サムネを再描画（選択枠の更新）
        for sub in list(self.grid.subviews()):
            sub.setNeedsDisplay_(True)

    @objc.python_method
    def delete_selected(self) -> None:
        """選択中のすべてをゴミ箱送り + index削除"""
        if not self._selected_paths:
            return
        urls = []
        for p in list(self._selected_paths):
            if Path(p).exists():
                urls.append(NSURL.fileURLWithPath_(p))
            index.remove_entry(p)
        if urls:
            NSWorkspace.sharedWorkspace().recycleURLs_completionHandler_(urls, None)
        self._selected_paths.clear()
        self.refresh_panel(self.search_field.stringValue())

    @objc.python_method
    def delete_all(self) -> int:
        """窓口の全エントリをゴミ箱送り。送った件数を返す（ゴミ箱から復元可能）"""
        entries = index.get_all()
        if not entries:
            return 0
        urls = []
        for e in entries:
            p = e["path"]
            if Path(p).exists():
                urls.append(NSURL.fileURLWithPath_(p))
            index.remove_entry(p)
        if urls:
            NSWorkspace.sharedWorkspace().recycleURLs_completionHandler_(urls, None)
        self._selected_paths.clear()
        self.refresh_panel(self.search_field.stringValue())
        return len(entries)

    @objc.python_method
    def show_notification(self, file_path: str) -> None:
        """撮影直後のフローティング通知を画面右下に1秒表示"""
        try:
            import paths as _p
            with open(_p.LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} | NOTIF show {Path(file_path).name}\n")
        except Exception:
            pass
        img = NSImage.alloc().initWithContentsOfFile_(file_path)
        if img is None:
            return

        notif_w, notif_h = 280, 90

        # 既存通知があれば再利用（連続撮影時のチラつき防止）
        if self._notif_window is None:
            self._notif_window = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(0, 0, notif_w, notif_h),
                NSWindowStyleMaskBorderless,
                NSBackingStoreBuffered,
                False,
            )
            self._notif_window.setLevel_(27)  # プレビュー(26)より更に上
            self._notif_window.setHidesOnDeactivate_(False)
            self._notif_window.setIgnoresMouseEvents_(True)
            self._notif_window.setHasShadow_(True)
            self._notif_window.setOpaque_(False)
            self._notif_window.setBackgroundColor_(
                NSColor.colorWithCalibratedWhite_alpha_(0.12, 0.92)
            )

        # 内容ビューを毎回作り直す
        content = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, notif_w, notif_h))

        # サムネ画像（左、80x60）
        thumb_iv = NSImageView.alloc().initWithFrame_(NSMakeRect(10, 15, 80, 60))
        thumb_iv.setImage_(img)
        thumb_iv.setImageScaling_(2)
        content.addSubview_(thumb_iv)

        # タイトル
        title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(100, 50, notif_w - 110, 22)
        )
        title.setStringValue_("📸 撮影されました")
        title.setEditable_(False)
        title.setSelectable_(False)
        title.setBordered_(False)
        title.setBezeled_(False)
        title.setDrawsBackground_(False)
        title.setFont_(NSFont.boldSystemFontOfSize_(13))
        title.setTextColor_(NSColor.whiteColor())
        content.addSubview_(title)

        # ファイル名
        filename = NSTextField.alloc().initWithFrame_(
            NSMakeRect(100, 22, notif_w - 110, 20)
        )
        filename.setStringValue_(Path(file_path).name)
        filename.setEditable_(False)
        filename.setSelectable_(False)
        filename.setBordered_(False)
        filename.setBezeled_(False)
        filename.setDrawsBackground_(False)
        filename.setFont_(NSFont.systemFontOfSize_(10))
        filename.setTextColor_(
            NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.7)
        )
        content.addSubview_(filename)

        self._notif_window.setContentSize_(NSSize(notif_w, notif_h))
        self._notif_window.setContentView_(content)

        # 画面右下に配置
        screen = NSScreen.mainScreen()
        sf = screen.frame() if screen else NSMakeRect(0, 0, 1920, 1080)
        x = sf.origin.x + sf.size.width - notif_w - 20
        y = sf.origin.y + 60
        self._notif_window.setFrameOrigin_(NSMakePoint(x, y))
        self._notif_window.orderFront_(None)

        # 1秒後に消す（連続撮影で前のタイマーは無効化、daemon=Trueでアプリ終了時に止まる）
        self._notif_seq += 1
        my_seq = self._notif_seq
        timer = threading.Timer(1.0, self._delayed_hide_notification, args=(my_seq,))
        timer.daemon = True
        timer.start()

    @objc.python_method
    def _delayed_hide_notification(self, seq: int) -> None:
        """タイマー満了後に呼ばれる。最新のタイマー以外は無視"""
        try:
            import paths as _p
            with open(_p.LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} | NOTIF hide seq={seq} cur={self._notif_seq}\n")
        except Exception:
            pass
        if seq != self._notif_seq:
            return
        from AppKit import NSOperationQueue
        NSOperationQueue.mainQueue().addOperationWithBlock_(
            lambda: self._notif_window.orderOut_(None)
            if self._notif_window is not None
            else None
        )


def _format_captured_at(iso: str) -> str:
    """ISO日時文字列を 'MM/DD HH:MM' に整形。失敗したら元文字列の先頭16字"""
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%m/%d %H:%M")
    except (ValueError, TypeError):
        return iso[:16] if iso else ""
