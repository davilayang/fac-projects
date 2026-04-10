import logging
import time

from sentence_transformers import CrossEncoder

from arxiv_rag.config import get_settings
from arxiv_rag.services.retrieval import RetrievalResult

logger = logging.getLogger(__name__)
_settings = get_settings()
ranker = CrossEncoder(
    _settings.rerank_model,
    model_kwargs={"cache_dir": _settings.rerank_cache_dir},
)


def rerank_retrieval_results(
    query: str, passages: list[RetrievalResult], top_k: int
) -> list[RetrievalResult]:
    start = time.perf_counter()

    pairs = [(query, passage.text) for passage in passages]
    scores = ranker.predict(pairs)

    ranked = sorted(zip(scores, passages), key=lambda x: x[0], reverse=True)[:top_k]

    results = [
        RetrievalResult(
            arxiv_id=passage.arxiv_id,
            title=passage.title,
            authors=passage.authors,
            categories=passage.categories,
            primary_category=passage.primary_category,
            published=passage.published,
            section=passage.section,
            text=passage.text,
            score=round(float(score), 4),
        )
        for score, passage in ranked
    ]
    logger.info(
        "rerank complete",
        extra={
            "event": "rerank",
            "query": query,
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "chunks": [{"arxiv_id": r.arxiv_id, "score": float(r.score)} for r in results],
        },
    )
    return results
