# ── Stage 1: install dependencies ────────────────────────────────────────────
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Copy workspace layout for dependency resolution
COPY pyproject.toml uv.lock ./
COPY packages/db/pyproject.toml packages/db/pyproject.toml
COPY services/api/pyproject.toml services/api/pyproject.toml

# Stub src dirs so uv sync can resolve workspace members
RUN mkdir -p packages/db/src/db services/api/src/arxiv_rag && \
    touch packages/db/src/db/__init__.py services/api/src/arxiv_rag/__init__.py

# Install deps before copying source so this layer is cached on code changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Download reranker model at build time so first request isn't slow.
RUN /app/.venv/bin/python -c \
    "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2', cache_dir='/opt/models')"

# Copy actual source
COPY packages/db/src/ packages/db/src/
COPY services/api/src/ services/api/src/
COPY services/api/alembic.ini services/api/alembic.ini

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# ── Stage 2: minimal runtime image ───────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv                    /app/.venv
COPY --from=builder /opt/models                   /opt/models
COPY --from=builder /app/packages/db/src          /app/packages/db/src
COPY --from=builder /app/services/api/src         /app/services/api/src
COPY --from=builder /app/services/api/alembic.ini /app/services/api/alembic.ini

ENV PATH="/app/.venv/bin:$PATH" \
    RERANK_CACHE_DIR="/opt/models"

EXPOSE 8000

COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["arxiv-rag-api"]
