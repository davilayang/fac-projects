import dagster as dg

from .assets import extract_documents, no_extraction_errors
from .resources import ExtractionConfig

extraction_job = dg.define_asset_job(
    name="extraction_job",
    selection=[extract_documents],
    description="Extract unprocessed PDFs to markdown and record metadata",
)

defs = dg.Definitions(
    assets=[extract_documents],
    asset_checks=[no_extraction_errors],
    jobs=[extraction_job],
    resources={
        "extraction_config": ExtractionConfig(),
    },
)
