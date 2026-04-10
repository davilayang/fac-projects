import logging
from pathlib import Path

from sqlalchemy import text

from arxiv_rag.clients import generate_embeddings, get_batch_metadata
from arxiv_rag.clients.s3_client import get_extracted, list_extracted
from arxiv_rag.database import ArxivChunk, get_session

from .chunking import split_into_chunks

logger = logging.getLogger(__name__)

EMBEDDING_BATCH_SIZE = 200


def get_documents() -> list[dict]:
    logger.info("Listing extracted files from S3")
    files = list_extracted()
    if not files:
        logger.warning("No .md files found in S3 extracted prefix — nothing to ingest")
        return []

    logger.info("Found %d files in S3", len(files))
    arxiv_ids = [Path(f).stem for f in files]

    logger.info("Fetching metadata from arxiv API for %d papers", len(arxiv_ids))
    try:
        metadata_by_id = {m.arxiv_id: m for m in get_batch_metadata(arxiv_ids)}
    except Exception:
        logger.exception("Failed to fetch metadata from arxiv API")
        raise

    missing = [aid for aid in arxiv_ids if aid not in metadata_by_id]
    if missing:
        logger.warning("Metadata not found for %d papers: %s", len(missing), missing)

    documents = []
    for f, arxiv_id in zip(files, arxiv_ids, strict=True):
        if arxiv_id not in metadata_by_id:
            continue
        try:
            text_content = get_extracted(f)
            documents.append({"metadata": metadata_by_id[arxiv_id], "text": text_content})
        except Exception:
            logger.exception("Failed to read s3 file %s — skipping", f)

    logger.info("Loaded %d documents from S3", len(documents))
    return documents


def build_embeddings():
    logger.info("Starting embedding build")

    logger.info("Truncating arxiv_chunks table")
    with get_session() as session:
        session.execute(text("TRUNCATE arxiv_chunks"))

    documents = get_documents()
    if not documents:
        logger.warning("No documents to embed — exiting")
        return

    chunks = [
        chunk
        for document in documents
        for chunk in split_into_chunks(document["text"], document["metadata"])
    ]
    logger.info("Split %d documents into %d chunks", len(documents), len(chunks))

    stored = 0
    total_batches = (len(chunks) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE
    for i in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[i : i + EMBEDDING_BATCH_SIZE]
        batch_num = i // EMBEDDING_BATCH_SIZE + 1
        logger.info("Embedding batch %d/%d (%d chunks)", batch_num, total_batches, len(batch))

        try:
            embeddings = generate_embeddings([chunk["text"] for chunk in batch])
        except Exception:
            logger.exception("Failed to generate embeddings for batch %d — aborting", batch_num)
            raise

        with get_session() as session:
            for chunk, embedding in zip(batch, embeddings, strict=True):
                session.add(
                    ArxivChunk(
                        arxiv_id=chunk["arxiv_id"],
                        title=chunk["title"],
                        authors=chunk["authors"],
                        published=chunk["published"],
                        categories=chunk["categories"],
                        primary_category=chunk["primary_category"],
                        section=chunk["section"],
                        subsection=chunk["subsection"],
                        text=chunk["text"],
                        embedding=embedding,
                    )
                )
        stored += len(batch)
        logger.info("Stored %d/%d chunks", stored, len(chunks))

    logger.info("Embedding build complete — %d chunks stored", stored)
