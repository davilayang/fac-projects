# Dagster assets for arXiv ingestion: search → upsert → download.

import logging

from concurrent.futures import ThreadPoolExecutor, as_completed

import dagster as dg

from pipeline.lib.arxiv_client import search_arxiv
from pipeline.lib.db import (
    complete_search_run,
    count_stale_downloads,
    create_search_run,
    get_pending_downloads,
    mark_download_status,
    upsert_paper,
)
from pipeline.lib.pdf_downloader import download_pdf, pdf_local_path
from pipeline.resources import DatabaseResource

from .resources import DownloadConfig

logger = logging.getLogger(__name__)

ASSET_OWNERS = ["team:data-eng"]
ASSET_TAGS = {"domain": "rag"}

# Default search parameters (overridable via RunConfig)
DEFAULT_QUERY = 'ti:"retrieval augmented generation" OR abs:"RAG"'
DEFAULT_DATE_FROM = "2026-01-01"


@dg.asset(
    group_name="arxiv_ingestion",
    compute_kind="api",
    owners=ASSET_OWNERS,
    tags=ASSET_TAGS,
    description="Search arXiv API and upsert paper metadata into Postgres",
    retry_policy=dg.RetryPolicy(max_retries=3, delay=10),
)
def arxiv_search_results(
    context: dg.AssetExecutionContext,
    database: DatabaseResource,
) -> dg.MaterializeResult:
    """Search arXiv, upsert results, and create an audit trail."""
    engine = database.get_engine()

    query_string = DEFAULT_QUERY
    date_from = DEFAULT_DATE_FROM
    date_to = None
    max_results = 500

    search_run_id = create_search_run(
        engine, query_string, date_from, date_to, max_results
    )
    context.log.info("Created search run %d", search_run_id)

    papers = search_arxiv(query_string, date_from, date_to, max_results)
    context.log.info("Found %d papers from arXiv", len(papers))

    new_count = 0
    for rank, paper in enumerate(papers):
        is_new = upsert_paper(engine, paper, search_run_id, rank)
        if is_new:
            new_count += 1

    complete_search_run(engine, search_run_id, len(papers), new_count)

    return dg.MaterializeResult(
        metadata={
            "search_run_id": dg.MetadataValue.int(search_run_id),
            "result_count": dg.MetadataValue.int(len(papers)),
            "new_papers": dg.MetadataValue.int(new_count),
            "query": dg.MetadataValue.text(query_string),
        }
    )


@dg.asset(
    group_name="arxiv_ingestion",
    compute_kind="filesystem",
    deps=[arxiv_search_results],
    owners=ASSET_OWNERS,
    tags=ASSET_TAGS,
    description="Download pending PDFs concurrently to local storage",
)
def downloaded_pdfs(
    context: dg.AssetExecutionContext,
    database: DatabaseResource,
    download_config: DownloadConfig,
) -> dg.MaterializeResult:
    """Download all pending papers using a thread pool."""
    engine = database.get_engine()
    engine.dispose()  # release stale connections before concurrent phase

    pending = get_pending_downloads(engine, limit=download_config.download_limit)
    context.log.info("%d papers pending download", len(pending))

    if not pending:
        return dg.MaterializeResult(
            metadata={
                "downloaded": dg.MetadataValue.int(0),
                "failed": dg.MetadataValue.int(0),
            }
        )

    downloaded = 0
    failed = 0

    def _download_one(paper: dict) -> bool:
        arxiv_id = paper["arxiv_id"]
        from db.models import DownloadStatus

        mark_download_status(engine, arxiv_id, DownloadStatus.downloading)
        target = pdf_local_path(
            download_config.pdf_dir, arxiv_id, paper["latest_version"]
        )
        try:
            download_pdf(paper["pdf_url"], target)
            mark_download_status(
                engine,
                arxiv_id,
                DownloadStatus.downloaded,
                local_pdf_path=str(target),
            )
            return True
        except Exception as exc:
            mark_download_status(
                engine,
                arxiv_id,
                DownloadStatus.failed,
                error=str(exc),
            )
            logger.error("Failed to download %s: %s", arxiv_id, exc)
            return False

    with ThreadPoolExecutor(max_workers=download_config.max_workers) as pool:
        futures = {pool.submit(_download_one, p): p for p in pending}
        for future in as_completed(futures):
            if future.result():
                downloaded += 1
            else:
                failed += 1

    context.log.info("Downloaded %d, failed %d", downloaded, failed)

    summary = (
        f"**Downloaded:** {downloaded} papers\n"
        f"**Failed:** {failed} papers\n"
        f"**Total pending:** {len(pending)}"
    )

    return dg.MaterializeResult(
        metadata={
            "downloaded": dg.MetadataValue.int(downloaded),
            "failed": dg.MetadataValue.int(failed),
            "summary": dg.MetadataValue.md(summary),
        }
    )


@dg.asset_check(asset=downloaded_pdfs)
def no_stale_downloads(
    database: DatabaseResource,
) -> dg.AssetCheckResult:
    """Verify no papers are stuck in DOWNLOADING status for more than 10 min."""
    stale_count = count_stale_downloads(database.get_engine())
    return dg.AssetCheckResult(
        passed=stale_count == 0,
        metadata={"stale_count": stale_count},
    )
