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

from openai import OpenAI
from sqlalchemy import create_engine, text

DEFAULT_QUESTION = "How do large language models handle long contexts?"

# Generation model — separate from the embedding model
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


def retrieve(question: str, top_k: int = 5) -> list[dict]:
    vector = embed_question(question)
    vector_str = "[" + ",".join(str(x) for x in vector) + "]"

    engine = get_db_engine()
    with engine.connect() as conn:
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
        return [dict(r._mapping) for r in rows]


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def _build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block for the prompt.

    Each chunk gets a reference number [1], [2], ... so the LLM can cite them
    by number in its answer. We strip markdown heading syntax from the chunk
    text — it was useful for embedding but clutters the answer.
    """
    parts = []
    for i, chunk in enumerate(chunks, 1):
        # Strip leading markdown heading (## **Title**\n\n) from chunk text
        clean_text = re.sub(r"^#{1,4}\s+\*{0,2}[^\n]+\*{0,2}\n\n", "", chunk["chunk_text"]).strip()
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


def generate(question: str, top_k: int = 5) -> dict:
    """Retrieve relevant chunks and generate a cited answer.

    Returns a dict with:
      answer   — the LLM-generated answer with inline citations
      sources  — list of source chunks used as context
    """
    chunks = retrieve(question, top_k=top_k)
    context = _build_context(chunks)
    prompt = _build_prompt(question, context)

    client = OpenAI()
    response = client.chat.completions.create(
        model=GENERATION_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,  # deterministic — we want factual answers, not creative ones
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": chunks,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def print_retrieval(question: str, top_k: int = 5) -> None:
    print(f"\nQuestion: {question}\n")
    print("=" * 60)

    results = retrieve(question, top_k=top_k)
    for i, chunk in enumerate(results, 1):
        print(
            f"\n[{i}] score={chunk['score']:.4f}"
            f" | {chunk['document_id']}"
            f" | {chunk['section_type']}"
            f" | {chunk['section_title']}"
        )
        print("-" * 40)
        print(chunk["chunk_text"][:400])
    print()


def print_answer(question: str, top_k: int = 5) -> None:
    print(f"\nQuestion: {question}\n")
    print("=" * 60)

    result = generate(question, top_k=top_k)

    print("\nAnswer:")
    print("-" * 40)
    print(result["answer"])

    print("\nSources:")
    print("-" * 40)
    for i, chunk in enumerate(result["sources"], 1):
        print(f"  [{i}] {chunk['document_id']} | score={chunk['score']:.4f} | {chunk['section_title']}")
    print()


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
