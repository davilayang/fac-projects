# Dagster assets for arXiv ingestion: search → fan out downloads → summarize.
#
# Uses a @graph_asset with DynamicOutput to fan out PDF downloads
# across pending papers. Concurrency limited via pool config.

import logging
import re

import dagster as dg
from db.models import DownloadStatus

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

ASSET_TAGS = {"domain": "rag"}

DEFAULT_QUERY = 'ti:"retrieval augmented generation" OR abs:"RAG"'
DEFAULT_DATE_FROM = "2026-01-01"


# ---------------------------------------------------------------------------
# Ops for the ingestion graph
# ---------------------------------------------------------------------------


@dg.op(out={"pending": dg.DynamicOut(dict)})
def search_and_list_pending(
    context: dg.OpExecutionContext,
    database: DatabaseResource,
    download_config: DownloadConfig,
):
    """Search arXiv, upsert metadata, then yield one DynamicOutput per pending paper."""
    engine = database.get_engine()

    query_string = DEFAULT_QUERY
    date_from = DEFAULT_DATE_FROM
    date_to = None
    max_results = 500

    # Phase 1: Search + upsert
    search_run_id = create_search_run(
        engine, query_string, date_from, date_to, max_results
    )
    context.log.info("Created search run %d", search_run_id)

    papers = search_arxiv(query_string, date_from, date_to, max_results)
    context.log.info("Found %d papers from arXiv", len(papers))

    new_count = 0
    for rank, paper in enumerate(papers):
        if upsert_paper(engine, paper, search_run_id, rank):
            new_count += 1

    complete_search_run(engine, search_run_id, len(papers), new_count)
    context.log.info(
        "Search run %d complete: %d results, %d new",
        search_run_id, len(papers), new_count,
    )

    # Phase 2: Yield pending downloads
    pending = get_pending_downloads(engine, limit=download_config.download_limit)
    context.log.info("%d papers pending download", len(pending))

    seen_keys: set[str] = set()
    for paper in pending:
        key = re.sub(r"[^a-zA-Z0-9_]", "_", paper["arxiv_id"])
        while key in seen_keys:
            key += "_"
        seen_keys.add(key)
        yield dg.DynamicOutput(paper, mapping_key=key, output_name="pending")


@dg.op(
    retry_policy=dg.RetryPolicy(max_retries=3, delay=10),
)
def download_single_pdf(
    context: dg.OpExecutionContext,
    paper: dict,
    database: DatabaseResource,
    download_config: DownloadConfig,
) -> dict:
    """Download one paper's PDF and update its status in DB."""
    engine = database.get_engine()
    arxiv_id = paper["arxiv_id"]

    mark_download_status(engine, arxiv_id, DownloadStatus.downloading)
    target = pdf_local_path(
        download_config.pdf_dir, arxiv_id, paper["latest_version"]
    )

    try:
        download_pdf(paper["pdf_url"], target)
        mark_download_status(
            engine, arxiv_id, DownloadStatus.downloaded,
            local_pdf_path=str(target),
        )
        context.log.info("Downloaded %s", arxiv_id)
        return {"arxiv_id": arxiv_id, "status": "ok"}
    except Exception as exc:
        mark_download_status(
            engine, arxiv_id, DownloadStatus.failed,
            error=str(exc),
        )
        context.log.error("Failed to download %s: %s", arxiv_id, exc)
        raise


@dg.op
def summarize_downloads(
    context: dg.OpExecutionContext,
    results: list[dict],
) -> dg.Output[list[dict]]:
    """Aggregate download results and produce a summary."""
    downloaded = [r for r in results if r.get("status") == "ok"]
    failed = [r for r in results if r.get("status") != "ok"]

    summary_lines = [
        f"**Downloaded:** {len(downloaded)} papers",
        f"**Failed:** {len(failed)} papers",
        f"**Total:** {len(results)} papers",
    ]
    if downloaded:
        summary_lines.append("\n| arxiv_id | status |")
        summary_lines.append("| --- | --- |")
        for d in downloaded:
            summary_lines.append(f"| `{d['arxiv_id']}` | {d['status']} |")

    context.log.info(
        "Downloads complete: %d downloaded, %d failed",
        len(downloaded), len(failed),
    )

    return dg.Output(
        results,
        metadata={
            "downloaded": dg.MetadataValue.int(len(downloaded)),
            "failed": dg.MetadataValue.int(len(failed)),
            "summary": dg.MetadataValue.md("\n".join(summary_lines)),
        },
    )


# ---------------------------------------------------------------------------
# Graph asset
# ---------------------------------------------------------------------------


@dg.graph_asset(
    tags=ASSET_TAGS,
    description="Search arXiv, upsert metadata, and download pending PDFs via dynamic fanout",
)
def arxiv_ingestion():
    """search + upsert → fan out download_single_pdf → collect → summarize."""
    pending = search_and_list_pending()
    results = pending.map(download_single_pdf)
    return summarize_downloads(results.collect())


@dg.asset_check(asset=arxiv_ingestion)
def no_stale_downloads(
    database: DatabaseResource,
) -> dg.AssetCheckResult:
    """Verify no papers are stuck in DOWNLOADING status for more than 10 min."""
    stale_count = count_stale_downloads(database.get_engine())
    return dg.AssetCheckResult(
        passed=stale_count == 0,
        metadata={"stale_count": stale_count},
    )
