import uuid

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ArxivChunk(Base):
    __tablename__ = "arxiv_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    arxiv_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    published: Mapped[datetime | None] = mapped_column()
    categories: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    primary_category: Mapped[str | None] = mapped_column(Text, index=True)
    section: Mapped[str | None] = mapped_column(Text)
    subsection: Mapped[str | None] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))

    def __repr__(self) -> str:
        return f"ArxivChunk(id={self.id}, arxiv_id={self.arxiv_id!r}, section={self.section!r})"
