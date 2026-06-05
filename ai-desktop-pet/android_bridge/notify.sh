#!/data/data/com.termux/files/usr/bin/bash
# 快捷通知脚本 —— 宠物向用户发送提醒
TITLE="${1:-桌面精灵}"
CONTENT="${2:-嗨，该休息一下啦~ 🐾}"
termux-notification --title "$TITLE" --content "$CONTENT" --priority high
echo "📬 $TITLE: $CONTENT"
