# Dagster assets for chunking & embedding: list → fan out → chunk+embed → summarize.
#
# Uses a @graph_asset with DynamicOutput to fan out processing
# across unchunked documents. Depends on extract_documents upstream.

import logging

from pathlib import Path

import dagster as dg

from pipeline.lib.chunker import split_into_chunks
from pipeline.lib.db import get_unchunked_documents, persist_chunks_and_embeddings
from pipeline.lib.embeddings_client import generate_embeddings, get_openai_client
from pipeline.resources import DatabaseResource

from .resources import ChunkingEmbeddingConfig

logger = logging.getLogger(__name__)

ASSET_TAGS = {"domain": "rag"}
BATCH_SIZE = 10


# ---------------------------------------------------------------------------
# Ops for the chunking & embedding graph
# ---------------------------------------------------------------------------


@dg.op(
    ins={"start": dg.In(dg.Nothing)},
    out={"doc_batches": dg.DynamicOut(list)},
)
def list_unchunked_documents_op(
    context: dg.OpExecutionContext,
    database: DatabaseResource,
):
    """Query DB for extracted-but-not-chunked documents, yield batches."""
    engine = database.get_engine()
    docs = get_unchunked_documents(engine)

    context.log.info("%d unchunked documents found", len(docs))

    if not docs:
        return

    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i : i + BATCH_SIZE]
        yield dg.DynamicOutput(
            batch,
            mapping_key=f"batch_{i // BATCH_SIZE}",
            output_name="doc_batches",
        )


@dg.op(
    retry_policy=dg.RetryPolicy(max_retries=2, delay=10),
)
def chunk_and_embed_batch(
    context: dg.OpExecutionContext,
    doc_batch: list,
    database: DatabaseResource,
    chunking_embedding_config: ChunkingEmbeddingConfig,
) -> list[dict]:
    """For each document in batch: read .md, chunk, embed via OpenAI, persist."""
    engine = database.get_engine()
    config = chunking_embedding_config
    client = get_openai_client(config.openai_api_key)

    results: list[dict] = []

    for doc in doc_batch:
        document_id = doc["document_id"]
        output_file = doc["output_file"]

        try:
            # Read extracted markdown
            md_path = Path(output_file)
            if not md_path.exists():
                context.log.warning("Missing file: %s", output_file)
                results.append(
                    {"document_id": document_id, "chunks": 0, "status": "file_missing"}
                )
                continue

            content = md_path.read_text(encoding="utf-8")

            # Build metadata dict for chunker
            metadata = {
                "arxiv_id": doc.get("arxiv_id") or "",
                "title": doc.get("title") or "",
                "authors": doc.get("authors") or [],
                "published": doc.get("published_at"),
                "categories": doc.get("categories") or [],
                "primary_category": doc.get("primary_category") or "",
            }

            # Chunk
            chunks = split_into_chunks(
                content,
                metadata,
                max_chunk_words=config.max_chunk_words,
                sentences_overlap=config.sentences_overlap,
                max_chunk_chars=config.max_chunk_chars,
            )

            if not chunks:
                context.log.warning("No chunks produced for %s", document_id)
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

            # Persist
            count = persist_chunks_and_embeddings(
                engine, document_id, chunks, all_embeddings, config.embedding_model
            )

            context.log.info(
                "Chunked %s: %d chunks, %d embeddings",
                document_id,
                count,
                len(all_embeddings),
            )
            results.append(
                {"document_id": document_id, "chunks": count, "status": "ok"}
            )

        except Exception as e:
            context.log.error("Failed to process %s: %s", document_id, e)
            results.append({"document_id": document_id, "chunks": 0, "status": str(e)})

    return results


@dg.op
def summarize_chunking(
    context: dg.OpExecutionContext,
    results: list[list[dict]],
) -> dg.Output[list[dict]]:
    """Flatten batch results and emit summary metadata."""
    flat = [r for batch in results for r in batch]
    ok = [r for r in flat if r.get("status") == "ok"]
    errors = [r for r in flat if r.get("status") != "ok"]
    total_chunks = sum(r.get("chunks", 0) for r in ok)

    summary_lines = [
        f"**Documents processed:** {len(ok)}",
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
            "documents_processed": dg.MetadataValue.int(len(ok)),
            "total_chunks": dg.MetadataValue.int(total_chunks),
            "errors": dg.MetadataValue.int(len(errors)),
            "summary": dg.MetadataValue.md("\n".join(summary_lines)),
        },
    )


# ---------------------------------------------------------------------------
# Graph asset: wires the ops together
# ---------------------------------------------------------------------------


@dg.graph_asset(
    ins={"extract_documents": dg.AssetIn()},
    tags=ASSET_TAGS,
    description="Chunk extracted documents and generate embeddings via dynamic fanout",
)
def chunked_embeddings(extract_documents):
    """list unchunked → fan out chunk_and_embed_batch → collect → summarize."""
    doc_batches = list_unchunked_documents_op(start=extract_documents)
    results = doc_batches.map(chunk_and_embed_batch)
    return summarize_chunking(results.collect())


@dg.asset_check(asset=chunked_embeddings)
def no_chunking_errors(
    context: dg.AssetCheckExecutionContext,
) -> dg.AssetCheckResult:
    """Verify the last chunking run had no errors."""
    event = context.instance.get_latest_materialization_event(chunked_embeddings.key)
    if event is None:
        return dg.AssetCheckResult(
            passed=False,
            metadata={"reason": "no materialization event found"},
        )

    metadata = event.asset_materialization.metadata  # type: ignore[union-attr]
    error_count = metadata.get("errors", dg.IntMetadataValue(0)).value
    return dg.AssetCheckResult(
        passed=error_count == 0,
        metadata={"error_count": error_count},
    )
