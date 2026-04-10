# arxiv-rag

RAG pipeline over arXiv papers. Extracts markdown, chunks semantically, embeds with OpenAI, stores in pgvector. Retrieval uses HNSW vector search with cross-encoder re-ranking and metadata filtering.

## Stack

- **Python** 3.12, managed with `uv`
- **OpenAI** `text-embedding-3-small` (1536 dims)
- **PostgreSQL** 16 + pgvector via Docker
- **SQLAlchemy** + **Alembic** for ORM and migrations
- **sentence-transformers** `cross-encoder/ms-marco-MiniLM-L-12-v2` for re-ranking
- **Hetzner Object Storage** (S3-compatible) for paper storage

## Setup

```bash
# 1. Install dependencies
`uv sync`

# 2. Pull secrets from 1Password
uv run scripts/setup_env.py

# 3. Start the database
docker compose up -d

# 4. Apply migrations
uv run alembic upgrade head
```

## Commands

```bash
# Embed and store all chunks (truncates existing data first)
uv run arxiv-rag build-embeddings

# Search — re-ranking enabled by default (fetches k*4 candidates, reranks to k)
uv run arxiv-rag retrieve --query "attention mechanism"
uv run arxiv-rag retrieve --query "attention mechanism" --k 10

# Skip re-ranking
uv run arxiv-rag retrieve --query "attention mechanism" --no-rerank

# Filter by metadata (combinable)
uv run arxiv-rag retrieve --query "quantization" --category "cs.CL"
uv run arxiv-rag retrieve --query "transformers" --author "Vaswani"
uv run arxiv-rag retrieve --query "scaling laws" --published-after "2026-01-01"
uv run arxiv-rag retrieve --query "RAG" --category "cs.IR" --published-after "2025-06-01" --k 10
```

## Database

```bash
# Start / stop
docker compose up -d
docker compose down

# Connect with psql
docker exec -it postgres psql -U <DB_USERNAME> -d <DB_DATABASE>
```

**Useful psql commands:**

```sql
\d                               -- list tables
\d arxiv_chunks                  -- describe schema
\timing                          -- toggle query timing

SELECT COUNT(*) FROM arxiv_chunks;
SELECT arxiv_id, title, section, left(text, 100) FROM arxiv_chunks LIMIT 5;

\q                               -- exit
```

## Generate

```bash
# Answer a question with citations (uses retrieval + reranking + Claude)
uv run arxiv-rag generate --query "What attention mechanisms are used in transformers?"
uv run arxiv-rag generate --query "quantization methods" --k 10
uv run arxiv-rag generate --query "scaling laws" --category "cs.LG" --published-after "2026-01-01"
```

## Logging

Every command emits structured JSON logs to stdout and persists them to the `logs` table in Postgres.

Each CLI invocation gets a unique `trace_id` (UUID) that links all events — retrieval, rerank, generation — for that request.

**Stdout format:**

```json
{"timestamp": "2026-04-09T07:52:35Z", "level": "INFO", "trace_id": "21dac702-...", "event": "retrieval", "query": "...", "latency_ms": 2325, "chunks": [...]}
{"timestamp": "2026-04-09T07:52:36Z", "level": "INFO", "trace_id": "21dac702-...", "event": "rerank", "latency_ms": 859, "chunks": [...]}
{"timestamp": "2026-04-09T07:52:47Z", "level": "INFO", "trace_id": "21dac702-...", "event": "generation", "model": "claude-sonnet-4-6", "tokens_input": 3756, "tokens_output": 635, "latency_ms": 11289, "cited": [0, 1, 2]}
```

**Querying logs in psql:**

```sql
-- Use expanded display for readable output
\x

-- Pipeline summary for a single request
SELECT event, latency_ms, jsonb_array_length(chunks) AS chunks_returned, cited
FROM logs
WHERE trace_id = '<trace_id>'
ORDER BY timestamp;

-- Token spend per generation
SELECT timestamp::date AS date, query, tokens_input, tokens_output,
       tokens_input + tokens_output AS total_tokens, latency_ms
FROM logs
WHERE event = 'generation'
ORDER BY timestamp DESC;

-- Unnest chunks to see per-chunk scores
SELECT event, chunk->>'arxiv_id' AS arxiv_id, round((chunk->>'score')::numeric, 4) AS score
FROM logs, jsonb_array_elements(chunks) AS chunk
WHERE trace_id = '<trace_id>'
  AND event IN ('retrieval', 'rerank')
ORDER BY event, score DESC;
```

**Cleanup** — remove logs older than 30 days:

```sql
DELETE FROM logs WHERE timestamp < NOW() - INTERVAL '30 days';
```

## Ingestion

Papers are stored as markdown files in Hetzner Object Storage (`vertuvian/arxiv_rag/extracted/`) and ingested into pgvector on demand.

### Upload papers

Upload `.md` files named by arXiv ID (e.g. `2301.12345v1.md`) to the S3 bucket:

```python
from arxiv_rag.clients.s3_client import s3, BUCKET, EXTRACTED_PREFIX

s3.upload_file("path/to/2301.12345v1.md", BUCKET, f"{EXTRACTED_PREFIX}2301.12345v1.md")
```

Or via the AWS CLI (configured with Hetzner Object Storage credentials):

```bash
aws s3 cp path/to/2301.12345v1.md s3://vertuvian/arxiv_rag/extracted/2301.12345v1.md \
  --endpoint-url https://hel1.your-objectstorage.com
```

### Run ingestion locally

```bash
uv run arxiv-rag build-embeddings
```

Truncates `arxiv_chunks`, reads all `.md` files from S3, fetches metadata from the arXiv API, chunks, embeds, and stores.

### Run ingestion on the server

```bash
ssh hetzner "docker exec arxiv-rag-api arxiv-rag build-embeddings"
```

## Deployment

The app runs on Hetzner behind nginx + Let's Encrypt. Images are built locally, pushed to a private registry on the server via SSH tunnel, and pulled by docker compose.

### Prerequisites

- SSH alias `hetzner` configured in `~/.ssh/config`
- Private Docker registry running on the server: `docker run -d --restart=always -p 127.0.0.1:5000:5000 --name registry registry:2`
- `.env` file with production secrets (see `.env.template`)

### First deploy

```bash
bash scripts/deploy.sh v1.0.0 --init
```

`--init` obtains the Let's Encrypt certificate via certbot. Subsequent cert renewals are automatic (certbot service runs every 12 hours).

### Re-deploy (new version)

```bash
bash scripts/deploy.sh v1.0.1
```

Builds a `linux/amd64` image, opens an SSH tunnel to the on-server registry, pushes the image, syncs config files, then pulls and restarts services. The tunnel is managed by the script — no manual step required.

### Update environment variables

The server's `.env` is written once on first deploy and never overwritten by subsequent deploys — this prevents local dev values from clobbering production secrets. To change a value in production, edit it directly on the server:

```bash
ssh hetzner "vi /opt/arxiv-rag/.env"
ssh hetzner "cd /opt/arxiv-rag && TAG=v0.1.0 docker compose up -d --force-recreate api"
```

Note: `docker compose restart` won't pick up `.env` changes — `--force-recreate` is required to recreate the container with the new values. Replace `v0.1.0` with the currently running tag.

### Logs

```bash
ssh hetzner "docker logs arxiv-rag-api -f"
ssh hetzner "docker logs arxiv-rag-nginx -f"
```

## Migrations

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Create a new migration after changing models.py
uv run alembic revision --autogenerate -m "describe change"

# Roll back one migration
uv run alembic downgrade -1

# Check current state
uv run alembic current
```
