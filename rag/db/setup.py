"""Create the ingestion schema and all tables.

Usage:
    python -m db.setup
    python -m db.setup --database-url postgresql://user:pass@host:5432/db
"""

import argparse
import os

from sqlalchemy import create_engine, text

from db.models import Base

_user = os.environ["POSTGRES_USER"]
_password = os.environ["POSTGRES_PASSWORD"]
_db = os.environ["POSTGRES_DB"]
_port = os.environ.get("POSTGRES_PORT", "5432")
DEFAULT_DATABASE_URL = f"postgresql://{_user}:{_password}@localhost:{_port}/{_db}"


def setup_database(database_url: str = DEFAULT_DATABASE_URL) -> None:
    engine = create_engine(database_url)

    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS ingestion"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    Base.metadata.create_all(engine)

    # HNSW index on the vector column for cosine similarity search.
    # Built after table creation; safe to re-run (IF NOT EXISTS).
    with engine.begin() as conn:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS embeddings_vector_hnsw
            ON ingestion.embeddings
            USING hnsw (vector vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
            """
            )
        )

    # Create a convenience view joining chunks with metadata and embeddings
    view_sql = text(
        """
        CREATE OR REPLACE VIEW ingestion.chunks_full AS
        SELECT
            c.chunk_id,
            c.document_id,
            c.chunk_text,
            c.chunk_strategy,
            c.section_type,
            c.section_number,
            c.section_title,
            c.has_equations,
            c.has_tables,
            c.has_figures,
            cp.processed_at AS chunk_processed_at,
            dm.title AS document_title,
            dm.authors AS document_authors,
            dm.institutes AS document_institutes,
            dm.summary AS document_summary,
            dm.abstract AS document_abstract,
            dp.source_file,
            dp.output_file,
            dp.extracted_at AS document_extracted_at,
            e.vector,
            e.embedding_model,
            e.embedding_model_params
        FROM ingestion.chunks c
        LEFT JOIN ingestion.chunk_processing_status cp
            ON c.chunk_id = cp.chunk_id
        LEFT JOIN ingestion.document_processing_status dp
            ON c.document_id = dp.document_id
        LEFT JOIN ingestion.document_metadata dm
            ON c.document_id = dm.document_id
        LEFT JOIN ingestion.embeddings e
            ON c.chunk_id = e.chunk_id
    """
    )

    with engine.begin() as conn:
        conn.execute(view_sql)

    print("Database setup complete.")
    print("  Schema: ingestion")
    print("  Tables: document_processing_status, document_metadata,")
    print("          chunk_processing_status, chunks, embeddings")
    print("  View:   chunks_full")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up the ingestion database")
    parser.add_argument(
        "--database-url",
        default=DEFAULT_DATABASE_URL,
        help=f"Postgres connection URL (default: {DEFAULT_DATABASE_URL})",
    )
    args = parser.parse_args()
    setup_database(args.database_url)
