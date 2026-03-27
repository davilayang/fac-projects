# Dagster assets for PDF extraction: scan → filter → extract → record.

import logging
from pathlib import Path

import dagster as dg

from pipeline.lib.db import filter_unprocessed, record_extraction
from pipeline.lib.pdf_extractor import extract_metadata, extract_to_markdown
from pipeline.resources import DatabaseResource

from .resources import ExtractionConfig

logger = logging.getLogger(__name__)

ASSET_OWNERS = ["team:data-eng"]
ASSET_TAGS = {"domain": "rag"}


@dg.asset(
    group_name="extraction",
    compute_kind="filesystem",
    owners=ASSET_OWNERS,
    tags=ASSET_TAGS,
    description="Scan local PDF folder and identify unprocessed documents",
)
def pending_extractions(
    context: dg.AssetExecutionContext,
    database: DatabaseResource,
    extraction_config: ExtractionConfig,
) -> dg.MaterializeResult:
    """Scan raw_dir for PDFs and filter out already-processed ones."""
    raw_dir = Path(extraction_config.raw_dir)

    if not raw_dir.exists():
        context.log.warning("Raw data folder does not exist: %s", raw_dir)
        return dg.MaterializeResult(
            metadata={
                "total_pdfs": dg.MetadataValue.int(0),
                "unprocessed": dg.MetadataValue.int(0),
            }
        )

    pdf_files = sorted(raw_dir.rglob("*.pdf"))
    engine = database.get_engine()
    unprocessed = filter_unprocessed(engine, pdf_files)

    context.log.info(
        "%d unprocessed out of %d total PDFs", len(unprocessed), len(pdf_files)
    )

    return dg.MaterializeResult(
        metadata={
            "total_pdfs": dg.MetadataValue.int(len(pdf_files)),
            "unprocessed": dg.MetadataValue.int(len(unprocessed)),
        }
    )


@dg.asset(
    group_name="extraction",
    compute_kind="pymupdf",
    deps=[pending_extractions],
    owners=ASSET_OWNERS,
    tags=ASSET_TAGS,
    description="Extract unprocessed PDFs to markdown and record metadata",
    retry_policy=dg.RetryPolicy(max_retries=2, delay=5),
)
def extracted_documents(
    context: dg.AssetExecutionContext,
    database: DatabaseResource,
    extraction_config: ExtractionConfig,
) -> dg.MaterializeResult:
    """Extract each unprocessed PDF to markdown, extract metadata, record in DB."""
    raw_dir = Path(extraction_config.raw_dir)
    output_dir = extraction_config.output_dir
    engine = database.get_engine()

    if not raw_dir.exists():
        return dg.MaterializeResult(
            metadata={"extracted": dg.MetadataValue.int(0)}
        )

    pdf_files = sorted(raw_dir.rglob("*.pdf"))
    unprocessed = filter_unprocessed(engine, pdf_files)

    if not unprocessed:
        context.log.info("All documents already processed.")
        return dg.MaterializeResult(
            metadata={"extracted": dg.MetadataValue.int(0)}
        )

    extracted_count = 0
    error_count = 0
    details: list[dict] = []

    for pdf_path in unprocessed:
        try:
            output_path = extract_to_markdown(pdf_path, output_dir)
            metadata = extract_metadata(pdf_path)
            record_extraction(engine, pdf_path, output_path, metadata)
            extracted_count += 1
            details.append(
                {
                    "file": pdf_path.name,
                    "title": (metadata.get("title") or "")[:60],
                    "pages": metadata.get("page_count", 0),
                }
            )
        except Exception as exc:
            logger.error("Failed to extract %s: %s", pdf_path.name, exc)
            error_count += 1

    # Build markdown summary
    summary_lines = [
        f"**Extracted:** {extracted_count} documents",
        f"**Errors:** {error_count}",
    ]
    if details:
        summary_lines.append("\n| file | title | pages |")
        summary_lines.append("| --- | --- | --- |")
        for d in details:
            summary_lines.append(
                f"| `{d['file']}` | {d['title']} | {d['pages']} |"
            )

    return dg.MaterializeResult(
        metadata={
            "extracted": dg.MetadataValue.int(extracted_count),
            "errors": dg.MetadataValue.int(error_count),
            "summary": dg.MetadataValue.md("\n".join(summary_lines)),
        }
    )


@dg.asset_check(asset=extracted_documents)
def no_extraction_errors(
    context: dg.AssetCheckExecutionContext,
) -> dg.AssetCheckResult:
    """Verify the last extraction had no errors."""
    events = context.instance.get_latest_materialization_event(
        extracted_documents.key
    )
    if events is None:
        return dg.AssetCheckResult(passed=True)

    metadata = events.asset_materialization.metadata  # type: ignore[union-attr]
    error_count = metadata.get("errors", dg.IntMetadataValue(0)).value
    return dg.AssetCheckResult(
        passed=error_count == 0,
        metadata={"error_count": error_count},
    )
