"""Markdown chunking with sentence-level overlap.

Adapted from services/api chunking logic. Pure Python — no Dagster dependency.
"""

import re

import spacy

from langchain_text_splitters import MarkdownHeaderTextSplitter

_section_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("#", "title"),
        ("##", "section"),
        ("###", "subsection"),
    ],
    strip_headers=False,
)

_nlp = spacy.blank("en")
_nlp.add_pipe("sentencizer")

_NOISE_PATTERN = re.compile(
    r"^(references|appendix|acknowledgement)", re.IGNORECASE
)


def _split_with_sentence_overlap(
    text: str,
    metadata: dict,
    max_chunk_words: int,
    sentences_overlap: int,
    max_chunk_chars: int,
) -> list[dict]:
    doc = _nlp(text)
    sentences = [s.text.strip() for s in doc.sents if s.text.strip()]

    chunks: list[dict] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence.split())
        if current_len + sentence_len > max_chunk_words and current:
            chunks.append({"text": " ".join(current), **metadata})
            current = current[-sentences_overlap:]
            current_len = sum(len(s.split()) for s in current)
        current.append(sentence)
        current_len += sentence_len

    if current:
        chunks.append({"text": " ".join(current), **metadata})

    for chunk in chunks:
        chunk["text"] = chunk["text"][:max_chunk_chars]

    return chunks


def split_into_chunks(
    content: str,
    metadata: dict,
    *,
    max_chunk_words: int = 300,
    sentences_overlap: int = 2,
    max_chunk_chars: int = 6000,
) -> list[dict]:
    """Split markdown content into overlapping sentence-based chunks.

    Args:
        content: Markdown text to split.
        metadata: Dict with keys like arxiv_id, title, authors, published,
            categories, primary_category. Attached to each chunk.
        max_chunk_words: Max words per chunk before splitting.
        sentences_overlap: Number of trailing sentences to carry over.
        max_chunk_chars: Hard character truncation per chunk.

    Returns:
        List of dicts, each with 'text' plus all metadata keys,
        plus 'section' and 'subsection' from markdown headers.
    """
    result: list[dict] = []
    for section in _section_splitter.split_text(content):
        if _NOISE_PATTERN.match(section.metadata.get("section", "")):
            continue
        chunk_metadata = {
            **metadata,
            "section": section.metadata.get("section", ""),
            "subsection": section.metadata.get("subsection", ""),
        }
        result.extend(
            _split_with_sentence_overlap(
                section.page_content,
                chunk_metadata,
                max_chunk_words,
                sentences_overlap,
                max_chunk_chars,
            )
        )
    return result
