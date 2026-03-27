# flows/embedding.py
# Generate embeddings for chunks and store them in pgvector.
#
# Supports two providers:
#   huggingface — local inference via sentence-transformers (default)
#   openai      — OpenAI Embeddings API (requires OPENAI_API_KEY)
#
# Configure via environment variables:
#   EMBEDDING_PROVIDER  huggingface | openai  (default: huggingface)
#   EMBEDDING_MODEL     model name             (default: allenai/specter2)
#
# The flow is idempotent: it only processes chunks that do not yet have
# an embedding row, so re-runs are safe.

import os
import sys

from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from db.models.chunks import Chunk
from db.models.embeddings import Embedding

DEFAULT_PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "huggingface")
DEFAULT_MODEL = os.environ.get("EMBEDDING_MODEL", "allenai/specter2")
DEFAULT_BATCH_SIZE = 32


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------


def _embed_huggingface(texts: list[str], model_name: str) -> list[list[float]]:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def _embed_openai(texts: list[str], model_name: str) -> list[list[float]]:
    from openai import OpenAI

    client = OpenAI()
    # OpenAI allows up to 2048 inputs per request
    vectors: list[list[float]] = []
    for i in range(0, len(texts), 2048):
        batch = texts[i : i + 2048]
        response = client.embeddings.create(model=model_name, input=batch)
        vectors.extend(item.embedding for item in response.data)
    return vectors


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@task(log_prints=True)
def get_db_engine(database_url: str):
    return create_engine(database_url)


@task(log_prints=True, cache_policy=NO_CACHE)
def get_unembedded_chunks(engine) -> list[tuple[str, str]]:
    """Return (chunk_id, chunk_text) pairs that have no embedding yet."""
    with Session(engine) as session:
        embedded_ids = {
            row[0] for row in session.execute(select(Embedding.chunk_id)).all()
        }
        rows = session.execute(select(Chunk.chunk_id, Chunk.chunk_text)).all()

    pending = [(cid, text) for cid, text in rows if cid not in embedded_ids]
    print(f"[embedding] {len(pending)} chunks pending embedding")
    return pending


@task(
    retries=2,
    retry_delay_seconds=10,
    timeout_seconds=600,
    cache_policy=NO_CACHE,
    log_prints=True,
)
def embed_and_store(
    engine,
    chunks: list[tuple[str, str]],
    batch_size: int,
    provider: str,
    model_name: str,
) -> int:
    """Embed chunks in batches and upsert vectors into Postgres."""
    stored = 0
    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start : batch_start + batch_size]
        ids = [row[0] for row in batch]
        texts = [row[1] for row in batch]

        if provider == "openai":
            vectors = _embed_openai(texts, model_name)
        else:
            vectors = _embed_huggingface(texts, model_name)

        with Session(engine) as session:
            for chunk_id, vector in zip(ids, vectors):
                session.merge(
                    Embedding(
                        chunk_id=chunk_id,
                        vector=vector,
                        embedding_model=model_name,
                        embedding_model_params=f"provider={provider}",
                    )
                )
            session.commit()

        stored += len(batch)
        print(f"[embedding] {stored}/{len(chunks)} embedded")

    return stored


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------


@flow(log_prints=True)
def embedding_flow(
    provider: str = "",
    model_name: str = "",
    batch_size: int = DEFAULT_BATCH_SIZE,
    database_url: str = "",
) -> None:
    """Embed all un-embedded chunks and store in pgvector.

    1. Query Postgres for chunks without an existing embedding row
    2. Embed in batches using the configured provider and model
       - huggingface: local inference via sentence-transformers
       - openai: OpenAI Embeddings API (requires OPENAI_API_KEY)
    3. Upsert vectors into ingestion.embeddings

    Provider and model default to EMBEDDING_PROVIDER / EMBEDDING_MODEL env vars.
    """
    _provider = provider or DEFAULT_PROVIDER
    _model = model_name or DEFAULT_MODEL

    if not database_url:
        _user = os.environ["POSTGRES_USER"]
        _password = os.environ["POSTGRES_PASSWORD"]
        _host = os.environ.get("POSTGRES_HOST", "localhost")
        _port = os.environ.get("POSTGRES_PORT", "5432")
        _db = os.environ["POSTGRES_DB"]
        database_url = f"postgresql://{_user}:{_password}@{_host}:{_port}/{_db}"

    print(f"[embedding] provider={_provider} model={_model}")

    engine = get_db_engine(database_url)
    pending = get_unembedded_chunks(engine)

    if not pending:
        print("[embedding] Nothing to embed.")
        return

    total = embed_and_store(engine, pending, batch_size, _provider, _model)
    print(f"[embedding] Done. {total} chunks embedded with {_model}.")


if __name__ == "__main__":
    embedding_flow()
