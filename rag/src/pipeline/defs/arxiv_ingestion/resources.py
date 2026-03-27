# Dagster resources specific to arXiv ingestion.

import dagster as dg

from pipeline.config import PDF_DIR


class DownloadConfig(dg.ConfigurableResource):
    """Configuration for PDF downloads."""

    pdf_dir: str = str(PDF_DIR)
    max_workers: int = 5
    download_limit: int | None = None
