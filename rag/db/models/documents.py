"""Document models: processing status and metadata."""

from sqlalchemy import ARRAY, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from db.models import Base


class DocumentProcessingStatus(Base):
    __tablename__ = "document_processing_status"
    __table_args__ = {"schema": "ingestion"}

    document_id = Column(String, primary_key=True)
    source_file = Column(String, nullable=False)
    output_file = Column(String)
    output_images = Column(String)
    extracted_at = Column(DateTime(timezone=True))
    arxiv_id = Column(
        String,
        ForeignKey("ingestion.arxiv_papers.arxiv_id", ondelete="SET NULL"),
        nullable=True,
    )


class DocumentMetadata(Base):
    __tablename__ = "document_metadata"
    __table_args__ = {"schema": "ingestion"}

    document_id = Column(
        String,
        ForeignKey(
            "ingestion.document_processing_status.document_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    title = Column(String)
    authors: Column[list[str] | None] = Column(ARRAY(String))
    institutes: Column[list[str] | None] = Column(ARRAY(String))
    summary = Column(Text)
    abstract = Column(Text)

    processing_status = relationship("DocumentProcessingStatus", backref="metadata")
