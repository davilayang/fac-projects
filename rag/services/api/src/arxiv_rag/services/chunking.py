import re

import spacy

from langchain_text_splitters import MarkdownHeaderTextSplitter

from arxiv_rag.clients import ArxivMetadata

section_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("#", "title"),
        ("##", "section"),
        ("###", "subsection"),
    ],
    strip_headers=False,
)

nlp = spacy.blank("en")
nlp.add_pipe("sentencizer")

SENTENCES_OVERLAP = 2
MAX_CHUNK_WORDS = 300
MAX_CHUNK_CHARS = 6000


def _is_noise_section(section: str) -> bool:
    return bool(
        re.match(r"^(references|appendix|acknowledgement)", section, re.IGNORECASE)
    )


def _split_with_sentence_overlap(text: str, metadata: dict) -> list[dict]:
    doc = nlp(text)
    sentences = [s.text.strip() for s in doc.sents if s.text.strip()]

    chunks = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence.split())
        if current_len + sentence_len > MAX_CHUNK_WORDS and current:
            chunks.append({"text": " ".join(current), **metadata})
            current = current[-SENTENCES_OVERLAP:]
            current_len = sum(len(s.split()) for s in current)
        current.append(sentence)
        current_len += sentence_len

    if current:
        chunks.append({"text": " ".join(current), **metadata})

    # Hard truncation safety net — catches equations/tables that inflate token count
    for chunk in chunks:
        chunk["text"] = chunk["text"][:MAX_CHUNK_CHARS]

    return chunks


def split_into_chunks(content: str, metadata: ArxivMetadata) -> list[dict]:
    result = []
    for section in section_splitter.split_text(content):
        if _is_noise_section(section.metadata.get("section", "")):
            continue
        chunk_metadata = {
            "arxiv_id": metadata.arxiv_id,
            "title": metadata.title,
            "authors": metadata.authors,
            "published": metadata.published,
            "categories": metadata.categories,
            "primary_category": metadata.primary_category,
            "section": section.metadata.get("section", ""),
            "subsection": section.metadata.get("subsection", ""),
        }
        result.extend(
            _split_with_sentence_overlap(section.page_content, chunk_metadata)
        )
    return result
