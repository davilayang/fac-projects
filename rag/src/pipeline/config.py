# Paths and settings for the RAG ingestion pipeline.

import os

from pathlib import Path

# Project layout
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_DIR / "data"
PDF_DIR = DATA_DIR / "pdfs"
EXTRACTED_DIR = DATA_DIR / "extracted"


def build_database_url() -> str:
    """Build a PostgreSQL connection URL from DAGSTER_PG_* env vars."""
    user = os.environ["DAGSTER_PG_USERNAME"]
    password = os.environ["DAGSTER_PG_PASSWORD"]
    host = os.environ.get("DAGSTER_PG_HOST", "localhost")
    port = os.environ.get("DAGSTER_PG_PORT", "5432")
    db = os.environ.get("DAGSTER_PG_DB", "dagster")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"
