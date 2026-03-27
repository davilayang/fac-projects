# Dagster assets for PDF extraction: scan → fan out → extract → summarize.
#
# Uses a @graph_asset with DynamicOutput to fan out extraction
# across unprocessed PDFs. Concurrency limited to 3 via pool config.

import logging
import re
from pathlib import Path

import dagster as dg

from pipeline.lib.db import filter_unprocessed, record_extraction
from pipeline.lib.pdf_extractor import extract_metadata, extract_to_markdown
from pipeline.resources import DatabaseResource

from .resources import ExtractionConfig

logger = logging.getLogger(__name__)

ASSET_TAGS = {"domain": "rag"}


# ---------------------------------------------------------------------------
# Ops for the extraction graph
# ---------------------------------------------------------------------------


@dg.op(out={"pdf_paths": dg.DynamicOut(str)})
def list_unprocessed_pdfs(
    context: dg.OpExecutionContext,
    database: DatabaseResource,
    extraction_config: ExtractionConfig,
):
    """Scan raw_dir, filter already-processed, yield one DynamicOutput per PDF."""
    raw_dir = Path(extraction_config.raw_dir)

    if not raw_dir.exists():
        context.log.warning("Raw data folder does not exist: %s", raw_dir)
        return

    pdf_files = sorted(raw_dir.rglob("*.pdf"))
    engine = database.get_engine()
    unprocessed = filter_unprocessed(engine, pdf_files)

    context.log.info(
        "%d unprocessed out of %d total PDFs", len(unprocessed), len(pdf_files)
    )

    seen_keys: set[str] = set()
    for pdf_path in unprocessed:
        key = re.sub(r"[^a-zA-Z0-9_]", "_", pdf_path.stem)
        # Deduplicate keys that collapse to the same string
        while key in seen_keys:
            key += "_"
        seen_keys.add(key)
        yield dg.DynamicOutput(str(pdf_path), mapping_key=key, output_name="pdf_paths")


@dg.op(
    tags={"dagster/concurrency_key": "pdf_extraction"},
    retry_policy=dg.RetryPolicy(max_retries=2, delay=5),
)
def extract_single_pdf(
    context: dg.OpExecutionContext,
    pdf_path_str: str,
    database: DatabaseResource,
    extraction_config: ExtractionConfig,
) -> dict:
    """Extract one PDF to markdown, extract metadata, and record in DB."""
    pdf_path = Path(pdf_path_str)
    output_dir = extraction_config.output_dir
    engine = database.get_engine()

    context.log.info("Extracting %s", pdf_path.name)
    output_path = extract_to_markdown(pdf_path, output_dir)
    metadata = extract_metadata(pdf_path)
    record_extraction(engine, pdf_path, output_path, metadata)

    return {
        "file": pdf_path.name,
        "title": (metadata.get("title") or "")[:60],
        "pages": metadata.get("page_count", 0),
        "status": "ok",
    }


@dg.op
def summarize_extractions(
    context: dg.OpExecutionContext,
    results: list[dict],
) -> dg.Output[list[dict]]:
    """Aggregate extraction results and log a summary."""
    extracted = [r for r in results if r.get("status") == "ok"]
    errors = [r for r in results if r.get("status") != "ok"]

    summary_lines = [
        f"**Extracted:** {len(extracted)} documents",
        f"**Errors:** {len(errors)}",
    ]
    if extracted:
        summary_lines.append("\n| file | title | pages |")
        summary_lines.append("| --- | --- | --- |")
        for d in extracted:
            summary_lines.append(
                f"| `{d['file']}` | {d['title']} | {d['pages']} |"
            )

    context.log.info(
        "Extraction complete: %d extracted, %d errors",
        len(extracted),
        len(errors),
    )

    return dg.Output(
        results,
        metadata={
            "extracted": dg.MetadataValue.int(len(extracted)),
            "errors": dg.MetadataValue.int(len(errors)),
            "summary": dg.MetadataValue.md("\n".join(summary_lines)),
        },
    )


# ---------------------------------------------------------------------------
# Graph asset: wires the ops together
# ---------------------------------------------------------------------------


@dg.graph_asset(
    tags=ASSET_TAGS,
    description="Extract unprocessed PDFs via dynamic fanout (max 3 concurrent)",
)
def extract_documents():
    """list unprocessed → fan out extract_single_pdf → collect → summarize."""
    pdf_paths = list_unprocessed_pdfs()
    results = pdf_paths.map(extract_single_pdf)
    return summarize_extractions(results.collect())


@dg.asset_check(asset=extract_documents)
def no_extraction_errors(
    context: dg.AssetCheckExecutionContext,
) -> dg.AssetCheckResult:
    """Verify the last extraction had no errors."""
    event = context.instance.get_latest_materialization_event(
        extract_documents.key
    )
    if event is None:
        return dg.AssetCheckResult(
            passed=False,
            metadata={"reason": "no materialization event found"},
        )

    metadata = event.asset_materialization.metadata  # type: ignore[union-attr]
    error_count = metadata.get("errors", dg.IntMetadataValue(0)).value
    return dg.AssetCheckResult(
        passed=error_count == 0,
        metadata={"error_count": error_count},
    )
