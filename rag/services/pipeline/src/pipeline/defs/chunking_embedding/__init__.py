import dagster as dg

from .assets import chunked_embeddings, no_chunking_errors
from .resources import ChunkingEmbeddingConfig

chunking_embedding_job = dg.define_asset_job(
    name="chunking_embedding_job",
    selection=[chunked_embeddings],
    description="Chunk extracted documents and generate OpenAI embeddings",
)

defs = dg.Definitions(
    assets=[chunked_embeddings],
    asset_checks=[no_chunking_errors],
    jobs=[chunking_embedding_job],
    resources={"chunking_embedding_config": ChunkingEmbeddingConfig()},
)
