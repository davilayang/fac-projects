# PDF download logic — pure Python, no orchestration dependency.

from pathlib import Path

import httpx


def pdf_local_path(base_dir: str, arxiv_id: str, version: int) -> Path:
    """Compute YYMM-partitioned path for a paper PDF."""
    yymm = arxiv_id[:4]
    return Path(base_dir) / yymm / f"{arxiv_id}v{version}.pdf"


def download_pdf(pdf_url: str, target_path: Path, timeout: int = 60) -> Path:
    """Download a PDF from a URL to the target path.

    Creates parent directories as needed. Returns the path on success.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    response = httpx.get(pdf_url, follow_redirects=True, timeout=timeout)
    response.raise_for_status()
    target_path.write_bytes(response.content)
    return target_path
