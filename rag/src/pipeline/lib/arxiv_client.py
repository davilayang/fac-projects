# arXiv API search logic — pure Python, no orchestration dependency.

import re
from datetime import datetime, timezone

import arxiv


def clean_arxiv_id(entry_id: str) -> tuple[str, int]:
    """Extract clean arxiv ID and version from entry URL.

    e.g. "http://arxiv.org/abs/2602.03300v1" -> ("2602.03300", 1)
    """
    match = re.search(r"(\d{4}\.\d{4,5})(v(\d+))?", entry_id)
    if not match:
        raise ValueError(f"Cannot parse arxiv ID from: {entry_id}")
    arxiv_id = match.group(1)
    version = int(match.group(3)) if match.group(3) else 1
    return arxiv_id, version


def search_arxiv(
    query_string: str,
    date_from: str,
    date_to: str | None,
    max_results: int,
) -> list[dict]:
    """Search arXiv and return a list of paper metadata dicts."""
    client = arxiv.Client(page_size=100, delay_seconds=3, num_retries=5)
    search = arxiv.Search(
        query=query_string,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    date_from_dt = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
    papers: list[dict] = []

    for result in client.results(search):
        if result.published < date_from_dt:
            break

        if date_to:
            date_to_dt = datetime.fromisoformat(date_to).replace(
                tzinfo=timezone.utc
            )
            if result.published > date_to_dt:
                continue

        arxiv_id, version = clean_arxiv_id(result.entry_id)

        papers.append(
            {
                "arxiv_id": arxiv_id,
                "version": version,
                "title": result.title,
                "authors": [str(a) for a in result.authors],
                "abstract": result.summary,
                "categories": result.categories,
                "primary_category": result.primary_category,
                "published_at": result.published,
                "updated_at": result.updated,
                "pdf_url": result.pdf_url,
                "abstract_url": result.entry_id,
            }
        )

    return papers
