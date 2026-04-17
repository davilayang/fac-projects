# Dagster assets for chunking and embedding — two separate stages.
#
# document_chunks:     extract_documents → read .md → chunk → write JSON
# document_embeddings: document_chunks → read JSON → embed via OpenAI → persist to DB

import json
import logging

from pathlib import Path

import dagster as dg

from pipeline.lib.chunker import split_into_chunks
from pipeline.lib.db import (
    get_unchunked_documents,
    get_unembedded_document_ids,
    persist_chunks_and_embeddings,
)
from pipeline.lib.embeddings_client import generate_embeddings, get_openai_client
from pipeline.resources import DatabaseResource

from .resources import ChunkingEmbeddingConfig

logger = logging.getLogger(__name__)

ASSET_TAGS = {"domain": "rag"}
BATCH_SIZE = 10


# ===========================================================================
# Stage 1: Chunking — reads markdown, writes JSON
# ===========================================================================


@dg.op(
    ins={"start": dg.In(dg.Nothing)},
    out={"doc_batches": dg.DynamicOut(list)},
)
def list_unchunked_docs_op(
    context: dg.OpExecutionContext,
    database: DatabaseResource,
    chunking_embedding_config: ChunkingEmbeddingConfig,
):
    """Query DB for extracted docs, filter by existing chunk JSONs."""
    engine = database.get_engine()
    docs = get_unchunked_documents(engine)
    chunks_dir = Path(chunking_embedding_config.chunks_dir)

    # Filter out documents that already have a chunk JSON on disk
    pending = [
        d for d in docs if not (chunks_dir / f"{d['document_id']}.json").exists()
    ]

    context.log.info(
        "%d unchunked documents (%d already have JSON)",
        len(pending),
        len(docs) - len(pending),
    )

    if not pending:
        return

    for i in range(0, len(pending), BATCH_SIZE):
        batch = pending[i : i + BATCH_SIZE]
        yield dg.DynamicOutput(
            batch,
            mapping_key=f"batch_{i // BATCH_SIZE}",
            output_name="doc_batches",
        )


@dg.op(retry_policy=dg.RetryPolicy(max_retries=2, delay=5))
def chunk_batch_op(
    context: dg.OpExecutionContext,
    doc_batch: list,
    chunking_embedding_config: ChunkingEmbeddingConfig,
) -> list[dict]:
    """Read markdown, chunk, write JSON to data/chunks/."""
    config = chunking_embedding_config
    chunks_dir = Path(config.chunks_dir)
    chunks_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []

    for doc in doc_batch:
        document_id = doc["document_id"]
        output_file = doc["output_file"]

        try:
            md_path = Path(output_file)
            if not md_path.exists():
                context.log.warning("Missing file: %s", output_file)
                results.append(
                    {"document_id": document_id, "chunks": 0, "status": "file_missing"}
                )
                continue

            content = md_path.read_text(encoding="utf-8")

            metadata = {
                "arxiv_id": doc.get("arxiv_id") or "",
                "title": doc.get("title") or "",
                "authors": doc.get("authors") or [],
                "published": str(doc.get("published_at") or ""),
                "categories": doc.get("categories") or [],
                "primary_category": doc.get("primary_category") or "",
            }

            chunks = split_into_chunks(
                content,
                metadata,
                max_chunk_words=config.max_chunk_words,
                sentences_overlap=config.sentences_overlap,
                max_chunk_chars=config.max_chunk_chars,
            )

            if not chunks:
                context.log.warning("No chunks for %s", document_id)
                results.append(
                    {"document_id": document_id, "chunks": 0, "status": "no_chunks"}
                )
                continue

            # Write JSON
            out_path = chunks_dir / f"{document_id}.json"
            payload = {**metadata, "document_id": document_id, "chunks": chunks}
            out_path.write_text(json.dumps(payload, default=str), encoding="utf-8")

            context.log.info("Chunked %s: %d chunks", document_id, len(chunks))
            results.append(
                {"document_id": document_id, "chunks": len(chunks), "status": "ok"}
            )

        except Exception as e:
            context.log.error("Failed to chunk %s: %s", document_id, e)
            results.append({"document_id": document_id, "chunks": 0, "status": str(e)})

    return results


@dg.op
def summarize_chunks_op(
    context: dg.OpExecutionContext,
    results: list[list[dict]],
) -> dg.Output[list[dict]]:
    """Flatten and summarize chunking results."""
    flat = [r for batch in results for r in batch]
    ok = [r for r in flat if r.get("status") == "ok"]
    errors = [r for r in flat if r.get("status") != "ok"]
    total_chunks = sum(r.get("chunks", 0) for r in ok)

    summary_lines = [
        f"**Documents chunked:** {len(ok)}",
        f"**Total chunks:** {total_chunks}",
        f"**Errors:** {len(errors)}",
    ]
    if ok:
        summary_lines.append("\n| document_id | chunks |")
        summary_lines.append("| --- | --- |")
        for r in ok:
            summary_lines.append(f"| `{r['document_id']}` | {r['chunks']} |")

    context.log.info(
        "Chunking complete: %d docs, %d chunks, %d errors",
        len(ok),
        total_chunks,
        len(errors),
    )

    return dg.Output(
        flat,
        metadata={
            "documents_chunked": dg.MetadataValue.int(len(ok)),
            "total_chunks": dg.MetadataValue.int(total_chunks),
            "errors": dg.MetadataValue.int(len(errors)),
            "summary": dg.MetadataValue.md("\n".join(summary_lines)),
        },
    )


@dg.graph_asset(
    ins={"extract_documents": dg.AssetIn()},
    tags=ASSET_TAGS,
    description="Chunk extracted documents and write JSON files to data/chunks/",
)
def document_chunks(extract_documents):
    doc_batches = list_unchunked_docs_op(start=extract_documents)
    results = doc_batches.map(chunk_batch_op)
    return summarize_chunks_op(results.collect())


@dg.asset_check(asset=document_chunks)
def no_chunking_errors(
    context: dg.AssetCheckExecutionContext,
) -> dg.AssetCheckResult:
    """Verify the last chunking run had no errors."""
    event = context.instance.get_latest_materialization_event(document_chunks.key)
    if event is None:
        return dg.AssetCheckResult(
            passed=False, metadata={"reason": "no materialization found"}
        )
    metadata = event.asset_materialization.metadata  # type: ignore[union-attr]
    error_count = metadata.get("errors", dg.IntMetadataValue(0)).value
    return dg.AssetCheckResult(
        passed=error_count == 0, metadata={"error_count": error_count}
    )


# ===========================================================================
# Stage 2: Embedding — reads JSON, calls OpenAI, writes to DB
# ===========================================================================


@dg.op(
    ins={"start": dg.In(dg.Nothing)},
    out={"doc_batches": dg.DynamicOut(list)},
)
def list_unembedded_docs_op(
    context: dg.OpExecutionContext,
    database: DatabaseResource,
    chunking_embedding_config: ChunkingEmbeddingConfig,
):
    """Scan chunk JSONs, filter by which are already in DB."""
    chunks_dir = Path(chunking_embedding_config.chunks_dir)
    if not chunks_dir.exists():
        context.log.warning("Chunks directory does not exist: %s", chunks_dir)
        return

    json_files = sorted(chunks_dir.glob("*.json"))
    if not json_files:
        context.log.info("No chunk JSON files found")
        return

    document_ids = [f.stem for f in json_files]
    engine = database.get_engine()
    pending_ids = get_unembedded_document_ids(engine, document_ids)

    pending_files = [chunks_dir / f"{did}.json" for did in pending_ids]

    context.log.info(
        "%d unembedded documents (%d already in DB)",
        len(pending_files),
        len(json_files) - len(pending_files),
    )

    if not pending_files:
        return

    for i in range(0, len(pending_files), BATCH_SIZE):
        batch = [str(f) for f in pending_files[i : i + BATCH_SIZE]]
        yield dg.DynamicOutput(
            batch,
            mapping_key=f"batch_{i // BATCH_SIZE}",
            output_name="doc_batches",
        )


@dg.op(retry_policy=dg.RetryPolicy(max_retries=2, delay=10))
def embed_batch_op(
    context: dg.OpExecutionContext,
    doc_batch: list,
    database: DatabaseResource,
    chunking_embedding_config: ChunkingEmbeddingConfig,
) -> list[dict]:
    """Read chunk JSONs, embed via OpenAI, persist to DB."""
    config = chunking_embedding_config
    engine = database.get_engine()
    client = get_openai_client(config.openai_api_key)

    results: list[dict] = []

    for json_path_str in doc_batch:
        json_path = Path(json_path_str)
        document_id = json_path.stem

        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            chunks = data["chunks"]

            if not chunks:
                results.append(
                    {"document_id": document_id, "chunks": 0, "status": "no_chunks"}
                )
                continue

            # Embed in sub-batches
            texts = [c["text"] for c in chunks]
            all_embeddings: list[list[float]] = []
            for j in range(0, len(texts), config.embedding_batch_size):
                sub_batch = texts[j : j + config.embedding_batch_size]
                all_embeddings.extend(
                    generate_embeddings(client, sub_batch, config.embedding_model)
                )

            # Persist to DB
            count = persist_chunks_and_embeddings(
                engine, document_id, chunks, all_embeddings, config.embedding_model
            )

            context.log.info("Embedded %s: %d chunks", document_id, count)
            results.append(
                {"document_id": document_id, "chunks": count, "status": "ok"}
            )

        except Exception as e:
            context.log.error("Failed to embed %s: %s", document_id, e)
            results.append({"document_id": document_id, "chunks": 0, "status": str(e)})

    return results


@dg.op
def summarize_embeddings_op(
    context: dg.OpExecutionContext,
    results: list[list[dict]],
) -> dg.Output[list[dict]]:
    """Flatten and summarize embedding results."""
    flat = [r for batch in results for r in batch]
    ok = [r for r in flat if r.get("status") == "ok"]
    errors = [r for r in flat if r.get("status") != "ok"]
    total_chunks = sum(r.get("chunks", 0) for r in ok)

    summary_lines = [
        f"**Documents embedded:** {len(ok)}",
        f"**Total chunks embedded:** {total_chunks}",
        f"**Errors:** {len(errors)}",
    ]
    if ok:
        summary_lines.append("\n| document_id | chunks |")
        summary_lines.append("| --- | --- |")
        for r in ok:
            summary_lines.append(f"| `{r['document_id']}` | {r['chunks']} |")

    context.log.info(
        "Embedding complete: %d docs, %d chunks, %d errors",
        len(ok),
        total_chunks,
        len(errors),
    )

    return dg.Output(
        flat,
        metadata={
            "documents_embedded": dg.MetadataValue.int(len(ok)),
            "total_chunks_embedded": dg.MetadataValue.int(total_chunks),
            "errors": dg.MetadataValue.int(len(errors)),
            "summary": dg.MetadataValue.md("\n".join(summary_lines)),
        },
    )


@dg.graph_asset(
    ins={"document_chunks": dg.AssetIn()},
    tags=ASSET_TAGS,
    description="Generate embeddings from chunk JSONs and persist to Postgres",
)
def document_embeddings(document_chunks):
    doc_batches = list_unembedded_docs_op(start=document_chunks)
    results = doc_batches.map(embed_batch_op)
    return summarize_embeddings_op(results.collect())


@dg.asset_check(asset=document_embeddings)
def no_embedding_errors(
    context: dg.AssetCheckExecutionContext,
) -> dg.AssetCheckResult:
    """Verify the last embedding run had no errors."""
    event = context.instance.get_latest_materialization_event(document_embeddings.key)
    if event is None:
        return dg.AssetCheckResult(
            passed=False, metadata={"reason": "no materialization found"}
        )
    metadata = event.asset_materialization.metadata  # type: ignore[union-attr]
    error_count = metadata.get("errors", dg.IntMetadataValue(0)).value
    return dg.AssetCheckResult(
        passed=error_count == 0, metadata={"error_count": error_count}
    )
