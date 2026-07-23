# Agente de cotação (desafio Namastex) — app/main.py
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/domains:/app/services/svc-orchestrator/src

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app ./app
COPY domains ./domains
COPY services/svc-orchestrator/src ./services/svc-orchestrator/src
COPY quote-service/data/plans.json ./quote-service/data/plans.json

EXPOSE 8100
RUN mkdir -p /data && useradd -r -u 10001 appuser && chown -R appuser:appuser /app /data
ENV AUDIT_DB_PATH=/data/audit.db
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
