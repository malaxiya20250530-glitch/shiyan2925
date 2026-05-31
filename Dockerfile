FROM python:3.13-slim

WORKDIR /app

# 纯标准库，无需 pip install
COPY hallucination_detector.py .
COPY awareness_gateway.py .
COPY observer_proxy.py .
COPY observer_security.py .
COPY alignment_middleware.py .
COPY feedback_store.py .
COPY feedback_dashboard.py .
COPY update_kb.py .
COPY logger.py .
COPY true_self_os.py .
COPY social_self_sim.py .
COPY config.json .
COPY kb_user.json .

# 初始化反馈数据库
RUN python3 -c "import feedback_store; feedback_store.init_db()"

EXPOSE 8800

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3 -c "from urllib.request import urlopen; urlopen('http://localhost:8800/health')" || exit 1

ENTRYPOINT ["python3", "awareness_gateway.py"]
CMD ["--mock"]
