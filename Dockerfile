FROM python:3.13-slim

LABEL org.opencontainers.image.title="觉察推理网关"
LABEL org.opencontainers.image.description="零依赖 LLM 幻觉检测网关 — 架在任何模型前面的觉察层"
LABEL org.opencontainers.image.version="2.3"

WORKDIR /app

# ── 系统依赖 ──
RUN apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends \
        tesseract-ocr tesseract-ocr-chi-sim \
        curl ca-certificates \
        2>/dev/null || echo "Tesseract 中文包不可用" && \
    rm -rf /var/lib/apt/lists/*

# ── 核心引擎 ──
COPY hallucination_detector.py .
COPY awareness_gateway.py .
COPY alignment_middleware.py .

# ── 观察器 ──
COPY observer_proxy.py .
COPY observer_security.py .
COPY knowledge_graph.py .
COPY compiled_awareness.py .

# ── 知识 & 检索 ──
COPY vector_kb.py .
COPY web_verifier.py .
COPY fuzzy_matcher.py .

# ── 共识 & 度量 ──
COPY consensus_engine.py .
COPY awareness_metrics.py .
COPY ml_consensus.py .

# ── 生产就绪 ──
COPY backpressure.py .
COPY rate_limiter.py .
COPY webhook_dispatcher.py .
COPY trace_exporter.py .
COPY prometheus_exporter.py .
COPY benchmark.py .

# ── 飞轮 ──
COPY feedback_collector.py .
COPY feedback_store.py .
COPY auto_kb_updater.py .

# ── 工具 ──
COPY feedback_dashboard.py .
COPY update_kb.py .
COPY logger.py .
COPY ocr_handler.py .
COPY langchain_plugin.py .
COPY encrypt_source.py .
COPY stress_test.py .

# ── 配置 ──
COPY config.json .
COPY kb_user.json .

# ── 初始化 ──
RUN python3 -c "import feedback_store; feedback_store.init_db()" && \
    python3 -c "import hallucination_detector; print('预加载完成')"

EXPOSE 8800 8801 9090

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -sf http://localhost:8800/health || exit 1

ENTRYPOINT ["python3", "awareness_gateway.py"]
CMD ["--mock"]
