"""Chunk models: processing status and chunk data."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from db.models import Base


class ChunkProcessingStatus(Base):
    __tablename__ = "chunk_processing_status"
    __table_args__ = {"schema": "ingestion"}

    chunk_id = Column(String, primary_key=True)
    processed_at = Column(DateTime(timezone=True))


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = {"schema": "ingestion"}

    chunk_id = Column(
        String,
        ForeignKey("ingestion.chunk_processing_status.chunk_id", ondelete="CASCADE"),
        primary_key=True,
    )
    document_id = Column(
        String,
        ForeignKey(
            "ingestion.document_processing_status.document_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    chunk_text = Column(Text, nullable=False)
    chunk_strategy = Column(String)

    # Section-level structural metadata
    section_type = Column(
        String, nullable=True
    )  # abstract|introduction|related_work|method|experiment|conclusion|appendix|preamble|other
    section_number = Column(String, nullable=True)  # e.g. "3.2.1"
    section_title = Column(
        String, nullable=True
    )  # e.g. "Collective Adversarial Data Generation"

    # Block-type flags for retrieval filtering
    has_equations = Column(Boolean, nullable=False, default=False)
    has_tables = Column(Boolean, nullable=False, default=False)
    has_figures = Column(Boolean, nullable=False, default=False)

    document = relationship("DocumentProcessingStatus", backref="chunks")
    processing_status = relationship("ChunkProcessingStatus", backref="chunk")
