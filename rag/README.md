# RAG — Document Ingestion Pipeline

arXiv document ingestion, chunking, and embedding pipeline using Prefect, PostgreSQL, and pgvector.

## Documentation

| Document | Description |
|---|---|
| [Architecture](./docs/architecture.md) | System design, data flow, and database schema |
| [Chunking & Embedding Strategy](./docs/CHUNKING_EMBEDDING_STRATEGY.md) | Chunking algorithm, embedding model choice, and design justification |
| [Prefect vs Airflow](./docs/PREFECT_vs_AIRFLOW.md) | Orchestration tool decision record |

---

## Prerequisites

- Python >= 3.12
- Docker with Compose v2
- [uv](https://docs.astral.sh/uv/)

---

## Quick Start

Follow these steps in order on a fresh machine.

**1. Install dependencies**
```bash
make install
```

**2. Configure environment**
```bash
cp .env.example .env
```
Open `.env` and fill in the Postgres credentials. `OPENAI_API_KEY` is not required — embeddings run locally via SPECTER2.

**3. Start services** (leave this terminal running)
```bash
make up
```
Wait until you see `Application startup complete` in the logs. This starts Postgres, Redis, the Prefect server, and the Prefect worker.

**4. Initialise the database** (new terminal)
```bash
make db-setup
```
Creates the `ingestion` schema, all tables, the `chunks_full` view, and the HNSW vector index.

**5. Run the ingestion pipeline**
```bash
make ingest
```
Runs three flows in sequence:
- **extraction** — converts PDFs in `data/pdfs/` to markdown in `data/extracted/`
- **chunking** — splits markdown into structured chunks stored in Postgres
- **embedding** — generates SPECTER2 vectors and stores them in pgvector

The first run downloads the SPECTER2 model (~500 MB). Subsequent runs use the local cache. Each flow is idempotent — re-running will only process new documents.

**Services**

| Service | URL |
|---|---|
| Prefect UI | http://localhost:4200 |
| RAG Postgres | `localhost:${POSTGRES_PORT}` |

---

## Making Changes

### Changing chunking logic

The chunking strategy lives entirely in `flows/chunking.py`. The public entry point is `chunk_markdown(text, document_title)` — a pure function with no database or Prefect dependencies, which makes it straightforward to test and iterate on.

After editing `flows/chunking.py`, run the tests to verify correctness:
```bash
make check
```

To re-chunk all documents with the updated logic, the `chunk_strategy` field in the database identifies which strategy produced each chunk. Rename the `CHUNK_STRATEGY` constant at the top of `chunking.py` (e.g. `subsection_semantic_v2`) and re-run:
```bash
make ingest
```
The chunking flow will detect that no documents have been chunked with the new strategy name and reprocess everything. Old chunks under the previous strategy name remain in the database until you clean them up manually.

### Changing the embedding model

The model name and batch size are configured at the top of `flows/embedding.py`:
```python
MODEL_NAME = "allenai/specter2"
DEFAULT_BATCH_SIZE = 32
```

If you change the model, also update `EMBEDDING_DIM` in `db/models/embeddings.py` to match the new model's output dimensions. Then drop the existing embeddings and re-run:
```sql
DELETE FROM ingestion.embeddings;
```
```bash
make ingest
```

### Changing the database schema

Schema changes require updating two places:

1. The SQLAlchemy model in `db/models/` (the Python class definition)
2. The `chunks_full` view in `db/setup.py` if the changed table is included in it

After making the changes, apply them by tearing down the database and re-running setup:
```bash
make reset    # stops services and deletes all data volumes
make up
make db-setup
make ingest
```

### Adding a new flow

1. Create `flows/your_flow.py` following the pattern of the existing flows
2. Add a deployment entry in `flows/deploy.py`
3. Run `make check` to verify it passes linting and type checks

---

## Stopping and Resetting

```bash
make down     # stop all services, data is preserved
make reset    # stop all services and delete all data (full reset)
```

Use `make reset` when you need a clean slate — for example after a schema change or if the database gets into an inconsistent state.

---

## References

- [Prefect self-hosted Docker Compose guide](https://docs.prefect.io/v3/how-to-guides/self-hosted/docker-compose)
