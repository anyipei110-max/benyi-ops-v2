#!/bin/zsh
cd "/Users/xuzirui/Documents/Codex/2026-06-06/0-mvp-1-2-3-4" || exit 1

if [ ! -f data/server.pid ]; then
  echo "没有找到正在运行的本亦运营后台。"
  exit 0
fi

pid=$(cat data/server.pid)
if kill -0 "$pid" >/dev/null 2>&1; then
  kill "$pid"
  rm -f data/server.pid
  echo "本亦运营后台已停止。"
else
  rm -f data/server.pid
  echo "后台没有运行，已清理旧记录。"
fi
