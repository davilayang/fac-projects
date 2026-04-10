"""Configurable resources for the chunking & embedding pipeline."""

import os

import dagster as dg


class ChunkingEmbeddingConfig(dg.ConfigurableResource):
    openai_api_key: str = os.environ.get("OPENAI_KEY", "")
    embedding_model: str = "text-embedding-3-small"
    embedding_batch_size: int = 100
    max_chunk_words: int = 300
    sentences_overlap: int = 2
    max_chunk_chars: int = 6000
