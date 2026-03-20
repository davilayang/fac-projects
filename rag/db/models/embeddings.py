"""Embedding models: vector storage for chunks."""

from sqlalchemy import ARRAY, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from db.models import Base


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
    vector: Column[list[str] | None] = Column(
        ARRAY(String)
    )  # placeholder — swap for pgvector Vector type later
    embedding_model = Column(String)
    embedding_model_params = Column(String)

    chunk = relationship("Chunk", backref="embedding")
