# eval.py — structured retrieval evaluation with experiment tracking
#
# Runs all test queries against the current system, records results to the
# eval schema, and links each query back to logs.queries for latency data.
#
# Usage:
#   make eval           # retrieval scores only (recall@k, precision@k, MRR)
#   make eval LLM=1     # also generate and store LLM answers

import argparse
import os
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from db.models.embeddings import EMBEDDING_DIM
from db.models.eval_tracking import EvalQueryResult, EvalRetrievedChunk, EvalRun
from flows.chunking import CHUNK_STRATEGY, MAX_TOKENS, MIN_TOKENS, OVERLAP_SENTENCES
from flows.embedding import DEFAULT_MODEL, DEFAULT_PROVIDER
from query import GENERATION_MODEL, generate, get_db_engine, log_query, retrieve

# ---------------------------------------------------------------------------
# Test cases — ground truth for measuring retrieval and generation quality
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

TOP_K = 5


# ---------------------------------------------------------------------------
# System config snapshot
# ---------------------------------------------------------------------------


def _get_corpus_counts(engine) -> tuple[int, int]:
    """Return (doc_count, chunk_count) from the current DB state."""
    with engine.connect() as conn:
        doc_count = conn.execute(
            text("SELECT COUNT(*) FROM ingestion.document_processing_status")
        ).scalar()
        chunk_count = conn.execute(
            text("SELECT COUNT(*) FROM ingestion.chunks")
        ).scalar()
    return int(doc_count), int(chunk_count)


def _build_run_config(engine, top_k: int, with_llm: bool) -> dict:
    """Snapshot current system configuration for the eval run record."""
    doc_count, chunk_count = _get_corpus_counts(engine)
    return {
        "extraction_method": "pymupdf4llm",
        "chunking_strategy": CHUNK_STRATEGY,
        "chunk_max_tokens": MAX_TOKENS,
        "chunk_min_tokens": MIN_TOKENS,
        "overlap_sentences": OVERLAP_SENTENCES,
        "embedding_model": os.environ.get("EMBEDDING_MODEL", DEFAULT_MODEL),
        "embedding_dim": EMBEDDING_DIM,
        "embedding_provider": os.environ.get("EMBEDDING_PROVIDER", DEFAULT_PROVIDER),
        "top_k": top_k,
        "generation_model": GENERATION_MODEL if with_llm else None,
        "corpus_doc_count": doc_count,
        "corpus_chunk_count": chunk_count,
    }


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def run_eval(with_llm: bool = False, notes: str | None = None) -> None:
    engine = get_db_engine()
    total = len(TEST_QUERIES)

    # --- Create eval run record ---
    config = _build_run_config(engine, top_k=TOP_K, with_llm=with_llm)
    run_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(EvalRun(run_id=run_id, notes=notes, **config))
        session.commit()

    print(f"\nEval run: {run_id}")
    print(f"Config: chunking={config['chunking_strategy']}"
          f"  embedding={config['embedding_model']}"
          f"  top_k={TOP_K}"
          f"  llm={config['generation_model'] or 'none'}")

    passed = 0
    total_precision = 0.0
    reciprocal_ranks = []

    for i, test in enumerate(TEST_QUERIES, 1):
        question = test["question"]
        expected_paper = test["expected_paper"]
        expected_answer = test["expected_answer"]

        print(f"\n{'=' * 70}")
        print(f"[{i}/{total}] {question}")
        print(f"Expected paper : {expected_paper}")
        print(f"Expected answer: {expected_answer}")
        print("-" * 70)

        # --- Retrieve (and optionally generate) ---
        if with_llm:
            result = generate(question, top_k=TOP_K, engine=engine)
            chunks = result["sources"]
            retrieval_ms = result["retrieval_latency_ms"]
            generation_ms = result["generation_latency_ms"]
            answer = result["answer"]
        else:
            chunks, retrieval_ms = retrieve(question, top_k=TOP_K, engine=engine)
            generation_ms = None
            answer = None

        # --- Log to logs.queries (shared operational log) ---
        query_id = log_query(
            engine,
            question,
            chunks,
            retrieval_ms,
            answer=answer,
            generation_latency_ms=generation_ms,
            source="eval",
        )

        # --- Compute retrieval metrics ---
        retrieved_papers = [c["document_id"] for c in chunks]
        recall_hit = any(expected_paper in doc_id for doc_id in retrieved_papers)

        expected_paper_rank = None
        expected_paper_score = None
        for rank, chunk in enumerate(chunks, 1):
            if expected_paper in chunk["document_id"]:
                if expected_paper_rank is None:
                    expected_paper_rank = rank
                    expected_paper_score = chunk["score"]

        precision = sum(1 for doc in retrieved_papers if expected_paper in doc) / TOP_K
        total_precision += precision

        # --- Print results ---
        for rank, chunk in enumerate(chunks, 1):
            hit = "✓" if expected_paper in chunk["document_id"] else " "
            print(
                f"  [{hit}] rank={rank} score={chunk['score']:.4f}"
                f" | {chunk['document_id']}"
                f" | {chunk['section_type']}"
                f" | {chunk['section_title']}"
            )

        if recall_hit:
            print(f"\n  PASS — correct paper at rank {expected_paper_rank}"
                  f"  precision@{TOP_K}={precision:.2f}"
                  f"  retrieval={retrieval_ms:.0f}ms")
            passed += 1
            reciprocal_ranks.append(1.0 / expected_paper_rank)
        else:
            print(f"\n  FAIL — correct paper not in top {TOP_K}"
                  f"  precision@{TOP_K}=0.00"
                  f"  retrieval={retrieval_ms:.0f}ms")
            reciprocal_ranks.append(0.0)

        if with_llm and answer:
            print(f"\n  Answer: {answer}")

        # --- Write to eval schema ---
        result_id = uuid.uuid4()
        eval_chunks = [
            EvalRetrievedChunk(
                result_id=result_id,
                rank=rank,
                document_id=chunk["document_id"],
                section_type=chunk.get("section_type"),
                section_title=chunk.get("section_title"),
                similarity_score=chunk["score"],
                is_expected=expected_paper in chunk["document_id"],
            )
            for rank, chunk in enumerate(chunks, 1)
        ]
        with Session(engine) as session:
            session.add(EvalQueryResult(
                result_id=result_id,
                run_id=run_id,
                query_id=query_id,
                question=question,
                expected_paper=expected_paper,
                expected_answer=expected_answer,
                generated_answer=answer,
                recall_hit=recall_hit,
                expected_paper_rank=expected_paper_rank,
                expected_paper_score=expected_paper_score,
            ))
            session.add_all(eval_chunks)
            session.commit()

    # --- Summary ---
    recall = passed / total
    mean_precision = total_precision / total
    mrr = sum(reciprocal_ranks) / total
    f1 = (2 * mean_precision * recall / (mean_precision + recall)) if (mean_precision + recall) else 0.0

    print(f"\n{'=' * 70}")
    print(f"Run ID: {run_id}")
    print(f"  Recall@{TOP_K}:    {recall:.0%}  ({passed}/{total})")
    print(f"  Precision@{TOP_K}: {mean_precision:.2f}")
    print(f"  F1:            {f1:.2f}")
    print(f"  MRR:           {mrr:.2f}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", action="store_true", help="Also generate LLM answers")
    parser.add_argument("--notes", default=None, help="Optional notes for this run")
    args = parser.parse_args()
    run_eval(with_llm=args.llm, notes=args.notes)
