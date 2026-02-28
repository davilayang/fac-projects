# syntax=docker/dockerfile:1

FROM python:3.13-slim

# Create non-root user early so we can chown the workdir
RUN addgroup --system app && adduser --system --ingroup app app

# uv settings:
#   UV_COMPILE_BYTECODE  — faster startup
#   UV_LINK_MODE=copy    — avoids hard-link issues across filesystems
#   UV_CACHE_DIR         — writable path for the non-root user
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/app/.cache/uv \
    HF_HOME=/app/.cache/huggingface \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install system libraries required by the LiveKit RTC native extension
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

# Install uv from the official distroless image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies before copying source (better layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application source and hand ownership to the app user
COPY . .
RUN chown -R app:app /app

USER app

# Download turn-detector model files from HuggingFace at build time
# so the container starts without needing network access to HF Hub.
RUN uv run agent.py download-files

CMD ["uv", "run", "agent.py", "start"]
