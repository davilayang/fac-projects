import dagster as dg

from .assets import arxiv_search_results, downloaded_pdfs, no_stale_downloads
from .resources import DownloadConfig

arxiv_ingestion_job = dg.define_asset_job(
    name="arxiv_ingestion_job",
    selection=[arxiv_search_results, downloaded_pdfs],
    description="Search arXiv, upsert metadata, and download pending PDFs",
)

defs = dg.Definitions(
    assets=[arxiv_search_results, downloaded_pdfs],
    asset_checks=[no_stale_downloads],
    jobs=[arxiv_ingestion_job],
    resources={
        "download_config": DownloadConfig(),
    },
)
