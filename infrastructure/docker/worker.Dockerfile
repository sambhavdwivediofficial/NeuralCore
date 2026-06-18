# infrastructure/docker/worker.Dockerfile

# Stage 1: Builder — Python dependencies
FROM python:3.12-slim as builder

LABEL maintainer="Sambhav Dwivedi <sambhavdwivedi@outlook.com>"
LABEL description="NeuralCore Worker Builder"

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-worker.txt ./

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir \
    celery[redis,amqp]==5.4.0 \
    -r requirements-worker.txt

# Stage 2: Runtime
FROM python:3.12-slim

LABEL version="1.0.0"
LABEL maintainer="Sambhav Dwivedi <sambhavdwivedi@outlook.com>"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libssl3 \
    curl \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN useradd -m -u 1000 -s /sbin/nologin neuralcore

WORKDIR /app

COPY --from=builder --chown=neuralcore:neuralcore /opt/venv /opt/venv

COPY --chown=neuralcore:neuralcore backend/task_queue/ ./worker
COPY --chown=neuralcore:neuralcore backend/settings.py ./

RUN mkdir -p /app/logs && chown -R neuralcore:neuralcore /app/logs

RUN echo '#!/bin/bash\n\
set -e\n\
echo "NeuralCore Worker starting..."\n\
exec /opt/venv/bin/celery -A workers.tasks worker \\\n\
    --loglevel=$LOG_LEVEL \\\n\
    --concurrency=$(python -c "import os; print(max(2, os.cpu_count() or 4))") \\\n\
    --pool=prefork \\\n\
    --max-tasks-per-child=1000 \\\n\
    --time-limit=3600 \\\n\
    --soft-time-limit=3300 \\\n\
    --without-gossip \\\n\
    --without-mingle \\\n\
    -Ofair\n\
' > /app/start.sh && chmod +x /app/start.sh

RUN echo '#!/bin/bash\n\
/opt/venv/bin/celery -A workers.tasks inspect active || exit 1\n\
' > /app/healthcheck.sh && chmod +x /app/healthcheck.sh

HEALTHCHECK --interval=60s --timeout=15s --start-period=30s --retries=3 \
    CMD /app/healthcheck.sh

USER neuralcore

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV CELERY_BROKER_URL=redis://redis:6379/0
ENV CELERY_RESULT_BACKEND=redis://redis:6379/1
ENV LOG_LEVEL=info
ENV NEURALCORE_ENV=production

ENTRYPOINT ["/app/start.sh"]

LABEL security.scan="enabled"
LABEL security.updates="weekly"
