#!/bin/zsh
cd "/Users/xuzirui/Documents/Codex/2026-06-06/0-mvp-1-2-3-4" || exit 1

mkdir -p data

if [ -f data/server.pid ]; then
  old_pid=$(cat data/server.pid)
  if kill -0 "$old_pid" >/dev/null 2>&1; then
    echo "本亦运营后台已经在运行。"
    open "http://127.0.0.1:8000"
    echo ""
    echo "如果员工无法访问，请先双击「停止本亦运营后台.command」，再重新双击启动。"
    exit 0
  fi
fi

echo "正在启动本亦运营后台 V2..."
BENYI_HOST=0.0.0.0 nohup python3 server.py > data/server.log 2>&1 &
echo $! > data/server.pid

sleep 1
open "http://127.0.0.1:8000"

echo ""
echo "已启动。浏览器会自动打开：http://127.0.0.1:8000"
echo "现在可以关闭这个终端窗口，后台会继续运行。"
echo ""
echo "员工如果和你连接同一个 Wi-Fi，可以用下面的地址访问："
found_ip=0
for iface in en0 en1 en2; do
  ip=$(ipconfig getifaddr "$iface" 2>/dev/null)
  if [ -n "$ip" ]; then
    echo "http://$ip:8000"
    found_ip=1
  fi
done
if [ "$found_ip" = "0" ]; then
  echo "暂时没自动识别到 Wi-Fi IP。请打开 系统设置 > Wi-Fi > 详情 查看 IP 地址。"
  echo "员工访问格式：http://你的IP:8000"
fi
echo ""
echo "如果 Mac 弹出网络权限或防火墙提示，请选择允许。"
