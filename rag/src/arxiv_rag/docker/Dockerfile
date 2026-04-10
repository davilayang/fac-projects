# ── Stage 1: install dependencies ────────────────────────────────────────────
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install deps before copying source so this layer is cached on code changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project

# Download reranker model at build time so first request isn't slow.
RUN /app/.venv/bin/python -c \
    "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2', cache_folder='/opt/models')"

COPY src/ src/
COPY alembic.ini pyproject.toml uv.lock README.md ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# ── Stage 2: minimal runtime image ───────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv          /app/.venv
COPY --from=builder /opt/models         /opt/models
COPY --from=builder /app/src            /app/src
COPY --from=builder /app/alembic.ini    /app/alembic.ini

ENV PATH="/app/.venv/bin:$PATH" \
    RERANK_CACHE_DIR="/opt/models"

EXPOSE 8000

COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["arxiv-rag-api"]
