"""Chunk models: processing status and chunk data."""

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
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
        ForeignKey(
            "ingestion.chunk_processing_status.chunk_id", ondelete="CASCADE"
        ),
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

    document = relationship("DocumentProcessingStatus", backref="chunks")
    processing_status = relationship("ChunkProcessingStatus", backref="chunk")
