"""Embedding models: vector storage for chunks."""

import os

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from db.models import Base

# Dimensionality of the embedding vector. Must match the chosen model.
# Set EMBEDDING_DIM env var before running db-setup when changing models.
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "768"))


class Embedding(Base):
    __tablename__ = "embeddings"
    __table_args__ = {"schema": "ingestion"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id = Column(
        String,
        ForeignKey("ingestion.chunks.chunk_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    vector = Column(Vector(EMBEDDING_DIM), nullable=True)
    embedding_model = Column(String)
    embedding_model_params = Column(String)

    chunk = relationship("Chunk", backref="embedding")
