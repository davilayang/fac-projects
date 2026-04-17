"""Arxiv paper models: search tracking and download management."""

import enum

from datetime import datetime, timezone

from sqlalchemy import (
    ARRAY,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from db.models import Base


class DownloadStatus(str, enum.Enum):
    pending = "pending"
    downloading = "downloading"
    downloaded = "downloaded"
    failed = "failed"


class ArxivPaper(Base):
    __tablename__ = "arxiv_papers"
    __table_args__ = (
        Index("ix_arxiv_papers_published_at", "published_at"),
        Index("ix_arxiv_papers_download_status", "download_status"),
        Index(
            "ix_arxiv_papers_categories",
            "categories",
            postgresql_using="gin",
        ),
        {"schema": "ingestion"},
    )

    # PK: clean arxiv ID without version (e.g. "2602.03300")
    arxiv_id = Column(String, primary_key=True)

    # Metadata from arxiv API
    title = Column(Text, nullable=False)
    authors: Column[list[str] | None] = Column(ARRAY(String))
    abstract = Column(Text)
    categories: Column[list[str] | None] = Column(ARRAY(String))
    primary_category = Column(String)
    published_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    pdf_url = Column(String)
    abstract_url = Column(String)
    latest_version = Column(Integer, default=1)

    # Download tracking
    download_status = Column(
        Enum(DownloadStatus, schema="ingestion"),
        nullable=False,
        default=DownloadStatus.pending,
    )
    local_pdf_path = Column(String)
    last_downloaded_at = Column(DateTime(timezone=True))
    started_downloading_at = Column(DateTime(timezone=True))
    download_error = Column(Text)

    # Housekeeping
    first_seen_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    metadata_updated_at = Column(DateTime(timezone=True))


class SearchRun(Base):
    __tablename__ = "arxiv_search_runs"
    __table_args__ = {"schema": "ingestion"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Search parameters
    query_string = Column(Text, nullable=False)
    date_from = Column(String)
    date_to = Column(String)
    max_results = Column(Integer)
    sort_by = Column(String)
    sort_order = Column(String)

    # Outcome
    started_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = Column(DateTime(timezone=True))
    result_count = Column(Integer)
    new_papers_count = Column(Integer)
    status = Column(String, nullable=False, default="running")
    error_message = Column(Text)


class SearchRunPaper(Base):
    __tablename__ = "arxiv_search_run_papers"
    __table_args__ = (
        UniqueConstraint("search_run_id", "arxiv_id", name="uq_search_run_paper"),
        {"schema": "ingestion"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    search_run_id = Column(
        Integer,
        ForeignKey("ingestion.arxiv_search_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    arxiv_id = Column(
        String,
        ForeignKey("ingestion.arxiv_papers.arxiv_id", ondelete="CASCADE"),
        nullable=False,
    )
    rank_in_run = Column(Integer)
