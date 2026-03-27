# eval.py — retrieval evaluation against known test questions
#
# For each question we know:
#   - the expected answer (what a correct response should contain)
#   - the expected source paper (which document_id must appear in top-k)
#
# This lets us measure retrieval quality BEFORE adding a generation step.
# Metric: recall@k — did the right paper appear in the top k results?
#
# Usage:
#   make eval

import os

from sqlalchemy import create_engine, text
from openai import OpenAI

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

TEST_QUERIES = [
    {
        "question": "In the Bielik-Q2-Sharp study, which 2-bit quantization method performed best on the Polish 11B model, and what accuracy did it achieve?",
        "expected_answer": "QuIP# E8P12, achieving 71.92%",
        "expected_paper": "2603.04162",
    },
    {
        "question": "What are the five modular components that the RAGPerf framework decomposes a RAG pipeline into?",
        "expected_answer": "embedding, indexing, retrieval, reranking, and generation",
        "expected_paper": "2603.10765",
    },
    {
        "question": "What key change did the second edition of the TREC RAG Track (2025) introduce compared to the 2024 track?",
        "expected_answer": "long, multi-sentence narrative queries to better reflect deep search tasks",
        "expected_paper": "2603.09891",
    },
    {
        "question": "According to the 'Thin Keys, Full Values' paper, what asymptotic dimensionality do queries and keys need for attention selection, and why is this different from values?",
        "expected_answer": "O(log N) dimensions, because selection is inherently lower-dimensional than value transfer",
        "expected_paper": "2603.04427",
    },
    {
        "question": "How does Speculative Speculative Decoding (SSD) differ from standard speculative decoding?",
        "expected_answer": "SSD parallelises speculation and verification steps; standard speculative decoding has sequential dependence",
        "expected_paper": "2603.03251",
    },
]

TOP_K = 5  # how many results to retrieve per question


# ---------------------------------------------------------------------------
# Helpers (same as query.py)
# ---------------------------------------------------------------------------


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


def retrieve(question: str, engine, top_k: int = TOP_K) -> list[dict]:
    vector = embed_question(question)
    vector_str = "[" + ",".join(str(x) for x in vector) + "]"

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
# Evaluation
# ---------------------------------------------------------------------------


def run_eval():
    engine = get_db_engine()

    passed = 0
    total = len(TEST_QUERIES)

    for i, test in enumerate(TEST_QUERIES, 1):
        question = test["question"]
        expected_paper = test["expected_paper"]
        expected_answer = test["expected_answer"]

        print(f"\n{'=' * 70}")
        print(f"[{i}/{total}] {question}")
        print(f"Expected paper : {expected_paper}")
        print(f"Expected answer: {expected_answer}")
        print("-" * 70)

        results = retrieve(question, engine, top_k=TOP_K)

        retrieved_papers = [r["document_id"] for r in results]
        found = any(expected_paper in doc_id for doc_id in retrieved_papers)

        for rank, chunk in enumerate(results, 1):
            hit = "✓" if expected_paper in chunk["document_id"] else " "
            print(
                f"  [{hit}] rank={rank} score={chunk['score']:.4f}"
                f" | {chunk['document_id']}"
                f" | {chunk['section_type']}"
                f" | {chunk['section_title']}"
            )

        if found:
            rank_found = next(
                r + 1
                for r, doc in enumerate(retrieved_papers)
                if expected_paper in doc
            )
            print(f"\n  PASS — correct paper found at rank {rank_found}")
            passed += 1
        else:
            print(f"\n  FAIL — correct paper not in top {TOP_K}")

    print(f"\n{'=' * 70}")
    print(f"RESULT: {passed}/{total} questions retrieved the correct paper in top-{TOP_K}")
    print(f"Recall@{TOP_K}: {passed / total:.0%}")
    print()


if __name__ == "__main__":
    run_eval()
