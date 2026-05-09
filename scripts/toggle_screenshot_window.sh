#!/bin/bash
# スクショ窓口アプリのパネル開閉トグル（BTT用）
# アプリが起動していればフラグファイルを作成し、アプリ側のタイマーが検知してトグルする
FLAG="$HOME/Library/Caches/スクショ窓口/.toggle_request"
if pgrep -f "スクショ窓口" >/dev/null; then
    mkdir -p "$(dirname "$FLAG")"
    touch "$FLAG"
fi
