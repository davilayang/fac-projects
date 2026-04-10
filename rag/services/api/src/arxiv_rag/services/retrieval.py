import logging
import time

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Float, func

from arxiv_rag.clients import generate_embedding
from arxiv_rag.database import ArxivChunk, get_session

logger = logging.getLogger(__name__)


@dataclass
class QueryFilters:
    author: str | None = None
    category: str | None = None
    published_after: datetime | None = None
    published_before: datetime | None = None


def build_query_filters(filters: QueryFilters | None) -> list:
    if filters is None:
        return []

    def array_filter(column, value):
        return func.array_to_string(column, ",").ilike(f"%{value}%")

    results = []
    if filters.author:
        results.append(array_filter(ArxivChunk.authors, filters.author))
    if filters.category:
        results.append(array_filter(ArxivChunk.categories, filters.category))
    if filters.published_after:
        results.append(ArxivChunk.published >= filters.published_after)
    if filters.published_before:
        results.append(ArxivChunk.published <= filters.published_before)

    return results


@dataclass
class RetrievalResult:
    arxiv_id: str
    title: str
    authors: list[str] | None
    categories: list[str] | None
    primary_category: str | None
    published: datetime | None
    section: str | None
    text: str
    score: float


def retrieve_embeddings(
    query: str,
    top_k: int = 5,
    filters: QueryFilters | None = None,
) -> list[RetrievalResult]:
    start = time.perf_counter()
    query_embedding = generate_embedding(query)
    query_filters = build_query_filters(filters)
    distance = ArxivChunk.embedding.op("<=>", return_type=Float())(query_embedding)

    with get_session() as session:
        rows = (
            session.query(ArxivChunk, distance.label("score"))
            .filter(*query_filters)
            .order_by(distance)
            .limit(top_k)
            .all()
        )

    results = [
        RetrievalResult(
            arxiv_id=chunk.arxiv_id,
            title=chunk.title,
            authors=chunk.authors,
            categories=chunk.categories,
            primary_category=chunk.primary_category,
            published=chunk.published,
            section=chunk.section,
            text=chunk.text,
            score=round(1 - score, 4),
        )
        for chunk, score in rows
    ]
    logger.info(
        "retrieval complete",
        extra={
            "event": "retrieval",
            "query": query,
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "chunks": [
                {"arxiv_id": r.arxiv_id, "score": float(r.score)} for r in results
            ],
        },
    )
    return results
