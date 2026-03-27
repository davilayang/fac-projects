"""SQLAlchemy models for the RAG ingestion database.

All app tables live in the 'ingestion' schema to keep them separate
from Dagster's internal tables in the same Postgres instance.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so Base.metadata.create_all() picks them up,
# and so callers can do: from db.models import DocumentMetadata, Chunk, ...
from db.models.arxiv import (  # noqa: E402, F401
    ArxivPaper,
    DownloadStatus,
    SearchRun,
    SearchRunPaper,
)
from db.models.chunks import Chunk, ChunkProcessingStatus  # noqa: E402, F401
from db.models.documents import (  # noqa: E402, F401
    DocumentMetadata,
    DocumentProcessingStatus,
)
from db.models.embeddings import Embedding  # noqa: E402, F401
