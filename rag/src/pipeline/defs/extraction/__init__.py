import dagster as dg

from .assets import extracted_documents, no_extraction_errors, pending_extractions
from .resources import ExtractionConfig

extraction_job = dg.define_asset_job(
    name="extraction_job",
    selection=[pending_extractions, extracted_documents],
    description="Extract unprocessed PDFs to markdown and record metadata",
)

defs = dg.Definitions(
    assets=[pending_extractions, extracted_documents],
    asset_checks=[no_extraction_errors],
    jobs=[extraction_job],
    resources={
        "extraction_config": ExtractionConfig(),
    },
)
