"""Experiment tracking models — schema: eval.

One eval run = one make eval execution with a fixed system config.
Designed for comparing system versions over time (recall, precision, MRR, latency).
Each eval query result links back to logs.queries for shared latency data.
"""

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.models import Base


class EvalRun(Base):
    __tablename__ = "runs"
    __table_args__ = {"schema": "eval"}

    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Ingestion config — what produced the chunks and vectors
    extraction_method = Column(String, nullable=False)  # e.g. "pymupdf4llm"
    chunking_strategy = Column(String, nullable=False)  # e.g. "paragraph_v1"
    chunk_max_tokens = Column(Integer, nullable=False)  # 400
    chunk_min_tokens = Column(Integer, nullable=False)  # 50
    overlap_sentences = Column(Integer, nullable=False)  # 2

    # Embedding config
    embedding_model = Column(String, nullable=False)  # e.g. "text-embedding-3-small"
    embedding_dim = Column(Integer, nullable=False)  # 1536
    embedding_provider = Column(String, nullable=False)  # "openai" | "huggingface"

    # Retrieval + generation config
    top_k = Column(Integer, nullable=False)
    generation_model = Column(String)  # null if retrieval-only run

    # Corpus snapshot at time of run
    corpus_doc_count = Column(Integer, nullable=False)
    corpus_chunk_count = Column(Integer, nullable=False)

    notes = Column(Text)

    query_results = relationship(
        "EvalQueryResult", back_populates="run", cascade="all, delete-orphan"
    )


class EvalQueryResult(Base):
    __tablename__ = "query_results"
    __table_args__ = {"schema": "eval"}

    result_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("eval.runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    # Link to operational log — latency data lives there, not duplicated here
    query_id = Column(
        UUID(as_uuid=True),
        ForeignKey("logs.queries.query_id"),
        nullable=True,
    )

    question = Column(Text, nullable=False)
    expected_paper = Column(String, nullable=False)
    expected_answer = Column(Text, nullable=False)
    generated_answer = Column(Text)

    # Retrieval outcome
    recall_hit = Column(Boolean, nullable=False)
    expected_paper_rank = Column(Integer)  # 1-indexed; null if not found in top_k
    expected_paper_score = Column(Float)  # best similarity score from expected paper

    run = relationship("EvalRun", back_populates="query_results")
    retrieved_chunks = relationship(
        "EvalRetrievedChunk",
        back_populates="query_result",
        cascade="all, delete-orphan",
    )


class EvalRetrievedChunk(Base):
    """One row per retrieved chunk per question — enables precision@k calculation."""

    __tablename__ = "retrieved_chunks"
    __table_args__ = {"schema": "eval"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    result_id = Column(
        UUID(as_uuid=True),
        ForeignKey("eval.query_results.result_id", ondelete="CASCADE"),
        nullable=False,
    )

    rank = Column(Integer, nullable=False)
    document_id = Column(String, nullable=False)
    section_type = Column(String)
    section_title = Column(String)
    similarity_score = Column(Float, nullable=False)
    is_expected = Column(Boolean, nullable=False)  # chunk from the expected paper?

    query_result = relationship("EvalQueryResult", back_populates="retrieved_chunks")
