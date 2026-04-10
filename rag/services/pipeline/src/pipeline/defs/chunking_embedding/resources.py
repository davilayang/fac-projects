"""Configurable resources for the chunking & embedding pipeline."""

import os

import dagster as dg

from pipeline.config import CHUNKS_DIR


class ChunkingEmbeddingConfig(dg.ConfigurableResource):
    chunks_dir: str = str(CHUNKS_DIR)
    openai_api_key: str = os.environ.get("OPENAI_KEY", "")
    embedding_model: str = "text-embedding-3-small"
    embedding_batch_size: int = 100
    max_chunk_words: int = 300
    sentences_overlap: int = 2
    max_chunk_chars: int = 6000
