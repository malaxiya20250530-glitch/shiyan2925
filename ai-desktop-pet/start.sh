#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# 🐾 AI虚拟桌面精灵 · 一键启动脚本
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

echo "╔══════════════════════════════════════════╗"
echo "║     🐾 AI 虚拟桌面精灵 v1.0             ║"
echo "║     Unity 3D + LLM + 手机自动化         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ─── 检查环境 ───

echo "🔍 环境检查..."

# 检查 Python
if ! command -v python3 &>/dev/null; then
    echo "  ✗ python3 未找到，请先安装: pkg install python"
    exit 1
fi
echo "  ✓ Python: $(python3 --version)"

# 检查 Termux:API
if command -v termux-notification &>/dev/null; then
    echo "  ✓ Termux:API 可用"
    AUTOMATION_ENABLED="true"
else
    echo "  ⚠ Termux:API 不可用，自动化功能将禁用"
    echo "    安装: pkg install termux-api (Termux) + Termux:API APK"
    AUTOMATION_ENABLED="false"
fi

# 检查 OpenAI API Key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "  ⚠ OPENAI_API_KEY 未设置"
    echo "    设置: export OPENAI_API_KEY=\"sk-...\""
    echo "    将使用模拟模式运行..."
    export OPENAI_API_KEY="mock-key-for-demo"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ─── 创建必要目录 ───
mkdir -p "$SCRIPT_DIR/screenshots"

# ─── 发送常驻通知 ───
if [ "$AUTOMATION_ENABLED" = "true" ]; then
    bash "$SCRIPT_DIR/android_bridge/floating_window.sh" notify-persistent 2>/dev/null
fi

# ─── 启动后端服务 ───
echo "🚀 启动 AI 后端服务..."
echo "   WebSocket: ws://127.0.0.1:9527"
echo "   LLM 模型: ${LLM_MODEL:-gpt-4o-mini}"
echo "   情绪引擎: 就绪"
echo "   自动化: $([ "$AUTOMATION_ENABLED" = "true" ] && echo '启用' || echo '禁用')"
echo ""
echo "📱 请确保 Unity APK 已安装并启动"
echo "   连接地址: ws://127.0.0.1:9527"
echo ""
echo "按 Ctrl+C 停止服务"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$BACKEND_DIR"
python3 pet_server.py

# ─── 清理 ───
if [ "$AUTOMATION_ENABLED" = "true" ]; then
    bash "$SCRIPT_DIR/android_bridge/floating_window.sh" notify-remove 2>/dev/null
fi
echo "🐾 桌面精灵已休眠，再见~"
