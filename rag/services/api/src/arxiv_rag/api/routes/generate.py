from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from arxiv_rag.api.rate_limit import check_rate_limit
from arxiv_rag.services import (
    QueryFilters,
    rerank_retrieval_results,
    retrieve_embeddings,
    stream_answer,
)

router = APIRouter(prefix="/generate", tags=["generate"])

_SYSTEM_PROMPT = (
    "You are a scientific research assistant specialising in machine learning"
    " and AI papers. Answer using only the provided documents."
    " Be precise and technical."
)


class GenerateRequest(BaseModel):
    query: str
    k: int = 5
    author: str | None = None
    category: str | None = None
    published_after: datetime | None = None
    published_before: datetime | None = None


@router.post("", dependencies=[Depends(check_rate_limit)])
def generate(request: GenerateRequest) -> StreamingResponse:
    filters = QueryFilters(
        author=request.author,
        category=request.category,
        published_after=request.published_after,
        published_before=request.published_before,
    )
    passages = retrieve_embeddings(request.query, top_k=request.k * 4, filters=filters)
    chunks = rerank_retrieval_results(request.query, passages, top_k=request.k)

    if not chunks:
        raise HTTPException(
            status_code=404, detail="No relevant documents found for this query."
        )

    return StreamingResponse(
        stream_answer(request.query, chunks, _SYSTEM_PROMPT),
        media_type="text/event-stream",
    )
