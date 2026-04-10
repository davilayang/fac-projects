import json
import logging
import time
from collections.abc import Generator

from anthropic import Anthropic

from arxiv_rag.config import get_settings
from arxiv_rag.services.retrieval import RetrievalResult

logger = logging.getLogger(__name__)
settings = get_settings()

anthropic_client = Anthropic(api_key=settings.anthropic_api_key.get_secret_value())


def _build_content(question: str, chunks: list[RetrievalResult]) -> list:
    content = []
    for chunk in chunks:
        authors = ", ".join(chunk.authors) if chunk.authors else "Unknown"
        published = chunk.published.strftime("%Y-%m") if chunk.published else "n/a"
        content.append(
            {
                "type": "document",
                "source": {
                    "type": "text",
                    "media_type": "text/plain",
                    "data": chunk.text,
                },
                "title": chunk.title,
                "context": (f"arXiv:{chunk.arxiv_id} | {authors} ({published}) | {chunk.section}"),
                "citations": {"enabled": True},
            }
        )
    content.append({"type": "text", "text": question})
    return content


def generate_answer(question: str, chunks: list[RetrievalResult], system_prompt: str) -> set[int]:
    """Stream the answer to stdout. Return 0-indexed document indices that were cited."""
    content = _build_content(question, chunks)
    cited_indices: set[int] = set()
    current_block_citations: list = []
    start = time.perf_counter()

    with anthropic_client.messages.stream(
        model=settings.llm_model,
        max_tokens=settings.max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": content}],
    ) as stream:
        for event in stream:
            if event.type == "content_block_delta":
                delta = event.delta
                if delta.type == "text_delta":
                    print(delta.text, end="", flush=True)
                elif delta.type == "citations_delta":
                    current_block_citations.append(delta.citation)
            elif event.type == "content_block_stop":
                if current_block_citations:
                    block_doc_indices = sorted({c.document_index for c in current_block_citations})
                    print(
                        "".join(f"[{i + 1}]" for i in block_doc_indices),
                        end="",
                        flush=True,
                    )
                    cited_indices.update(block_doc_indices)
                    current_block_citations = []

        final_message = stream.get_final_message()

    print()
    _log_generation(question, start, final_message.usage, sorted(cited_indices))
    return cited_indices



def stream_answer(
    question: str, chunks: list[RetrievalResult], system_prompt: str
) -> Generator[str, None, None]:
    """Yield SSE-formatted events for the API streaming endpoint."""
    content = _build_content(question, chunks)
    cited_indices: set[int] = set()
    current_block_citations: list = []
    start = time.perf_counter()

    with anthropic_client.messages.stream(
        model=settings.llm_model,
        max_tokens=settings.max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": content}],
    ) as stream:
        for event in stream:
            if event.type == "content_block_delta":
                delta = event.delta
                if delta.type == "text_delta":
                    yield f"data: {json.dumps({'type': 'text', 'text': delta.text})}\n\n"
                elif delta.type == "citations_delta":
                    current_block_citations.append(delta.citation)
            elif event.type == "content_block_stop":
                if current_block_citations:
                    block_doc_indices = sorted({c.document_index for c in current_block_citations})
                    markers = "".join(f"[{i + 1}]" for i in block_doc_indices)
                    yield f"data: {json.dumps({'type': 'citation', 'markers': markers})}\n\n"
                    cited_indices.update(block_doc_indices)
                    current_block_citations = []

        final_message = stream.get_final_message()

    _log_generation(question, start, final_message.usage, sorted(cited_indices))

    sources = [
        {
            "index": i + 1,
            "arxiv_id": chunks[i].arxiv_id,
            "title": chunks[i].title,
            "authors": chunks[i].authors,
            "published": pub.strftime("%Y-%m") if (pub := chunks[i].published) else None,
            "section": chunks[i].section,
        }
        for i in sorted(cited_indices)
    ]
    yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
    yield "data: [DONE]\n\n"


def _log_generation(question: str, start: float, usage, cited: list[int]) -> None:
    logger.info(
        "generation complete",
        extra={
            "event": "generation",
            "query": question,
            "model": settings.llm_model,
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "tokens_input": usage.input_tokens,
            "tokens_output": usage.output_tokens,
            "cited": cited,
        },
    )
