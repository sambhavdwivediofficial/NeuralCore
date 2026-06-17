# infrastructure/docker/api.Dockerfile

FROM python:3.12-slim as builder

LABEL maintainer="Sambhav Dwivedi <sambhavdwivedi@outlook.com>"
LABEL description="NeuralCore API Builder"

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-prod.txt ./

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements-prod.txt

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

COPY --chown=neuralcore:neuralcore backend/ .

RUN mkdir -p /app/logs /app/cache /app/uploads && \
    chown -R neuralcore:neuralcore /app/logs /app/cache /app/uploads

RUN echo '#!/bin/bash\n\
set -e\n\
echo "NeuralCore API starting..."\n\
exec /opt/venv/bin/uvicorn main:app \\\n\
    --host 0.0.0.0 \\\n\
    --port 8000 \\\n\
    --workers $(python -c "import os; print(os.cpu_count() or 4)") \\\n\
    --timeout-keep-alive 65 \\\n\
    --timeout-notify 30\n\
' > /app/start.sh && chmod +x /app/start.sh

RUN echo '#!/bin/bash\n\
curl -f http://localhost:8000/health || exit 1\n\
' > /app/healthcheck.sh && chmod +x /app/healthcheck.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /app/healthcheck.sh

USER neuralcore

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV NEURALCORE_ENV=production
ENV LOG_LEVEL=info

EXPOSE 8000

ENTRYPOINT ["/app/start.sh"]

# Security labels
LABEL security.scan="enabled"
LABEL security.updates="weekly"
LABEL security.compliance="OWASP"
