# Database query functions — pure Python, no orchestration dependency.
# SQLAlchemy models are imported from the existing db/ package.

import re
import uuid

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import Engine, create_engine, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from db.models import (
    ArxivPaper,
    Chunk,
    ChunkProcessingStatus,
    DocumentMetadata,
    DocumentProcessingStatus,
    DownloadStatus,
    Embedding,
    SearchRun,
    SearchRunPaper,
)


def get_engine(database_url: str) -> Engine:
    return create_engine(database_url)


def create_search_run(
    engine: Engine,
    query_string: str,
    date_from: str,
    date_to: str | None,
    max_results: int,
) -> int:
    """Insert a SearchRun row and return its ID."""
    with Session(engine) as session:
        run = SearchRun(
            query_string=query_string,
            date_from=date_from,
            date_to=date_to,
            max_results=max_results,
            sort_by="SubmittedDate",
            sort_order="Descending",
            status="running",
        )
        session.add(run)
        session.commit()
        return run.id


def upsert_paper(
    engine: Engine,
    paper: dict,
    search_run_id: int,
    rank: int,
) -> bool:
    """Upsert paper into arxiv_papers and link to search run.

    Returns True if the paper is new.
    """
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        stmt = pg_insert(ArxivPaper).values(
            arxiv_id=paper["arxiv_id"],
            title=paper["title"],
            authors=paper["authors"],
            abstract=paper["abstract"],
            categories=paper["categories"],
            primary_category=paper["primary_category"],
            published_at=paper["published_at"],
            updated_at=paper["updated_at"],
            pdf_url=paper["pdf_url"],
            abstract_url=paper["abstract_url"],
            latest_version=paper["version"],
            download_status=DownloadStatus.pending,
            first_seen_at=now,
            metadata_updated_at=now,
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["arxiv_id"],
            set_={
                "title": stmt.excluded.title,
                "authors": stmt.excluded.authors,
                "abstract": stmt.excluded.abstract,
                "categories": stmt.excluded.categories,
                "primary_category": stmt.excluded.primary_category,
                "updated_at": stmt.excluded.updated_at,
                "pdf_url": stmt.excluded.pdf_url,
                "abstract_url": stmt.excluded.abstract_url,
                "latest_version": stmt.excluded.latest_version,
                "metadata_updated_at": now,
            },
        )

        session.execute(stmt)

        existing = session.get(ArxivPaper, paper["arxiv_id"])
        is_new = existing is not None and existing.first_seen_at == now

        # Reset to pending if version changed and already downloaded
        if (
            existing
            and existing.latest_version != paper["version"]
            and existing.download_status
            in (DownloadStatus.downloaded, DownloadStatus.failed)
        ):
            existing.download_status = DownloadStatus.pending

        # Link paper to search run
        link_stmt = pg_insert(SearchRunPaper).values(
            search_run_id=search_run_id,
            arxiv_id=paper["arxiv_id"],
            rank_in_run=rank,
        )
        link_stmt = link_stmt.on_conflict_do_nothing(constraint="uq_search_run_paper")
        session.execute(link_stmt)

        session.commit()

    return is_new


def get_pending_downloads(engine: Engine, limit: int | None = None) -> list[dict]:
    """Get papers with pending or stale downloading status."""
    stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=10)

    with Session(engine) as session:
        stmt = select(
            ArxivPaper.arxiv_id,
            ArxivPaper.pdf_url,
            ArxivPaper.latest_version,
        ).where(
            (ArxivPaper.download_status == DownloadStatus.pending)
            | (
                (ArxivPaper.download_status == DownloadStatus.downloading)
                & (ArxivPaper.started_downloading_at < stale_threshold)
            )
        )

        if limit:
            stmt = stmt.limit(limit)

        rows = session.execute(stmt).all()

    return [
        {
            "arxiv_id": row.arxiv_id,
            "pdf_url": row.pdf_url,
            "latest_version": row.latest_version,
        }
        for row in rows
    ]


def mark_download_status(
    engine: Engine,
    arxiv_id: str,
    status: DownloadStatus,
    *,
    local_pdf_path: str | None = None,
    error: str | None = None,
) -> None:
    """Update the download status for a paper."""
    now = datetime.now(timezone.utc)
    values: dict = {"download_status": status}

    if status == DownloadStatus.downloading:
        values["started_downloading_at"] = now
    elif status == DownloadStatus.downloaded:
        values["local_pdf_path"] = local_pdf_path
        values["last_downloaded_at"] = now
        values["download_error"] = None
    elif status == DownloadStatus.failed:
        values["download_error"] = error

    with Session(engine) as session:
        session.execute(
            update(ArxivPaper).where(ArxivPaper.arxiv_id == arxiv_id).values(**values)
        )
        session.commit()


def complete_search_run(
    engine: Engine,
    search_run_id: int,
    result_count: int,
    new_papers_count: int,
) -> None:
    """Mark a search run as completed."""
    with Session(engine) as session:
        session.execute(
            update(SearchRun)
            .where(SearchRun.id == search_run_id)
            .values(
                completed_at=datetime.now(timezone.utc),
                result_count=result_count,
                new_papers_count=new_papers_count,
                status="completed",
            )
        )
        session.commit()


def count_stale_downloads(engine: Engine) -> int:
    """Count papers stuck in DOWNLOADING status for more than 10 minutes."""
    stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=10)

    with Session(engine) as session:
        stmt = select(ArxivPaper.arxiv_id).where(
            (ArxivPaper.download_status == DownloadStatus.downloading)
            & (ArxivPaper.started_downloading_at < stale_threshold)
        )
        return len(session.execute(stmt).all())


# --- Extraction queries ---


def filter_unprocessed(engine: Engine, pdf_files: list[Path]) -> list[Path]:
    """Return only PDFs not yet recorded in document_processing_status."""
    with Session(engine) as session:
        stmt = select(DocumentProcessingStatus.source_file)
        processed = {row[0] for row in session.execute(stmt).all()}

    return [f for f in pdf_files if str(f) not in processed]


def record_extraction(
    engine: Engine,
    pdf_path: Path,
    output_path: Path,
    metadata: dict,
) -> None:
    """Write processing status and metadata records to Postgres."""
    with Session(engine) as session:
        # Derive arxiv_id by stripping version suffix (e.g. 2602.03300v1 → 2602.03300)
        arxiv_id = re.sub(r"v\d+$", "", pdf_path.stem)
        status_record = DocumentProcessingStatus(
            document_id=pdf_path.stem,
            arxiv_id=arxiv_id,
            source_file=str(pdf_path),
            output_file=str(output_path),
            extracted_at=datetime.now(timezone.utc),
        )
        session.merge(status_record)

        meta_record = DocumentMetadata(
            document_id=pdf_path.stem,
            title=metadata.get("title") or None,
            authors=metadata.get("authors") or None,
        )
        session.merge(meta_record)

        session.commit()


# --- Chunking & Embedding queries ---


def get_unchunked_documents(engine: Engine) -> list[dict]:
    """Return extracted documents that have not been chunked yet.

    Joins document_processing_status → arxiv_papers (via arxiv_id FK)
    and filters out documents that already have chunks.
    """
    with Session(engine) as session:
        # Subquery: document_ids that already have chunks
        chunked_ids = (
            select(Chunk.document_id).distinct().subquery()
        )

        stmt = (
            select(
                DocumentProcessingStatus.document_id,
                DocumentProcessingStatus.arxiv_id,
                DocumentProcessingStatus.output_file,
                ArxivPaper.title,
                ArxivPaper.authors,
                ArxivPaper.published_at,
                ArxivPaper.categories,
                ArxivPaper.primary_category,
            )
            .outerjoin(
                ArxivPaper,
                DocumentProcessingStatus.arxiv_id == ArxivPaper.arxiv_id,
            )
            .where(
                DocumentProcessingStatus.output_file.isnot(None),
                DocumentProcessingStatus.document_id.notin_(
                    select(chunked_ids.c.document_id)
                ),
            )
        )

        rows = session.execute(stmt).all()

    return [
        {
            "document_id": row.document_id,
            "arxiv_id": row.arxiv_id,
            "output_file": row.output_file,
            "title": row.title,
            "authors": row.authors,
            "published_at": row.published_at,
            "categories": row.categories,
            "primary_category": row.primary_category,
        }
        for row in rows
    ]


def persist_chunks_and_embeddings(
    engine: Engine,
    document_id: str,
    chunks: list[dict],
    embeddings: list[list[float]],
    embedding_model: str,
) -> int:
    """Write chunks + embeddings for one document in a single transaction.

    Creates Chunk rows, Embedding rows, and a ChunkProcessingStatus row.
    Returns the number of chunks persisted.
    """
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{document_id}::chunk{i}"

            # ChunkProcessingStatus (must exist before Chunk due to FK)
            session.merge(
                ChunkProcessingStatus(chunk_id=chunk_id, processed_at=now)
            )

            session.merge(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    chunk_text=chunk["text"],
                    chunk_strategy="markdown_sentence_overlap",
                )
            )

            session.merge(
                Embedding(
                    chunk_id=chunk_id,
                    vector=vector,
                    embedding_model=embedding_model,
                )
            )

        session.commit()

    return len(chunks)
