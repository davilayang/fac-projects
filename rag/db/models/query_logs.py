"""Operational query log models — schema: logs.

Every query the system handles (CLI, API, eval) is recorded here.
Designed to grow indefinitely and support production feedback collection.
"""

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.models import Base


class QueryLog(Base):
    __tablename__ = "queries"
    __table_args__ = {"schema": "logs"}

    query_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asked_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    question = Column(Text, nullable=False)

    # System config at query time
    embedding_model = Column(String, nullable=False)
    generation_model = Column(String)  # null if retrieval-only
    top_k = Column(Integer, nullable=False)

    # What the system returned
    generated_answer = Column(Text)  # null if retrieval-only

    # Latency in milliseconds
    retrieval_latency_ms = Column(Float, nullable=False)
    generation_latency_ms = Column(Float)  # null if retrieval-only
    total_latency_ms = Column(Float, nullable=False)

    # Where the query came from
    source = Column(String, nullable=False, server_default="cli")  # cli | api | eval

    chunks = relationship(
        "QueryChunkLog", back_populates="query", cascade="all, delete-orphan"
    )
    feedback = relationship(
        "QueryFeedback", back_populates="query", cascade="all, delete-orphan"
    )


class QueryChunkLog(Base):
    __tablename__ = "query_chunks"
    __table_args__ = {"schema": "logs"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(
        UUID(as_uuid=True),
        ForeignKey("logs.queries.query_id", ondelete="CASCADE"),
        nullable=False,
    )

    rank = Column(Integer, nullable=False)
    document_id = Column(String, nullable=False)
    section_type = Column(String)
    section_title = Column(String)
    similarity_score = Column(Float, nullable=False)

    query = relationship("QueryLog", back_populates="chunks")


class QueryFeedback(Base):
    """User feedback on a query result — populated once you have a UI or API."""

    __tablename__ = "query_feedback"
    __table_args__ = {"schema": "logs"}

    feedback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(
        UUID(as_uuid=True),
        ForeignKey("logs.queries.query_id", ondelete="CASCADE"),
        nullable=False,
    )
    submitted_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    rating = Column(SmallInteger)  # 1–5
    comment = Column(Text)

    query = relationship("QueryLog", back_populates="feedback")
