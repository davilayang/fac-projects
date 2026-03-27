# flows/chunking.py
# Paragraph-based section-aware chunking for scientific papers.
#
# Strategy: paragraph_v1
#
# Algorithm
# ---------
# 1. Pre-process: strip References section, page-break artefacts, author
#    affiliation blockquotes.
# 2. Parse document into a flat list of sections using ## headings.
#    Section number depth (e.g. "3.2.1" = depth 3) encodes logical hierarchy
#    because pymupdf4llm flattens all headings to ##.
# 3. Assign each section a type (abstract, introduction, method, …) and keep
#    Abstract as a guaranteed single chunk.
# 4. For every other section body exceeding MAX_TOKENS, split by blank-line
#    paragraph boundaries, falling back to sentence boundaries for oversized
#    single paragraphs.
# 5. Atomic blocks (equation+context, tables, algorithm pseudocode, figure
#    captions) are never split. Standalone equation placeholders are merged
#    with their surrounding paragraph.
# 6. Apply 2-sentence overlap between consecutive sub-chunks within a section.
# 7. Merge orphan sub-chunks below MIN_TOKENS into the preceding chunk.
# 8. Prepend the section heading to each sub-chunk for embedding context.
# 9. Detect has_equations / has_tables / has_figures per final chunk.

import hashlib
import os
import re
import sys

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import tiktoken

from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from db.models import DocumentProcessingStatus
from db.models.chunks import Chunk, ChunkProcessingStatus

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHUNK_STRATEGY = "paragraph_v1"

_ENCODING = tiktoken.get_encoding("cl100k_base")
MAX_TOKENS = 400  # hard upper target; stays within SPECTER2's 512-token limit
MIN_TOKENS = 50  # orphan threshold — merge below this into preceding chunk
OVERLAP_SENTENCES = 2


def _count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def _chunk_id(document_id: str, index: int) -> str:
    raw = f"{document_id}::{index:06d}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# All headings are ## in pymupdf4llm output regardless of logical level
_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)

# Section number prefix: "3", "3.2", "3.2.1", "A", "A.1", "I", "II", "IV"
_ARABIC_NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)[.\s]")
_APPENDIX_LETTER_RE = re.compile(r"^([A-Z])(?:[.\s]|$)")

# Markdown bold/italic cleanup
_MD_MARKUP_RE = re.compile(r"\*+|_(?=\S)")

# Standalone equation placeholder (entire paragraph)
_STANDALONE_EQ_RE = re.compile(
    r"^\*\*==> picture \[\d+ x \d+\] intentionally omitted <==\*\*$"
)
# Any equation placeholder anywhere in text
_ANY_EQ_RE = re.compile(r"\*\*==> picture \[\d+ x \d+\] intentionally omitted <==\*\*")

# Picture text block
_PICTURE_TEXT_RE = re.compile(
    r"\*\*----- Start of picture text -----\*\*.*?\*\*----- End of picture text -----\*\*",
    re.DOTALL,
)

# Table line
_TABLE_LINE_RE = re.compile(r"^\|", re.MULTILINE)

# Figure caption
_FIGURE_CAPTION_RE = re.compile(r"^_Figure \d+[._]", re.MULTILINE)

# Table caption
_TABLE_CAPTION_RE = re.compile(r"^_Table \d+[._]", re.MULTILINE)

# Mathematical continuation phrase after an equation
_CONTINUATION_RE = re.compile(
    r"^(?:where|such that|which|we have|note that|here,|in which|and\s+\w)",
    re.IGNORECASE,
)

# Sentence boundary (end-of-sentence punctuation followed by a capital)
_SENT_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\[])")

# Author affiliation blockquote lines near the preamble
_AFFILIATION_LINE_RE = re.compile(
    r"^>\s*.*(?:University|Institute|Lab|Research|Department|Corporation|Inc\.|Ltd\.)",
    re.IGNORECASE,
)

# Bare page number line
_PAGE_NUM_RE = re.compile(r"^\s*\d{1,3}\s*$")


# ---------------------------------------------------------------------------
# Section dataclass
# ---------------------------------------------------------------------------


@dataclass
class _Section:
    raw_heading: str  # e.g. "## **3.2.1. Collective Adversarial Data Generation**"
    number: str  # e.g. "3.2.1" | "A.1" | ""
    depth: int  # 0 = no number, 1 = top-level, 2 = subsection, 3 = sub-sub
    title: str  # clean title without number prefix or markup
    section_type: str  # abstract | introduction | related_work | method | …
    body: str  # content exclusive to this section


# ---------------------------------------------------------------------------
# Paragraph dataclass
# ---------------------------------------------------------------------------


@dataclass
class _Para:
    text: str
    is_atomic: bool  # must not be split (equation context, table, figure, algorithm)


# ---------------------------------------------------------------------------
# Pre-processing
# ---------------------------------------------------------------------------


def _preprocess(text: str, document_title: str = "") -> str:
    """Strip noise before any chunking logic.

    Removes:
    - The References section and everything after it (up to the first appendix
      heading, which is kept).
    - Bare page-number lines.
    - Repeated page-title headers (lines that match the document title exactly).
    - Author affiliation blockquotes near the preamble.
    """
    # Strip References section.
    # Keep content up to (but not including) the References heading.
    # Appendices that follow References are kept because they are valid retrieval
    # targets — we stop stripping at the first appendix heading.
    refs_re = re.compile(
        r"^##\s+\*{0,2}References\*{0,2}\s*$", re.MULTILINE | re.IGNORECASE
    )
    appendix_re = re.compile(r"^##\s+\*{0,2}[A-Z][.\s]", re.MULTILINE)
    m = refs_re.search(text)
    if m:
        appendix_after = appendix_re.search(text, m.end())
        if appendix_after:
            text = text[: m.start()] + "\n\n" + text[appendix_after.start() :]
        else:
            text = text[: m.start()]

    # Strip bare page numbers and repeated title headers line-by-line.
    clean_title = re.sub(_MD_MARKUP_RE, "", document_title).strip().lower()
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if _PAGE_NUM_RE.match(stripped):
            continue
        if (
            clean_title
            and re.sub(_MD_MARKUP_RE, "", stripped).strip().lower() == clean_title
        ):
            continue
        if _AFFILIATION_LINE_RE.match(stripped):
            continue
        lines.append(line)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section parsing
# ---------------------------------------------------------------------------


def _clean_heading_text(raw: str) -> str:
    """Remove markdown bold/italic markers and strip whitespace."""
    return re.sub(_MD_MARKUP_RE, "", raw).strip()


def _parse_section_number(title: str) -> tuple[str, int]:
    """Extract section number and logical depth from clean heading title.

    Returns (number_str, depth):
      "3.2.1 Title" → ("3.2.1", 3)
      "A.1 Title"   → ("A.1",   2)
      "Title"       → ("",      0)
    """
    m = _ARABIC_NUM_RE.match(title)
    if m:
        num = m.group(1)
        return num, len(num.split("."))
    m = _APPENDIX_LETTER_RE.match(title)
    if m:
        letter = m.group(1)
        # Check for sub-appendix like "A.1"
        sub = re.match(r"^[A-Z]\.(\d+(?:\.\d+)*)", title)
        if sub:
            return title.split()[0], 1 + len(sub.group(1).split("."))
        return letter, 1
    return "", 0


def _classify_section_type(number: str, title: str) -> str:
    t = title.lower()
    # Appendix: single uppercase letter section number or title contains "appendix"
    if re.match(r"^[A-Z](?:\.\d+)*$", number) or "appendix" in t:
        return "appendix"
    if "abstract" in t:
        return "abstract"
    # Introduction is typically section "1" at top level
    top = number.split(".")[0] if number else ""
    if "introduction" in t or top == "1":
        return "introduction"
    if any(
        k in t
        for k in (
            "related work",
            "related",
            "background",
            "prior work",
            "literature review",
        )
    ):
        return "related_work"
    if any(
        k in t
        for k in ("conclusion", "discussion", "future work", "limitation", "summary")
    ):
        return "conclusion"
    if any(
        k in t
        for k in (
            "experiment",
            "evaluation",
            "result",
            "ablation",
            "benchmark",
            "analysis",
        )
    ):
        return "experiment"
    if any(
        k in t
        for k in (
            "method",
            "approach",
            "framework",
            "algorithm",
            "model",
            "our ",
            "proposed",
        )
    ):
        return "method"
    return "other"


def _parse_sections(text: str) -> list[_Section]:
    """Parse flat ## heading structure into a list of _Section objects."""
    matches = list(_HEADING_RE.finditer(text))
    sections: list[_Section] = []

    # Preamble — content before the first heading (title, authors)
    if matches:
        preamble_body = text[: matches[0].start()].strip()
        if preamble_body:
            sections.append(
                _Section(
                    raw_heading="",
                    number="",
                    depth=0,
                    title="Preamble",
                    section_type="preamble",
                    body=preamble_body,
                )
            )

    for i, m in enumerate(matches):
        raw_heading = m.group(0)
        heading_text = m.group(2).strip()
        clean = _clean_heading_text(heading_text)
        number, depth = _parse_section_number(clean)

        # Remove number prefix to get the pure title
        if number:
            title = re.sub(
                r"^\d+(?:\.\d+)*[.\s]+|^[A-Z](?:\.\d+)*[.\s]+", "", clean
            ).strip()
        else:
            title = clean

        section_type = _classify_section_type(number, title)

        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()

        sections.append(
            _Section(
                raw_heading=raw_heading,
                number=number,
                depth=depth,
                title=title,
                section_type=section_type,
                body=body,
            )
        )

    return sections


# ---------------------------------------------------------------------------
# Paragraph segmentation
# ---------------------------------------------------------------------------


def _segment_paragraphs(body: str) -> list[_Para]:
    """Split body into paragraphs and classify each."""
    raw = [p.strip() for p in re.split(r"\n{2,}", body) if p.strip()]
    paras: list[_Para] = []

    for p in raw:
        is_table = bool(_TABLE_LINE_RE.search(p))
        is_picture_text = bool(_PICTURE_TEXT_RE.search(p))
        is_figure_cap = bool(_FIGURE_CAPTION_RE.match(p))
        is_table_cap = bool(_TABLE_CAPTION_RE.match(p))
        has_inline_eq = bool(_ANY_EQ_RE.search(p))
        is_standalone_eq = bool(_STANDALONE_EQ_RE.match(p.strip()))

        is_atomic = (
            is_table
            or is_picture_text
            or is_figure_cap
            or is_table_cap
            or is_standalone_eq
            or (has_inline_eq and not is_table)
        )

        paras.append(_Para(text=p, is_atomic=is_atomic))

    return paras


def _merge_equation_context(paras: list[_Para]) -> list[_Para]:
    """Merge standalone equation/picture-text paragraphs with surrounding context.

    - A standalone equation is merged INTO the preceding paragraph (they form
      an inseparable semantic unit).
    - If the paragraph immediately after an equation starts with a mathematical
      continuation phrase ("where …", "such that …"), it is also merged.
    - Figure captions are merged with the preceding content paragraph.
    """
    if not paras:
        return paras

    result: list[_Para] = []
    i = 0
    while i < len(paras):
        p = paras[i]
        is_standalone = (
            _STANDALONE_EQ_RE.match(p.text.strip())
            or _PICTURE_TEXT_RE.search(p.text)
            or _FIGURE_CAPTION_RE.match(p.text)
            or _TABLE_CAPTION_RE.match(p.text)
        )

        if is_standalone and result:
            prev = result[-1]
            merged = prev.text + "\n\n" + p.text

            # Also absorb a following continuation paragraph
            if (
                i + 1 < len(paras)
                and _CONTINUATION_RE.match(paras[i + 1].text)
                and not _TABLE_LINE_RE.search(paras[i + 1].text)
            ):
                merged += "\n\n" + paras[i + 1].text
                i += 1

            result[-1] = _Para(text=merged, is_atomic=True)
            i += 1
            continue

        result.append(p)
        i += 1

    return result


# ---------------------------------------------------------------------------
# Sentence utilities
# ---------------------------------------------------------------------------


def _split_sentences(text: str) -> list[str]:
    parts = _SENT_BOUNDARY_RE.split(text)
    return [s.strip() for s in parts if s.strip()]


def _tail_sentences(text: str, n: int) -> list[str]:
    sents = _split_sentences(text)
    return sents[-n:] if sents else []


def _overlap_prefix(tail: list[str]) -> str:
    return f"[...] {' '.join(tail)}\n\n" if tail else ""


# ---------------------------------------------------------------------------
# Sentence-level splitting (Tier 3 fallback)
# ---------------------------------------------------------------------------


def _sentence_chunks(
    text: str, max_tokens: int, tail: list[str], has_prior: bool
) -> list[str]:
    """Split text at sentence boundaries when paragraph splitting isn't enough."""
    sentences = _split_sentences(text)
    if not sentences:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    current_tail = list(tail)

    for sent in sentences:
        tok = _count_tokens(sent)
        if current_tokens + tok > max_tokens and current:
            prefix = _overlap_prefix(current_tail) if (chunks or has_prior) else ""
            chunks.append(prefix + " ".join(current))
            n = min(OVERLAP_SENTENCES, len(current))
            current_tail = current[-n:]
            current = []
            current_tokens = 0
        current.append(sent)
        current_tokens += tok

    if current:
        prefix = _overlap_prefix(current_tail) if (chunks or has_prior) else ""
        chunks.append(prefix + " ".join(current))

    return chunks


# ---------------------------------------------------------------------------
# Paragraph packing (Tiers 1 & 2)
# ---------------------------------------------------------------------------


def _pack_paragraphs(paras: list[_Para], max_tokens: int) -> list[str]:
    """Pack paragraphs into chunks by size, falling back to sentence splitting.

    Breaks at blank-line paragraph boundaries when adding the next paragraph
    would exceed max_tokens. Sentence-splits any single oversized non-atomic
    paragraph as a last resort.
    """
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    tail: list[str] = []

    def _flush() -> None:
        nonlocal current, current_tokens, tail
        if not current:
            return
        prefix = _overlap_prefix(tail) if chunks else ""
        chunks.append(prefix + "\n\n".join(current))
        tail = _tail_sentences(current[-1], OVERLAP_SENTENCES)
        current = []
        current_tokens = 0

    for para in paras:
        tok = _count_tokens(para.text)

        # Single paragraph exceeds budget
        if tok > max_tokens:
            if para.is_atomic:
                # Emit intact even if oversized — correctness over size compliance
                _flush()
                prefix = _overlap_prefix(tail) if chunks else ""
                chunks.append(prefix + para.text)
                tail = _tail_sentences(para.text, OVERLAP_SENTENCES)
            else:
                _flush()
                sub = _sentence_chunks(para.text, max_tokens, tail, bool(chunks))
                chunks.extend(sub)
                if sub:
                    tail = _tail_sentences(sub[-1], OVERLAP_SENTENCES)
            continue

        if current and current_tokens + tok > max_tokens:
            _flush()

        current.append(para.text)
        current_tokens += tok

    _flush()
    return chunks


# ---------------------------------------------------------------------------
# Orphan merging
# ---------------------------------------------------------------------------


def _merge_orphans(chunks: list[str], min_tokens: int) -> list[str]:
    """Merge sub-chunks below min_tokens into the preceding chunk."""
    if not chunks:
        return chunks
    result = [chunks[0]]
    for chunk in chunks[1:]:
        if _count_tokens(chunk) < min_tokens:
            result[-1] = result[-1] + "\n\n" + chunk
        else:
            result.append(chunk)
    return result


# ---------------------------------------------------------------------------
# Block-type detection
# ---------------------------------------------------------------------------


def _detect_block_types(text: str) -> tuple[bool, bool, bool]:
    """Return (has_equations, has_tables, has_figures)."""
    return (
        bool(_ANY_EQ_RE.search(text)),
        bool(_TABLE_LINE_RE.search(text)),
        bool(_FIGURE_CAPTION_RE.search(text)),
    )


# ---------------------------------------------------------------------------
# ChunkData
# ---------------------------------------------------------------------------


@dataclass
class ChunkData:
    text: str
    section_number: str
    section_title: str
    section_type: str
    has_equations: bool = False
    has_tables: bool = False
    has_figures: bool = False


# ---------------------------------------------------------------------------
# Per-section chunking
# ---------------------------------------------------------------------------


def _chunks_for_section(section: _Section) -> list[ChunkData]:
    """Split a single section into one or more ChunkData objects."""
    body = section.body
    if not body:
        return []

    heading_prefix = (section.raw_heading + "\n\n") if section.raw_heading else ""

    # Abstract is always a single chunk — never split
    if section.section_type == "abstract":
        text = heading_prefix + body
        eq, tbl, fig = _detect_block_types(text)
        return [
            ChunkData(
                text=text,
                section_number=section.number,
                section_title=section.title,
                section_type=section.section_type,
                has_equations=eq,
                has_tables=tbl,
                has_figures=fig,
            )
        ]

    # Sections that fit within the budget — single chunk
    if _count_tokens(body) <= MAX_TOKENS:
        text = heading_prefix + body
        eq, tbl, fig = _detect_block_types(text)
        return [
            ChunkData(
                text=text,
                section_number=section.number,
                section_title=section.title,
                section_type=section.section_type,
                has_equations=eq,
                has_tables=tbl,
                has_figures=fig,
            )
        ]

    # Section exceeds budget — apply paragraph packing with fallbacks
    paras = _segment_paragraphs(body)
    paras = _merge_equation_context(paras)
    raw_chunks = _pack_paragraphs(paras, MAX_TOKENS)
    raw_chunks = _merge_orphans(raw_chunks, MIN_TOKENS)

    result: list[ChunkData] = []
    for chunk_body in raw_chunks:
        # Prepend section heading to every sub-chunk for embedding context
        text = heading_prefix + chunk_body
        eq, tbl, fig = _detect_block_types(text)
        result.append(
            ChunkData(
                text=text,
                section_number=section.number,
                section_title=section.title,
                section_type=section.section_type,
                has_equations=eq,
                has_tables=tbl,
                has_figures=fig,
            )
        )

    return result


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def chunk_markdown(text: str, document_title: str = "") -> list[ChunkData]:
    """Convert a full extracted markdown document into a list of ChunkData.

    This is the pure logic layer — no database or Prefect dependencies.
    """
    text = _preprocess(text, document_title)
    sections = _parse_sections(text)

    chunks: list[ChunkData] = []
    for section in sections:
        # Skip depth-1 section intros that are below the orphan threshold
        # (a transitional sentence before the first subsection)
        if section.depth == 1 and section.section_type not in (
            "abstract",
            "introduction",
        ):
            if _count_tokens(section.body) < MIN_TOKENS:
                continue
        chunks.extend(_chunks_for_section(section))

    return chunks


# ---------------------------------------------------------------------------
# Prefect tasks
# ---------------------------------------------------------------------------


@task(log_prints=True)
def get_db_engine(database_url: str):
    return create_engine(database_url)


@task(log_prints=True, cache_policy=NO_CACHE)
def get_unchunked_documents(engine, extracted_dir: str) -> list[tuple[str, Path]]:
    """Return (document_id, md_path) pairs not yet chunked with current strategy."""
    extracted = Path(extracted_dir)
    if not extracted.exists():
        print(f"[chunking] Extracted dir not found: {extracted}")
        return []

    md_files = {f.stem: f for f in extracted.glob("*.md")}

    with Session(engine) as session:
        extracted_ids = {
            row[0]
            for row in session.execute(
                select(DocumentProcessingStatus.document_id)
            ).all()
        }
        chunked_ids = {
            row[0]
            for row in session.execute(
                select(Chunk.document_id)
                .where(Chunk.chunk_strategy == CHUNK_STRATEGY)
                .distinct()
            ).all()
        }

    pending_ids = extracted_ids - chunked_ids
    result = [
        (doc_id, md_files[doc_id]) for doc_id in pending_ids if doc_id in md_files
    ]
    print(f"[chunking] {len(result)} documents pending chunking")
    return result


@task(
    retries=2,
    retry_delay_seconds=5,
    timeout_seconds=120,
    task_run_name="chunk-{document_id}",
    cache_policy=NO_CACHE,
    log_prints=True,
)
def chunk_document(engine, document_id: str, md_path: Path) -> int:
    """Read a markdown file, chunk it, and write chunks to Postgres."""
    text = md_path.read_text(encoding="utf-8")
    chunks = chunk_markdown(text, document_title="")

    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        for i, chunk in enumerate(chunks):
            cid = _chunk_id(document_id, i)
            session.merge(ChunkProcessingStatus(chunk_id=cid, processed_at=now))
            session.merge(
                Chunk(
                    chunk_id=cid,
                    document_id=document_id,
                    chunk_text=chunk.text,
                    chunk_strategy=CHUNK_STRATEGY,
                    section_type=chunk.section_type,
                    section_number=chunk.section_number or None,
                    section_title=chunk.section_title or None,
                    has_equations=chunk.has_equations,
                    has_tables=chunk.has_tables,
                    has_figures=chunk.has_figures,
                )
            )
        session.commit()

    print(f"[chunking] {document_id}: {len(chunks)} chunks")
    return len(chunks)


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------


@flow(log_prints=True)
def chunking_flow(
    extracted_dir: str = "data/extracted",
    database_url: str = "",
) -> None:
    """Chunk extracted markdown documents using paragraph_v1 strategy.

    1. Find documents extracted but not yet chunked with the current strategy
    2. Pre-process each document (strip references, artefacts, affiliations)
    3. Parse into sections by ## heading and section-number depth
    4. Split oversized sections at paragraph boundaries with 2-sentence overlap,
       preserving atomic blocks (equations, tables, figures) intact
    5. Write chunks with full structural metadata to Postgres
    """
    if not database_url:
        _user = os.environ["POSTGRES_USER"]
        _password = os.environ["POSTGRES_PASSWORD"]
        _host = os.environ.get("POSTGRES_HOST", "localhost")
        _port = os.environ.get("POSTGRES_PORT", "5432")
        _db = os.environ["POSTGRES_DB"]
        database_url = f"postgresql://{_user}:{_password}@{_host}:{_port}/{_db}"

    engine = get_db_engine(database_url)
    pending = get_unchunked_documents(engine, extracted_dir)

    if not pending:
        print("[chunking] Nothing to chunk.")
        return

    total = 0
    for document_id, md_path in pending:
        n = chunk_document(engine, document_id, md_path)
        total += n

    print(f"[chunking] Done. {len(pending)} documents → {total} chunks total.")


if __name__ == "__main__":
    chunking_flow(extracted_dir="data/extracted")
