"""SQLAlchemy models for the fnc-ingestion database.

All app tables live in the 'ingestion' schema to avoid collisions
with Prefect's internal tables in the same Postgres instance.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so Base.metadata.create_all() picks them up,
# and so callers can do: from db.models import DocumentMetadata, Chunk, ...
from db.models.chunks import Chunk, ChunkProcessingStatus  # noqa: E402, F401
from db.models.documents import (  # noqa: E402, F401
    DocumentMetadata,
    DocumentProcessingStatus,
)
from db.models.embeddings import Embedding  # noqa: E402, F401
from db.models.eval_tracking import (  # noqa: E402
    EvalQueryResult as EvalQueryResult,
)
from db.models.eval_tracking import (
    EvalRetrievedChunk as EvalRetrievedChunk,
)
from db.models.eval_tracking import (
    EvalRun as EvalRun,
)
from db.models.query_logs import (  # noqa: E402
    QueryChunkLog as QueryChunkLog,
)
from db.models.query_logs import (
    QueryFeedback as QueryFeedback,
)
from db.models.query_logs import (
    QueryLog as QueryLog,
)
