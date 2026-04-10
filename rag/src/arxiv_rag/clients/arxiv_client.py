from dataclasses import dataclass
from datetime import datetime

import arxiv

client = arxiv.Client()


@dataclass
class ArxivMetadata:
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published: datetime
    updated: datetime
    categories: list[str]
    primary_category: str
    pdf_url: str | None


def _to_metadata(document: arxiv.Result) -> ArxivMetadata:
    return ArxivMetadata(
        arxiv_id=document.entry_id.split("/abs/")[-1],
        title=document.title,
        authors=[author.name for author in document.authors],
        abstract=document.summary,
        published=document.published,
        updated=document.updated,
        categories=document.categories,
        primary_category=document.primary_category,
        pdf_url=document.pdf_url,
    )


def get_document_metadata(document_id: str) -> ArxivMetadata:
    """Fetch metadata for a given arXiv document id (e.g. '2602.03300v1')."""
    document = next(client.results(arxiv.Search(id_list=[document_id])))
    return _to_metadata(document)


def get_batch_metadata(document_ids: list[str]) -> list[ArxivMetadata]:
    """Fetch metadata for multiple arXiv documents in a single API call."""
    results = client.results(arxiv.Search(id_list=document_ids))
    return [_to_metadata(doc) for doc in results]
