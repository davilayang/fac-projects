# RAG — Document Ingestion Pipeline

arXiv document ingestion, chunking, and embedding pipeline using Prefect, PostgreSQL, and pymupdf4llm.

See [architecture.md](./architecture.md) for detailed design and database schema.

## Prerequisites

- Python >= 3.12
- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
# Install dependencies
uv sync
```

### Local Development

First, set up `.env` from `.env.example`, then start the Prefect cluster:

```bash
cp .env.example .env
# Fill in your credentials

# Build and start cluster (Postgres, Redis, Prefect server, worker, and creates "local-pool" work pool)
docker compose up --build

# In a separate terminal, initialise the database (uses the cluster's Postgres)
uv run poe db-setup
```

- Prefect UI: http://localhost:4200
- Stop the cluster with `Ctrl-C`, then tear down:

```bash
docker compose down --volumes
```

## Deploying & Running Flows

**Deploy all flows** in `/flows`:

This registers flows defined in `flows/deploy.py` with the cluster (metadata only).
The worker container mounts the project directory, so local code changes are
picked up on the next run without restarting or redeploying.

```bash
uv run --env-file .env poe deploy
# If "Work pool 'local-pool' not found", wait a moment and retry
```

**Trigger a flow run:**

- **Option A:** Prefect UI at http://localhost:4200 → Deployments → select flow → Run → Quick Run
- **Option B:** CLI (single run, bypasses the deployment):
  ```bash
  # Arxiv ingestion: search, download, and track papers
  uv run --env-file .env python -m flows.arxiv_search
  
  # Extraction: process local PDFs to markdown
  uv run --env-file .env python -m flows.extraction
  ```

### Arxiv Ingestion Flow

Searches arxiv for papers, downloads PDFs into `data/pdfs/<YYMM>/` subdirectories, and tracks everything in Postgres. Feeds into the extraction flow.

```bash
# Quick test (5 papers)
uv run --env-file .env python -m flows.arxiv_search

# Backfill: retry downloading pending/failed papers without re-searching
# Set skip_search=True via the Prefect UI, or modify the __main__ block
```

## References

- [Prefect self-hosted Docker Compose guide](https://docs.prefect.io/v3/how-to-guides/self-hosted/docker-compose)
