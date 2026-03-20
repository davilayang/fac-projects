# flows/arxiv_search.py
# Search arxiv, download papers, and track everything in Postgres

import os
import re
import sys

from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import arxiv
import httpx

from prefect import flow, task
from prefect.artifacts import create_markdown_artifact
from prefect.cache_policies import NO_CACHE
from prefect.task_runners import ThreadPoolTaskRunner
from sqlalchemy import create_engine, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from db.models import ArxivPaper, DownloadStatus, SearchRun, SearchRunPaper

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def pdf_local_path(base_dir: str, arxiv_id_with_version: str) -> Path:
    """Compute YYMM-partitioned path for a paper PDF."""
    yymm = arxiv_id_with_version[:4]
    return Path(base_dir) / yymm / f"{arxiv_id_with_version}.pdf"


def clean_arxiv_id(entry_id: str) -> tuple[str, int]:
    """Extract clean arxiv ID and version from entry URL.

    e.g. "http://arxiv.org/abs/2602.03300v1" -> ("2602.03300", 1)
    """
    match = re.search(r"(\d{4}\.\d{4,5})(v(\d+))?", entry_id)
    if not match:
        raise ValueError(f"Cannot parse arxiv ID from: {entry_id}")
    arxiv_id = match.group(1)
    version = int(match.group(3)) if match.group(3) else 1
    return arxiv_id, version


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@task(log_prints=True)
def get_db_engine(database_url: str):
    """Create a SQLAlchemy engine."""
    return create_engine(database_url)


@task(log_prints=True, cache_policy=NO_CACHE)
def create_search_run(
    engine,
    query_string: str,
    date_from: str,
    date_to: str | None,
    max_results: int,
) -> int:
    """Insert a SearchRun row and return its ID."""
    with Session(engine) as session:
        run = SearchRun(
            query_string=query_string,
            date_from=date_from,
            date_to=date_to,
            max_results=max_results,
            sort_by="SubmittedDate",
            sort_order="Descending",
            status="running",
        )
        session.add(run)
        session.commit()
        search_run_id = run.id
    print(f"[arxiv] Created search run {search_run_id}")
    return search_run_id


@task(
    retries=3,
    retry_delay_seconds=[3, 10, 30],
    timeout_seconds=300,
    log_prints=True,
)
def search_arxiv(
    query_string: str,
    date_from: str,
    date_to: str | None,
    max_results: int,
) -> list[dict]:
    """Search arxiv and return a list of paper metadata dicts."""
    client = arxiv.Client(page_size=100, delay_seconds=3, num_retries=5)
    search = arxiv.Search(
        query=query_string,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    date_from_dt = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
    papers: list[dict] = []

    for result in client.results(search):
        if result.published < date_from_dt:
            print(
                f"[arxiv] Reached papers before {date_from}, "
                f"stopping at {len(papers)} results"
            )
            break

        if date_to:
            date_to_dt = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
            if result.published > date_to_dt:
                continue

        arxiv_id, version = clean_arxiv_id(result.entry_id)

        papers.append(
            {
                "arxiv_id": arxiv_id,
                "version": version,
                "title": result.title,
                "authors": [str(a) for a in result.authors],
                "abstract": result.summary,
                "categories": result.categories,
                "primary_category": result.primary_category,
                "published_at": result.published,
                "updated_at": result.updated,
                "pdf_url": result.pdf_url,
                "abstract_url": result.entry_id,
            }
        )

    print(f"[arxiv] Found {len(papers)} papers")
    return papers


@task(log_prints=True, cache_policy=NO_CACHE)
def upsert_paper_metadata(
    engine,
    paper: dict,
    search_run_id: int,
    rank: int,
) -> bool:
    """Upsert paper into arxiv_papers and link to search run.

    Returns True if the paper is new.
    """
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        # Upsert into arxiv_papers
        stmt = pg_insert(ArxivPaper).values(
            arxiv_id=paper["arxiv_id"],
            title=paper["title"],
            authors=paper["authors"],
            abstract=paper["abstract"],
            categories=paper["categories"],
            primary_category=paper["primary_category"],
            published_at=paper["published_at"],
            updated_at=paper["updated_at"],
            pdf_url=paper["pdf_url"],
            abstract_url=paper["abstract_url"],
            latest_version=paper["version"],
            download_status=DownloadStatus.pending,
            first_seen_at=now,
            metadata_updated_at=now,
        )

        # On conflict: update mutable fields only.
        # Reset download_status to pending if a new version is detected.
        stmt = stmt.on_conflict_do_update(
            index_elements=["arxiv_id"],
            set_={
                "title": stmt.excluded.title,
                "authors": stmt.excluded.authors,
                "abstract": stmt.excluded.abstract,
                "categories": stmt.excluded.categories,
                "primary_category": stmt.excluded.primary_category,
                "updated_at": stmt.excluded.updated_at,
                "pdf_url": stmt.excluded.pdf_url,
                "abstract_url": stmt.excluded.abstract_url,
                "latest_version": stmt.excluded.latest_version,
                "metadata_updated_at": now,
            },
        )

        result = session.execute(stmt)
        is_new = result.rowcount == 1 and result.returned_defaults is not None

        # Check if we actually inserted (vs updated) by checking first_seen_at
        existing = session.get(ArxivPaper, paper["arxiv_id"])
        is_new = existing is not None and existing.first_seen_at == now

        # Reset to pending if version changed and already downloaded
        if (
            existing
            and existing.latest_version != paper["version"]
            and existing.download_status
            in (DownloadStatus.downloaded, DownloadStatus.failed)
        ):
            existing.download_status = DownloadStatus.pending

        # Link paper to search run
        link_stmt = pg_insert(SearchRunPaper).values(
            search_run_id=search_run_id,
            arxiv_id=paper["arxiv_id"],
            rank_in_run=rank,
        )
        link_stmt = link_stmt.on_conflict_do_nothing(constraint="uq_search_run_paper")
        session.execute(link_stmt)

        session.commit()

    return is_new


@task(log_prints=True, cache_policy=NO_CACHE)
def get_pending_downloads(engine, limit: int | None = None) -> list[dict]:
    """Get papers with pending or stale downloading status."""
    stale_threshold = datetime.now(timezone.utc).replace(
        minute=datetime.now(timezone.utc).minute - 10
    )

    with Session(engine) as session:
        stmt = select(
            ArxivPaper.arxiv_id,
            ArxivPaper.pdf_url,
            ArxivPaper.latest_version,
        ).where(
            (ArxivPaper.download_status == DownloadStatus.pending)
            | (
                (ArxivPaper.download_status == DownloadStatus.downloading)
                & (ArxivPaper.started_downloading_at < stale_threshold)
            )
        )

        if limit:
            stmt = stmt.limit(limit)

        rows = session.execute(stmt).all()

    papers = [
        {
            "arxiv_id": row.arxiv_id,
            "pdf_url": row.pdf_url,
            "latest_version": row.latest_version,
        }
        for row in rows
    ]
    return papers


@task(
    retries=3,
    retry_delay_seconds=[5, 15, 30],
    timeout_seconds=120,
    task_run_name="download-{paper[arxiv_id]}",
    log_prints=True,
    cache_policy=NO_CACHE,
)
def download_pdf(engine, paper: dict, pdf_dir: str) -> None:
    """Download a single paper PDF to the YYMM-partitioned directory."""
    arxiv_id = paper["arxiv_id"]
    version = paper["latest_version"]
    pdf_url = paper["pdf_url"]
    arxiv_id_with_version = f"{arxiv_id}v{version}"

    # Mark as downloading
    with Session(engine) as session:
        session.execute(
            update(ArxivPaper)
            .where(ArxivPaper.arxiv_id == arxiv_id)
            .values(
                download_status=DownloadStatus.downloading,
                started_downloading_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

    target_path = pdf_local_path(pdf_dir, arxiv_id_with_version)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        response = httpx.get(pdf_url, follow_redirects=True, timeout=60)
        response.raise_for_status()
        target_path.write_bytes(response.content)

        with Session(engine) as session:
            session.execute(
                update(ArxivPaper)
                .where(ArxivPaper.arxiv_id == arxiv_id)
                .values(
                    download_status=DownloadStatus.downloaded,
                    local_pdf_path=str(target_path),
                    last_downloaded_at=datetime.now(timezone.utc),
                    download_error=None,
                )
            )
            session.commit()

        size_kb = target_path.stat().st_size / 1024
        print(f"[arxiv] Downloaded {arxiv_id_with_version} ({size_kb:.1f} KB)")

    except Exception as e:
        with Session(engine) as session:
            session.execute(
                update(ArxivPaper)
                .where(ArxivPaper.arxiv_id == arxiv_id)
                .values(
                    download_status=DownloadStatus.failed,
                    download_error=str(e),
                )
            )
            session.commit()
        raise


@task(log_prints=True, cache_policy=NO_CACHE)
def complete_search_run(
    engine,
    search_run_id: int,
    result_count: int,
    new_papers_count: int,
) -> None:
    """Mark a search run as completed."""
    with Session(engine) as session:
        session.execute(
            update(SearchRun)
            .where(SearchRun.id == search_run_id)
            .values(
                completed_at=datetime.now(timezone.utc),
                result_count=result_count,
                new_papers_count=new_papers_count,
                status="completed",
            )
        )
        session.commit()
    print(
        f"[arxiv_search] Search run {search_run_id} completed: "
        f"{result_count} results, {new_papers_count} new"
    )


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------


@flow(task_runner=ThreadPoolTaskRunner(max_workers=5), log_prints=True)
def arxiv_ingestion_flow(
    query_string: str,
    date_from: str,
    date_to: str | None = None,
    max_results: int = 500,
    pdf_dir: str = "data/pdfs",
    download_limit: int | None = None,
    skip_search: bool = False,
    database_url: str = "",
) -> None:
    """Search arxiv for papers, download PDFs, and track in Postgres.

    Phase 1 (search + upsert): Query arxiv API, upsert paper metadata.
    Phase 2 (download): Download all pending PDFs concurrently.

    Set skip_search=True for backfill mode (download only).
    """
    if not database_url:
        _user = os.environ["PREFECT_DB_USER"]
        _password = os.environ["PREFECT_DB_PASSWORD"]
        _host = os.environ.get("PREFECT_DB_HOST", "localhost")
        _port = os.environ.get("PREFECT_DB_PORT", "5432")
        _db = os.environ["PREFECT_DB_NAME"]
        database_url = f"postgresql://{_user}:{_password}@{_host}:{_port}/{_db}"

    engine = get_db_engine(database_url)

    search_run_id = None
    result_count = 0
    new_count = 0

    # Phase 1: Search + upsert (sequential)
    if not skip_search:
        search_run_id = create_search_run(
            engine, query_string, date_from, date_to, max_results
        )
        papers = search_arxiv(query_string, date_from, date_to, max_results)
        result_count = len(papers)

        for rank, paper in enumerate(papers):
            is_new = upsert_paper_metadata(engine, paper, search_run_id, rank)
            if is_new:
                new_count += 1

    # Release stale connections between phases
    engine.dispose()

    # Phase 2: Download pending papers (concurrent)
    pending = get_pending_downloads(engine, limit=download_limit)
    print(f"[arxiv_search] {len(pending)} papers pending download")
    futures = [download_pdf.submit(engine, paper, pdf_dir) for paper in pending]
    for f in futures:
        f.wait()

    downloaded = sum(1 for f in futures if f.state.is_completed())
    failed = len(futures) - downloaded

    if search_run_id:
        complete_search_run(engine, search_run_id, result_count, new_count)

    # Publish run summary as Prefect artifact
    create_markdown_artifact(
        key="arxiv-run-summary",
        markdown=dedent(
            f"""\
            **Search:** `{query_string}`

            | Metric | Value |
            |---|---|
            | Results found | {result_count} |
            | New papers | {new_count} |
            | Downloaded | {downloaded} |
            | Failed | {failed} |
        """
        ),
        description="Arxiv ingestion run summary",
    )

    print(
        f"[arxiv_search] Done. {result_count} results, {new_count} new, "
        f"{downloaded} downloaded, {failed} failed"
    )


if __name__ == "__main__":
    arxiv_ingestion_flow(
        query_string='ti:"retrieval augmented generation" OR abs:"RAG"',
        date_from="2026-01-01",
        max_results=5,
        pdf_dir="data/pdfs",
    )
