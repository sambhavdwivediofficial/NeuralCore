# infrastructure/docker/frontend.Dockerfile

FROM node:20-alpine as dependencies

LABEL maintainer="Sambhav Dwivedi <sambhavdwivedi@outlook.com>"
LABEL description="NeuralCore Frontend Dependencies"

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./

RUN npm ci --legacy-peer-deps

FROM node:20-alpine as builder

LABEL maintainer="Sambhav Dwivedi <sambhavdwivedi@outlook.com>"
LABEL description="NeuralCore Frontend Builder"

WORKDIR /app

COPY --from=dependencies /app/node_modules ./node_modules

COPY frontend/ .

ARG NODE_ENV=production
ENV NODE_ENV=$NODE_ENV
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_OPTIONS="--max-old-space-size=2048"

RUN npm run build

FROM node:20-alpine

LABEL version="1.0.0"
LABEL maintainer="Sambhav Dwivedi <sambhavdwivedi@outlook.com>"

RUN apk add --no-cache dumb-init curl

RUN addgroup -g 1000 neuralcore && \
    adduser -D -u 1000 -G neuralcore neuralcore

WORKDIR /app

COPY --from=builder --chown=neuralcore:neuralcore /app/.next ./.next
COPY --from=builder --chown=neuralcore:neuralcore /app/public ./public
COPY --from=builder --chown=neuralcore:neuralcore /app/package.json package.json
COPY --from=builder --chown=neuralcore:neuralcore /app/next.config.js next.config.js

COPY --from=builder --chown=neuralcore:neuralcore /app/node_modules ./node_modules

RUN echo '#!/bin/sh\n\
curl -f http://localhost:3000/health || exit 1\n\
' > /app/healthcheck.sh && chmod +x /app/healthcheck.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /app/healthcheck.sh

USER neuralcore

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000

EXPOSE 3000

ENTRYPOINT ["dumb-init", "--"]

CMD ["node_modules/.bin/next", "start"]

LABEL security.scan="enabled"
LABEL security.updates="weekly"
LABEL security.compliance="CSP"
