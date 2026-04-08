# PDF text/metadata extraction — pure Python, no orchestration dependency.

from pathlib import Path

import pymupdf
import pymupdf4llm


def extract_to_markdown(pdf_path: Path, output_dir: str) -> Path:
    """Extract a PDF to markdown using pymupdf4llm.

    Preserves YYMM directory structure from the source path.
    """
    out_dir = Path(output_dir)
    yymm = pdf_path.parent.name
    out_subdir = out_dir / yymm if yymm != out_dir.name else out_dir
    out_subdir.mkdir(parents=True, exist_ok=True)
    output_path = out_subdir / f"{pdf_path.stem}.md"

    md_text = pymupdf4llm.to_markdown(str(pdf_path))
    output_path.write_text(md_text, encoding="utf-8")
    return output_path


def extract_metadata(pdf_path: Path) -> dict:
    """Extract metadata from a PDF using pymupdf."""
    with pymupdf.open(pdf_path) as doc:
        meta = doc.metadata
        page_count = doc.page_count

    raw_authors = meta.get("author", "")
    if raw_authors:
        sep = ";" if ";" in raw_authors else ","
        authors = [a.strip() for a in raw_authors.split(sep) if a.strip()]
    else:
        authors = []

    return {
        "document_id": pdf_path.stem,
        "title": meta.get("title", ""),
        "authors": authors,
        "page_count": page_count,
    }
