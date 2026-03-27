# query.py — test retrieval against the corpus
#
# Usage:
#   make query                              # runs the default question
#   make query Q="your question here"       # runs a custom question

import argparse
import os

from openai import OpenAI
from sqlalchemy import create_engine, text

DEFAULT_QUESTION = "How do large language models handle long contexts?"


def get_db_engine():
    url = (
        f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ.get('POSTGRES_HOST', 'localhost')}:{os.environ.get('POSTGRES_PORT', '5432')}"
        f"/{os.environ['POSTGRES_DB']}"
    )
    return create_engine(url)


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", "-q", default=DEFAULT_QUESTION)
    args = parser.parse_args()

    question = args.question
    print(f"\nQuestion: {question}\n")
    print("=" * 60)

    results = retrieve(question, top_k=5)
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
