# Top-level Dagster Definitions — entrypoint for `dagster dev`.
# Each defs/ subfolder exports its own Definitions; this file merges them
# and adds shared resources (like database) that span multiple pipelines.

import dagster as dg

from pipeline.defs import arxiv_ingestion, chunking_embedding, extraction
from pipeline.resources import DatabaseResource

defs = dg.Definitions.merge(
    arxiv_ingestion.defs,
    extraction.defs,
    chunking_embedding.defs,
    dg.Definitions(resources={"database": DatabaseResource()}),
)
