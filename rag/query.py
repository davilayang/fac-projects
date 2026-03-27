# query.py — retrieval and generation against the corpus
#
# Usage:
#   make query                              # retrieve only, default question
#   make query Q="your question here"       # retrieve only, custom question
#   make query LLM=1                        # retrieve + generate answer
#   make query Q="your question" LLM=1      # retrieve + generate, custom question

import argparse
import os
import re
import time
import uuid

from openai import OpenAI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from db.models.query_logs import QueryChunkLog, QueryLog

DEFAULT_QUESTION = "How do large language models handle long contexts?"
GENERATION_MODEL = "gpt-4o-mini"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


def get_db_engine():
    url = (
        f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ.get('POSTGRES_HOST', 'localhost')}:{os.environ.get('POSTGRES_PORT', '5432')}"
        f"/{os.environ['POSTGRES_DB']}"
    )
    return create_engine(url)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def embed_question(question: str) -> list[float]:
    client = OpenAI()
    response = client.embeddings.create(
        model=os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"),
        input=question,
    )
    return response.data[0].embedding


def retrieve(question: str, top_k: int = 5, engine=None) -> tuple[list[dict], float]:
    """Embed the question and run vector search.

    Returns (chunks, retrieval_latency_ms).
    Accepts an optional engine to avoid re-creating a connection per call.
    """
    t0 = time.perf_counter()

    vector = embed_question(question)
    vector_str = "[" + ",".join(str(x) for x in vector) + "]"

    _engine = engine or get_db_engine()
    with _engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    c.document_id,
                    c.section_type,
                    c.section_title,
                    c.chunk_text,
                    1 - (e.vector <=> CAST(:vector AS vector)) AS score
                FROM ingestion.chunks c
                JOIN ingestion.embeddings e ON c.chunk_id = e.chunk_id
                ORDER BY e.vector <=> CAST(:vector AS vector)
                LIMIT :top_k
            """),
            {"vector": vector_str, "top_k": top_k},
        )
        chunks = [dict(r._mapping) for r in rows]

    latency_ms = (time.perf_counter() - t0) * 1000
    return chunks, latency_ms


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def _build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block for the prompt.

    Strips markdown heading syntax — useful for embedding but clutters answers.
    """
    parts = []
    for i, chunk in enumerate(chunks, 1):
        clean_text = re.sub(
            r"^#{1,4}\s+\*{0,2}[^\n]+\*{0,2}\n\n", "", chunk["chunk_text"]
        ).strip()
        parts.append(
            f"[{i}] Source: {chunk['document_id']} | {chunk['section_title']}\n{clean_text}"
        )
    return "\n\n".join(parts)


def _build_prompt(question: str, context: str) -> str:
    return f"""You are a research assistant answering questions about scientific papers.

Answer the question using ONLY the context provided below.
- Be specific and precise — include numbers, names, and technical terms where relevant.
- Cite each claim with the reference number in square brackets, e.g. [1] or [2].
- If the answer spans multiple sources, cite all of them.
- If the context does not contain enough information to answer, say so explicitly. Do not guess.

Context:
{context}

Question: {question}

Answer:"""


def generate(question: str, top_k: int = 5, engine=None) -> dict:
    """Retrieve relevant chunks and generate a cited answer.

    Returns:
        answer               — LLM-generated answer with inline citations
        sources              — chunks used as context
        retrieval_latency_ms — time spent on embed + vector search
        generation_latency_ms — time spent on LLM call
        total_latency_ms
    """
    chunks, retrieval_ms = retrieve(question, top_k=top_k, engine=engine)
    context = _build_context(chunks)
    prompt = _build_prompt(question, context)

    t0 = time.perf_counter()
    client = OpenAI()
    response = client.chat.completions.create(
        model=GENERATION_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    generation_ms = (time.perf_counter() - t0) * 1000

    return {
        "answer": response.choices[0].message.content,
        "sources": chunks,
        "retrieval_latency_ms": retrieval_ms,
        "generation_latency_ms": generation_ms,
        "total_latency_ms": retrieval_ms + generation_ms,
    }


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def log_query(
    engine,
    question: str,
    chunks: list[dict],
    retrieval_latency_ms: float,
    answer: str | None = None,
    generation_latency_ms: float | None = None,
    source: str = "cli",
) -> uuid.UUID:
    """Write a query and its retrieved chunks to logs.queries / logs.query_chunks.

    Returns the query_id so callers (e.g. eval.py) can link back to this log entry.
    """

    query_id = uuid.uuid4()
    total_ms = retrieval_latency_ms + (generation_latency_ms or 0.0)

    chunk_logs = [
        QueryChunkLog(
            query_id=query_id,
            rank=i + 1,
            document_id=chunk["document_id"],
            section_type=chunk.get("section_type"),
            section_title=chunk.get("section_title"),
            similarity_score=chunk["score"],
        )
        for i, chunk in enumerate(chunks)
    ]

    with Session(engine) as session:
        session.add(QueryLog(
            query_id=query_id,
            question=question,
            embedding_model=os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"),
            generation_model=GENERATION_MODEL if answer else None,
            top_k=len(chunks),
            generated_answer=answer,
            retrieval_latency_ms=retrieval_latency_ms,
            generation_latency_ms=generation_latency_ms,
            total_latency_ms=total_ms,
            source=source,
        ))
        session.add_all(chunk_logs)
        session.commit()

    return query_id


# ---------------------------------------------------------------------------
# CLI display helpers
# ---------------------------------------------------------------------------


def print_retrieval(question: str, top_k: int = 5) -> None:
    engine = get_db_engine()
    chunks, latency_ms = retrieve(question, top_k=top_k, engine=engine)

    print(f"\nQuestion: {question}\n")
    print("=" * 60)

    for i, chunk in enumerate(chunks, 1):
        print(
            f"\n[{i}] score={chunk['score']:.4f}"
            f" | {chunk['document_id']}"
            f" | {chunk['section_type']}"
            f" | {chunk['section_title']}"
        )
        print("-" * 40)
        print(chunk["chunk_text"][:400])

    print(f"\nRetrieval latency: {latency_ms:.0f}ms")

    log_query(engine, question, chunks, latency_ms, source="cli")


def print_answer(question: str, top_k: int = 5) -> None:
    engine = get_db_engine()
    result = generate(question, top_k=top_k, engine=engine)

    print(f"\nQuestion: {question}\n")
    print("=" * 60)
    print("\nAnswer:")
    print("-" * 40)
    print(result["answer"])
    print("\nSources:")
    print("-" * 40)
    for i, chunk in enumerate(result["sources"], 1):
        print(
            f"  [{i}] {chunk['document_id']}"
            f" | score={chunk['score']:.4f}"
            f" | {chunk['section_title']}"
        )
    print(
        f"\nLatency: retrieval={result['retrieval_latency_ms']:.0f}ms"
        f"  generation={result['generation_latency_ms']:.0f}ms"
        f"  total={result['total_latency_ms']:.0f}ms"
    )

    log_query(
        engine,
        question,
        result["sources"],
        result["retrieval_latency_ms"],
        answer=result["answer"],
        generation_latency_ms=result["generation_latency_ms"],
        source="cli",
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", "-q", default=DEFAULT_QUESTION)
    parser.add_argument("--llm", action="store_true", help="Generate an answer using the LLM")
    parser.add_argument("--top-k", "-k", type=int, default=5)
    args = parser.parse_args()

    if args.llm:
        print_answer(args.question, top_k=args.top_k)
    else:
        print_retrieval(args.question, top_k=args.top_k)
