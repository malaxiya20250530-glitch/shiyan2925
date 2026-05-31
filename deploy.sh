#!/bin/bash
# 觉察网关一键部署脚本
# 用法: bash deploy.sh [--port 8800] [--mock] [--ollama]

set -e

PORT="${PORT:-8800}"
MOCK="${MOCK:-false}"
UPSTREAM="${UPSTREAM:-http://localhost:11434/v1}"
MODEL="${MODEL:-llama3.2}"

echo "========================================"
echo "  觉察推理网关 — 一键部署"
echo "========================================"

# 检查 Python
if ! command -v python3 &>/dev/null; then
    echo "安装 Python3..."
    apt-get update -qq && apt-get install -y -qq python3 2>/dev/null || {
        echo "请手动安装 Python 3.10+"
        exit 1
    }
fi

# 安装项目
if ! python3 -c "import hallucination_detector" 2>/dev/null; then
    echo "安装觉察网关..."
    pip install git+https://github.com/malaxiya20250530-glitch/shiyan2925.git 2>/dev/null || {
        # fallback: 直接运行
        echo "直接运行模式..."
    }
fi

# 启动网关
echo ""
echo "启动网关..."
echo "  端口: $PORT"
echo "  模式: $([ "$MOCK" = "true" ] && echo 'Mock (无 LLM)' || echo "上游: $UPSTREAM")"
echo ""

if [ "$MOCK" = "true" ]; then
    python3 awareness_gateway.py --port "$PORT" --mock &
else
    python3 awareness_gateway.py --port "$PORT" --upstream "$UPSTREAM" --model "$MODEL" &
fi
PID=$!
sleep 2

# 检查
if curl -s "http://localhost:$PORT/health" | grep -q '"status":"ok"'; then
    echo ""
    echo "✅ 网关已启动: http://localhost:$PORT"
    echo ""
    echo "端点:"
    echo "  健康检查:  http://localhost:$PORT/health"
    echo "  OpenAI:    http://localhost:$PORT/v1/chat/completions"
    echo "  Ollama:    http://localhost:$PORT/api/chat"
    echo "  仪表盘:    http://localhost:$PORT/feedback"
    echo ""
    echo "PID: $PID — kill $PID 停止"
else
    echo "⚠️  健康检查失败，请查看日志"
fi

wait $PID
