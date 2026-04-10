from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from arxiv_rag.services import (
    QueryFilters,
    rerank_retrieval_results,
    retrieve_embeddings,
)

router = APIRouter(prefix="/retrieve", tags=["retrieve"])


class ChunkResponse(BaseModel):
    arxiv_id: str
    title: str
    authors: list[str] | None
    categories: list[str] | None
    section: str | None
    score: float
    text: str


@router.get("", response_model=list[ChunkResponse])
def retrieve(
    query: str,
    k: int = 5,
    rerank: bool = True,
    author: str | None = None,
    category: str | None = None,
    published_after: datetime | None = None,
    published_before: datetime | None = None,
) -> list[ChunkResponse]:
    filters = QueryFilters(
        author=author,
        category=category,
        published_after=published_after,
        published_before=published_before,
    )
    passages = retrieve_embeddings(query, top_k=k * 4, filters=filters)
    results = (
        rerank_retrieval_results(query, passages, top_k=k) if rerank else passages[:k]
    )
    return [
        ChunkResponse(
            arxiv_id=r.arxiv_id,
            title=r.title,
            authors=r.authors,
            categories=r.categories,
            section=r.section,
            score=r.score,
            text=r.text,
        )
        for r in results
    ]
