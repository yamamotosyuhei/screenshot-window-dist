# スクショ窓口

撮ったスクリーンショットが自動で集まるメニューバーアプリ。
サムネで一覧 → ホバーで拡大プレビュー → ドラッグ＆ドロップで Discord / Slack / メール等にそのまま送れる。

## できること

- macOSの `⌘+Shift+3` `⌘+Shift+4` で撮ったスクショが自動で**「窓口」に集約**される
- メニューバーの 🖼️ アイコン or **Dockのアプリアイコンクリック**で開閉
- サムネに **マウスを乗せると原寸プレビュー**
- サムネを **ドラッグして他のアプリにドロップ** で送れる（Discord / Slack / メール / Finder 等）
- **Cmd + クリックで複数選択** → ドラッグで一括送信、× で一括削除
- パネル上部の **「🗑 窓口を全部ゴミ箱に送る」ボタン**で全クリア（確認ダイアログあり、ゴミ箱から復元可能）
- サムネ右上の **× ボタン**で1枚ずつゴミ箱へ
- サムネを **ダブルクリック** で macOS Quick Look の全画面プレビュー
- 検索ボックスでファイル名・日付絞り込み
- 撮影直後に画面右下に1秒だけ通知
- データは全部ローカル（クラウド送信なし）

---

## インストール（最短3ステップ）

### 1. zip を解凍
ダウンロードした `スクショ窓口.zip` をダブルクリックして解凍 → `スクショ窓口.app` が出てくる。

### 2. アプリケーションフォルダに移動
`スクショ窓口.app` を `アプリケーション`（`/Applications`）フォルダにドラッグ。

### 3. 初回起動（重要：「右クリック → 開く」）
`/Applications/スクショ窓口.app` を **右クリック → 「開く」** をクリック。

> **macOS のセキュリティ警告**：
> 「開発元が未確認のアプリ」と出ますが、**「開く」を選択**してOK。
> （これは Apple の有料署名（年額$99）を取得していないだけで、安全なアプリです）

⚠ ダブルクリックでの初回起動は警告が出るだけで開きません。**必ず右クリック→開くで初回起動**してください。
2回目以降はダブルクリック / Spotlight / Dock のいずれでも起動できます。

---

## 初回起動時の同意ダイアログ

起動すると次のダイアログが出ます：

> スクショ窓口へようこそ。
> アプリの動作のため、次の2点をmacOSに設定します:
> ・スクリーンショット保存先 → ~/Pictures/スクショ窓口/
> ・撮影直後の純正プレビュー → 無効（即ファイル保存に切り替え）
> 設定しますか？

**「設定する」を押すとアプリが使えるようになります。**

「設定しない」を押すとアプリは起動しません（このアプリはこの設定が前提のため）。
不安な場合は、後述の「**何が変更されるか**」を読んでから判断してください。
**いつでもメニューの「アンインストール」から元に戻せます。**

---

## 操作方法

| 操作 | やり方 |
|:---|:---|
| 窓口を開く / 閉じる | メニューバー 🖼️ → 「窓口を開く」 / Dockアイコンをクリック |
| サムネを見る | パネル内のサムネにマウスを乗せる → 大きく表示 |
| 他アプリに送る | サムネをドラッグして対象アプリにドロップ |
| **複数選択** | Cmd + クリック（トグル）／ Shift + クリック（追加） |
| **複数まとめて送る** | 複数選択した状態でどれか1枚をドラッグ |
| 1枚削除 | サムネの右上 × ボタン |
| **複数まとめて削除** | 複数選択 → どれかの × をクリック |
| 全部ゴミ箱に送る | パネル最上部の「🗑 窓口を全部ゴミ箱に送る」ボタン |
| 全画面プレビュー | サムネをダブルクリック（macOS Quick Look） |
| 検索 | パネル上部の 🔍 入力欄にファイル名 or 日付を入力 |
| 選択を解除 | 別の場所のサムネを通常クリック |

---

## ホットキー（オプション）

メニューバークリックの代わりに、好きなキーで窓口を開閉したい場合：

1. [BetterTouchTool](https://folivora.ai/) または [Karabiner-Elements](https://karabiner-elements.pqrs.org/) などをインストール
2. お好みのキー（例：`⌘+Shift+P`）に **シェルスクリプト実行** を割り当て
3. コマンド：
   ```
   touch "$HOME/Library/Caches/スクショ窓口/.toggle_request"
   ```

これで設定したキーで窓口が開閉します。

---

## 何が変更されるか（透明性）

| 項目 | 変更前 | 変更後 |
|:---|:---|:---|
| `defaults read com.apple.screencapture location` | デスクトップ | `~/Pictures/スクショ窓口/` |
| `defaults read com.apple.screencapture show-thumbnail` | true | false |

この2つを `defaults write` で変更します。**システムに勝手にインストールされるものはありません。**

---

## アンインストール

メニューバー 🖼️ → **「アンインストール（macOS設定を戻す）」** をクリック → 「実行」を選ぶ。

これで：
- スクショ保存先がデスクトップに戻る
- 撮影直後プレビューが復活
- アプリが終了

その後、`/Applications/スクショ窓口.app` を手動でゴミ箱へドラッグして完了。

完全に消したい場合は次のフォルダも削除：
- `~/Pictures/スクショ窓口/`（過去のスクショ）
- `~/Library/Caches/スクショ窓口/`（サムネキャッシュ）
- `~/Library/Application Support/スクショ窓口/`（インデックスJSON）

---

## トラブルシューティング

### Q1. 「開発元が未確認」で起動できない
**A.** `/Applications/スクショ窓口.app` を **右クリック → 「開く」** で初回起動してください。

それでも開かない場合：
- システム設定 → プライバシーとセキュリティ → 「このまま開く」ボタンをクリック

### Q2. 撮影しても窓口に入らない
**A.** メニューの「保存先設定を確認」をクリック → `~/Pictures/スクショ窓口/` と一致しているか確認。
ずれていれば、メニューの「終了」 → アプリ再起動で自動修正されます。

それでも直らない場合、ターミナルで：
```
defaults write com.apple.screencapture location ~/Pictures/スクショ窓口
killall SystemUIServer
```

### Q3. 窓口が表示されない
**A.** メニューバー 🖼️ → 「窓口を開く」 / Dockアイコンクリック / `⌘+Shift+P`（設定済みなら）。
それでも出ない場合、メニュー → 「終了」 → アプリ再起動。

### Q4. 削除したくないのに撮ったスクショが消えた
**A.** 削除（× ボタン / 全クリアボタン）はゴミ箱に送るだけです。Finder のゴミ箱から復元できます。

### Q5. macOS の元のスクショ動作（デスクトップ保存・撮影直後プレビュー）に戻したい
**A.** メニュー → 「アンインストール（macOS設定を戻す）」を実行。
これで `defaults` がリセットされます。

### Q6. 既に起動中で2重起動の警告が出る
**A.** これは正常動作。1つだけ起動するよう PIDロック で制御しています。
古いプロセスが残っている場合は、ターミナルで：
```
pkill -f "スクショ窓口"
rm -f ~/Library/Caches/スクショ窓口/.pid
```

### Q7. アプリがクラッシュする
**A.** ログ `~/bin/screenshot_window.log` を確認してください（無ければ作成されます）。
このファイルを開発者に送れば原因特定できます。

---

## 動作環境

- macOS 13 (Ventura) 以降推奨（macOS 25 / Tahoe で開発）
- Apple Silicon / Intel 両対応
- ストレージ：アプリ本体 約75MB、サムネキャッシュ 約1MB / 100枚
- 必要権限：なし（フォルダ書き込みは ~/Pictures, ~/Library 内のみ）

---

## Claude Code / AI による自動セットアップ

このREADMEを Claude Code や ChatGPT などの AI ツールに読み込ませてセットアップを自動化できます。**人間が GUI で「右クリック→開く」する代わりに、ターミナルでコマンド実行で完結**します。

### 前提条件
- `スクショ窓口配布.zip` が `~/Downloads/` にダウンロード済み
- macOS 13 (Ventura) 以降
- 管理者パスワード不要（`/Applications` 書き込み可能な前提）

### 自動セットアップ手順

以下のコマンドを順番に実行してください。AIツールに「このREADMEを読んで実行して」と頼めば、これを順に走らせます。

```bash
# 1. zip 解凍
cd ~/Downloads && unzip -o スクショ窓口配布.zip

# 2. /Applications にインストール（既存があれば上書き）
[ -d /Applications/スクショ窓口.app ] && rm -rf /Applications/スクショ窓口.app
cp -R ~/Downloads/スクショ窓口配布/スクショ窓口.app /Applications/

# 3. Gatekeeper の quarantine 属性を削除（「右クリック→開く」と同等の効果）
xattr -dr com.apple.quarantine /Applications/スクショ窓口.app

# 4. アプリ起動
open /Applications/スクショ窓口.app

# 5. プロセス確認（成功すれば PID と app パスが返る）
sleep 3 && pgrep -fl "スクショ窓口.app"
```

### 初回起動の同意ダイアログを自動で「設定する」にする

`open` 直後に「スクショ窓口へようこそ」ダイアログが出ます。手動で「設定する」を押すか、以下のコマンドで自動押下します（**同意の意思がある場合のみ実行**）：

```bash
# AppleScript で Return キー押下（デフォルトボタン=「設定する」を押す）
sleep 2 && osascript -e 'tell application "System Events" to keystroke return'
```

### 動作確認

```bash
# 保存先設定が変更されたか
defaults read com.apple.screencapture location
# 期待値: /Users/<USER>/Pictures/スクショ窓口

# 撮影直後プレビューが無効になったか
defaults read com.apple.screencapture show-thumbnail
# 期待値: 0

# テスト撮影（screencapture コマンドで擬似スクショ）
screencapture -x ~/Pictures/スクショ窓口/test_capture.png
sleep 2

# インデックスに反映されたか
cat ~/Library/Application\ Support/スクショ窓口/index.json
# JSONに test_capture.png が含まれていれば成功
```

### BTT などでホットキー設定（オプション）

ホットキーは **手動で BetterTouchTool 等の設定が必要** です（Claude Code が直接設定はできない）。
任意のキーに以下のシェルスクリプトを割り当てると、そのキーで窓口を開閉できます：

```bash
touch "$HOME/Library/Caches/スクショ窓口/.toggle_request"
```

### 完全アンインストール

```bash
# 1. アプリ終了
pkill -f "スクショ窓口" 2>/dev/null

# 2. macOS設定を元に戻す
defaults write com.apple.screencapture location ~/Desktop
defaults write com.apple.screencapture show-thumbnail -bool true
killall SystemUIServer

# 3. アプリとアプリデータを削除
rm -rf /Applications/スクショ窓口.app
rm -rf ~/Library/Caches/スクショ窓口
rm -rf ~/Library/Application\ Support/スクショ窓口

# 注意: ~/Pictures/スクショ窓口/ には撮影済みのファイルがあります。
# 必要に応じて手動でゴミ箱へ移動してください：
# mv ~/Pictures/スクショ窓口 ~/.Trash/
```

### トラブル時の自動診断コマンド

```bash
# 状態スナップショット（Claude Code に貼って原因相談する用）
echo "=== プロセス ==="; pgrep -fl "スクショ窓口"
echo "=== 保存先 ==="; defaults read com.apple.screencapture location 2>&1
echo "=== プレビュー設定 ==="; defaults read com.apple.screencapture show-thumbnail 2>&1
echo "=== ログ末尾 ==="; tail -20 ~/bin/screenshot_window.log 2>&1 || echo "ログなし"
echo "=== インデックス件数 ==="; python3 -c "import json; print(len(json.load(open('$HOME/Library/Application Support/スクショ窓口/index.json'))))" 2>&1
echo "=== 保存先のファイル数 ==="; ls ~/Pictures/スクショ窓口/ 2>&1 | wc -l
```

---

## ライセンス・配布元

著作権：© 2026 shimesapo

依存ライブラリのライセンス：
- rumps (MIT) / pyobjc (MIT) / Pillow (HPND) / watchdog (Apache 2.0)

無保証で配布。使用は自己責任で。
