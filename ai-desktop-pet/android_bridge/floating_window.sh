#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# AI桌面精灵 · Android 悬浮窗管理脚本
# 通过 Termux:API 控制通知、传感器等系统功能
# ============================================================

ACTION="$1"
shift

case "$ACTION" in
    notify)
        # 发送系统通知: floating_window.sh notify "标题" "内容"
        termux-notification --title "$1" --content "$2"
        echo "通知已发送: $1"
        ;;
    notify-persistent)
        # 发送常驻通知（宠物后台运行标识）
        termux-notification \
            --id "desktop-pet" \
            --title "🐾 桌面精灵" \
            --content "正在运行中..." \
            --ongoing \
            --priority high
        ;;
    notify-remove)
        termux-notification-remove "desktop-pet"
        echo "常驻通知已移除"
        ;;
    clipboard)
        # 读取/设置剪贴板
        if [ -z "$1" ]; then
            termux-clipboard-get
        else
            echo "$1" | termux-clipboard-set
            echo "已复制到剪贴板: $1"
        fi
        ;;
    screenshot)
        # 截屏: floating_window.sh screenshot [保存路径]
        SAVE_PATH="${1:-$HOME/ai-desktop-pet/screenshots/shot_$(date +%s).png}"
        mkdir -p "$(dirname "$SAVE_PATH")"
        termux-screenshot "$SAVE_PATH"
        echo "截图已保存: $SAVE_PATH"
        ;;
    volume)
        # 音量控制: floating_window.sh volume [0-15]
        VOL="${1:-7}"
        media volume --set "$VOL"
        echo "音量已设置为: $VOL"
        ;;
    brightness)
        # 亮度控制: floating_window.sh brightness [0-255]
        BRI="${1:-128}"
        settings put system screen_brightness "$BRI"
        echo "亮度已设置为: $BRI"
        ;;
    battery)
        # 获取电池信息
        termux-battery-status
        ;;
    sensor)
        # 读取传感器 (light/pressure/proximity 等)
        SENSOR_TYPE="${1:-light}"
        termux-sensor -s "$SENSOR_TYPE" -n 1
        ;;
    toast)
        # 显示 Toast
        termux-toast "$1"
        ;;
    open-url)
        # 打开 URL
        termux-open-url "$1"
        ;;
    *)
        echo "用法: $0 <动作> [参数]"
        echo ""
        echo "动作:"
        echo "  notify <标题> <内容>       发送系统通知"
        echo "  notify-persistent           发送常驻通知（后台标识）"
        echo "  notify-remove               移除常驻通知"
        echo "  clipboard [文本]            读取或设置剪贴板"
        echo "  screenshot [路径]           截屏"
        echo "  volume <0-15>              调节音量"
        echo "  brightness <0-255>         调节亮度"
        echo "  battery                    查看电池状态"
        echo "  sensor <类型>              读取传感器"
        echo "  toast <文本>              显示 Toast"
        echo "  open-url <URL>             打开链接"
        ;;
esac
