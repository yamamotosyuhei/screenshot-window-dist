#!/bin/bash
# エージェント連携ツール（lastshot / selfshot / lastdl）インストーラ
# やること:
#   1. 3つのコマンドを ~/bin/ にコピー
#   2. ~/bin にPATHが通っていなければ ~/.zshrc に1行追記
#   3. （任意）AIエージェント用の説明を ~/.claude/CLAUDE.md に追記
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/bin"

echo "=== スクショ窓口 エージェント連携ツール インストール ==="

# 1. ~/bin にコピー
mkdir -p "$BIN"
for t in lastshot selfshot lastdl; do
  if [ ! -f "$HERE/$t" ]; then
    echo "エラー: $HERE/$t が見つかりません（zipを丸ごと解凍していますか？）" >&2
    exit 1
  fi
  cp "$HERE/$t" "$BIN/$t"
  chmod +x "$BIN/$t"
  echo "✓ $BIN/$t"
done

# 2. PATH（人間がターミナルから打つ時用。エージェントはフルパスで呼ぶので必須ではない）
case ":$PATH:" in
  *":$BIN:"*) echo "✓ PATH設定済み（~/bin）" ;;
  *)
    if ! grep -qs 'export PATH="$HOME/bin:$PATH"' "$HOME/.zshrc"; then
      printf '\nexport PATH="$HOME/bin:$PATH"\n' >> "$HOME/.zshrc"
      echo "✓ ~/.zshrc にPATHを追記（新しいターミナルから有効）"
    else
      echo "✓ ~/.zshrc に追記済み（新しいターミナルから有効）"
    fi
    ;;
esac

# 3. Claude Code（AIエージェント）用の説明を CLAUDE.md に追記
SNIP="$HERE/CLAUDE_SNIPPET.md"
TARGET="$HOME/.claude/CLAUDE.md"
if [ -f "$SNIP" ]; then
  if [ -f "$TARGET" ] && grep -qs "lastshot" "$TARGET"; then
    echo "✓ CLAUDE.md は設定済み（lastshotの記述あり）"
  else
    printf "Claude Code用の設定を %s に追記しますか？ [y/N]: " "$TARGET"
    read -r ans
    if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
      mkdir -p "$HOME/.claude"
      # 先頭の「貼り付けてください」行を除いて追記
      { echo ""; tail -n +2 "$SNIP"; } >> "$TARGET"
      echo "✓ $TARGET に追記しました"
    else
      echo "スキップしました。あとで CLAUDE_SNIPPET.md の中身を手で貼り付けてもOKです"
    fi
  fi
fi

echo ""
echo "=== 完了。動作テスト ==="
if "$BIN/lastshot" >/dev/null 2>&1; then
  echo "✓ lastshot: $("$BIN/lastshot" | head -1)"
else
  echo "・lastshot: まだスクショがありません（⌘+Shift+4 で撮ると入ります）"
fi
echo "・selfshot / lastdl も同様に使えます"
