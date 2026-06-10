# infrastructure/docker/rust_engine.Dockerfile

FROM rust:1.75-slim as builder

LABEL maintainer="Sambhav Dwivedi <sambhavdwivedi@outlook.com>"
LABEL description="NeuralCore Rust Engine Builder"

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libssl-dev \
    libssl3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY rust_engine/Cargo.toml rust_engine/Cargo.lock ./

RUN mkdir -p src && echo "fn main() {}" > src/main.rs && \
    cargo build --release --features cli,compression,simd,python-bindings 2>&1 | grep -v "warning:" || true && \
    rm -rf src

COPY rust_engine/src ./src
COPY rust_engine/benches ./benches

RUN cargo build --release \
    --features cli,compression,simd,python-bindings \
    -j $(nproc) \
    && strip target/release/neuralcore_engine_cli

RUN pip install maturin && \
    maturin build --release --strip -j $(nproc)

FROM debian:bookworm-slim

LABEL version="1.0.0"
LABEL maintainer="Sambhav Dwivedi <sambhavdwivedi@outlook.com>"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libssl3 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN useradd -m -u 1000 -s /sbin/nologin neuralcore

WORKDIR /app

COPY --from=builder --chown=neuralcore:neuralcore /build/target/release/neuralcore_engine_cli /app/engine

COPY --from=builder --chown=neuralcore:neuralcore /build/target/criterion /app/benchmarks

RUN echo '#!/bin/bash\n/app/engine info > /dev/null 2>&1 && exit 0 || exit 1' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh

USER neuralcore

ENV RUST_LOG=info
ENV RUST_BACKTRACE=1
ENV OMP_NUM_THREADS=auto

EXPOSE 9090

ENTRYPOINT ["/app/engine"]
CMD ["info"]

LABEL security.scan="enabled"
LABEL security.updates="weekly"
