import dagster as dg

from .assets import (
    document_chunks,
    document_embeddings,
    no_chunking_errors,
    no_embedding_errors,
)
from .resources import ChunkingEmbeddingConfig

chunking_embedding_job = dg.define_asset_job(
    name="chunking_embedding_job",
    selection=[document_chunks, document_embeddings],
    description="Chunk extracted documents and generate OpenAI embeddings",
)

defs = dg.Definitions(
    assets=[document_chunks, document_embeddings],
    asset_checks=[no_chunking_errors, no_embedding_errors],
    jobs=[chunking_embedding_job],
    resources={"chunking_embedding_config": ChunkingEmbeddingConfig()},
)
