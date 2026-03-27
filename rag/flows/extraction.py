# flows/extraction.py
# Extracting text and metadata from PDF documents

import os
import sys

from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path when running as a script
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pymupdf
import pymupdf4llm

from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from db.models import DocumentMetadata, DocumentProcessingStatus

# ---------------------------------------------------------------------------
# DAG Tasks
# ---------------------------------------------------------------------------


@task(log_prints=True)
def get_db_engine(database_url: str):
    """Create a SQLAlchemy engine."""
    return create_engine(database_url)


@task(log_prints=True)
def scan_local_folder(raw_dir: str) -> list[Path]:
    """Find all PDF files in the raw data folder."""
    folder = Path(raw_dir)
    if not folder.exists():
        print(f"[extraction] Raw data folder does not exist: {folder}")
        return []

    pdfs = sorted(folder.glob("*.pdf"))
    print(f"[extraction] Found {len(pdfs)} PDF files in {folder}")
    return pdfs


@task(log_prints=True, cache_policy=NO_CACHE)
def filter_unprocessed(engine, pdf_files: list[Path]) -> list[Path]:
    """Check Postgres and return only PDFs not yet processed."""
    with Session(engine) as session:
        stmt = select(DocumentProcessingStatus.source_file)
        processed = {row[0] for row in session.execute(stmt).all()}

    unprocessed = [f for f in pdf_files if str(f) not in processed]
    print(f"[extraction] {len(unprocessed)} unprocessed out of {len(pdf_files)} total")
    return unprocessed


@task(
    retries=2,
    retry_delay_seconds=5,
    timeout_seconds=300,
    task_run_name="extract-{pdf_path.name}",
    log_prints=True,
)
def extract_pdf_to_markdown(pdf_path: Path, output_dir: str) -> Path:
    """Extract a single PDF to markdown using pymupdf4llm."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{pdf_path.stem}.md"

    print(f"[extraction] Extracting {pdf_path.name} → {output_path.name}")
    md_text = pymupdf4llm.to_markdown(str(pdf_path))
    output_path.write_text(md_text, encoding="utf-8")
    print(f"[extraction] Saved {output_path.stat().st_size / 1024:.1f} KB")

    return output_path


def _extract_abstract_from_markdown(md_path: Path) -> str | None:
    """Parse the Abstract section from extracted markdown."""
    import re

    text = md_path.read_text(encoding="utf-8")
    # Match heading variants: # Abstract, ## Abstract, **Abstract**, Abstract\n===
    match = re.search(
        r"(?:^#{1,4}\s*abstract\s*\n|^\*\*abstract\*\*\s*\n)(.*?)(?=^#{1,4}\s|\Z)",
        text,
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    if match:
        return match.group(1).strip() or None
    return None


@task(log_prints=True, task_run_name="metadata-{pdf_path.name}")
def extract_metadata(pdf_path: Path, output_path: Path) -> dict:
    """Extract metadata from a PDF using pymupdf, plus abstract from markdown."""
    doc = pymupdf.open(pdf_path)
    meta = doc.metadata

    raw_authors = meta.get("author", "")
    if raw_authors:
        sep = ";" if ";" in raw_authors else ","
        authors = [a.strip() for a in raw_authors.split(sep) if a.strip()]
    else:
        authors = []

    abstract = _extract_abstract_from_markdown(output_path)
    if abstract:
        print(f"[extraction] Abstract extracted ({len(abstract)} chars)")
    else:
        print("[extraction] No abstract found in markdown")

    return {
        "document_id": pdf_path.stem,
        "title": meta.get("title", ""),
        "authors": authors,
        "page_count": doc.page_count,
        "abstract": abstract,
    }


@task(log_prints=True, cache_policy=NO_CACHE)
def record_extraction(
    engine,
    pdf_path: Path,
    output_path: Path,
    metadata: dict,
) -> None:
    """Write processing status and metadata records to Postgres."""
    with Session(engine) as session:
        status_record = DocumentProcessingStatus(
            document_id=pdf_path.stem,
            source_file=str(pdf_path),
            output_file=str(output_path),
            extracted_at=datetime.now(timezone.utc),
        )
        session.merge(status_record)

        meta_record = DocumentMetadata(
            document_id=pdf_path.stem,
            title=metadata.get("title") or None,
            authors=metadata.get("authors") or None,
        )
        session.merge(meta_record)

        session.commit()
    print(f"[extraction] Recorded extraction: {pdf_path.name}")


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------


@flow(log_prints=True)
def extraction_flow(
    raw_dir: str = "data/pdfs",
    output_dir: str = "data/extracted",
    database_url: str = "",
) -> None:
    """Extract unprocessed PDF documents to markdown.

    1. Scan local folder for PDFs
    2. Filter out already-processed documents (check Postgres)
    3. Extract each PDF to markdown (pymupdf4llm)
    4. Extract metadata (pymupdf)
    5. Record processing status and metadata in Postgres
    """
    # NOTE: docstring shows up in the deployment's "Description"

    if not database_url:
        _user = os.environ["POSTGRES_USER"]
        _password = os.environ["POSTGRES_PASSWORD"]
        _host = os.environ.get("POSTGRES_HOST", "localhost")
        _port = os.environ.get("POSTGRES_PORT", "5432")
        _db = os.environ["POSTGRES_DB"]
        database_url = f"postgresql://{_user}:{_password}@{_host}:{_port}/{_db}"

    engine = get_db_engine(database_url)
    pdf_files = scan_local_folder(raw_dir)

    if not pdf_files:
        print("[extraction] No PDF files found. Nothing to do.")
        return

    unprocessed = filter_unprocessed(engine, pdf_files)

    if not unprocessed:
        print("[extraction] All documents already processed. Nothing to do.")
        return

    for pdf_path in unprocessed:
        output_path = extract_pdf_to_markdown(pdf_path, output_dir)
        metadata = extract_metadata(pdf_path, output_path)  # type: ignore[call-overload]
        record_extraction(engine, pdf_path, output_path, metadata)

    print(f"[extraction] Done. Processed {len(unprocessed)} documents.")


if __name__ == "__main__":
    # "Parameters", used with single run
    extraction_flow(
        raw_dir="data/pdfs",
        output_dir="data/extracted",
    )
