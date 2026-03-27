# Dagster resources specific to PDF extraction.

import dagster as dg

from pipeline.config import EXTRACTED_DIR, PDF_DIR


class ExtractionConfig(dg.ConfigurableResource):
    """Configuration for PDF extraction."""

    raw_dir: str = str(PDF_DIR)
    output_dir: str = str(EXTRACTED_DIR)
