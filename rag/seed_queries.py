# seed_queries.py — run a batch of questions to populate logs for Grafana
#
# Runs a mix of retrieval-only and retrieval+generation queries so
# logs.queries and logs.query_chunks fill up with realistic data.
#
# Usage:
#   make seed

import time

from query import generate, get_db_engine, log_query, retrieve

QUESTIONS = [
    # Retrieval + generation
    {"q": "What techniques reduce hallucination in large language models?", "llm": True},
    {"q": "How does speculative decoding improve inference speed?", "llm": True},
    {"q": "What is the KV cache and why does it matter for LLM efficiency?", "llm": True},
    {"q": "How do RAG systems handle multi-hop questions that require reasoning across documents?", "llm": True},
    {"q": "What are the main challenges in evaluating RAG pipelines?", "llm": True},
    # Retrieval only
    {"q": "What embedding models are used for scientific document retrieval?", "llm": False},
    {"q": "How does HNSW indexing work for approximate nearest neighbour search?", "llm": False},
    {"q": "What is the difference between sparse and dense retrieval?", "llm": False},
    {"q": "How do transformer attention mechanisms scale with sequence length?", "llm": False},
    {"q": "What quantization methods are used to compress large language models?", "llm": False},
    {"q": "How does re-ranking improve retrieval quality in RAG systems?", "llm": False},
    {"q": "What is positional encoding and how has it evolved in recent models?", "llm": False},
    # More generation
    {"q": "What evaluation metrics are commonly used for RAG systems beyond recall?", "llm": True},
    {"q": "How does the TREC RAG benchmark measure retrieval-augmented generation quality?", "llm": True},
    {"q": "What are the trade-offs between using a large context window vs retrieval?", "llm": True},
]


def main():
    engine = get_db_engine()
    total = len(QUESTIONS)

    print(f"Running {total} queries...\n")

    for i, item in enumerate(QUESTIONS, 1):
        question = item["q"]
        use_llm = item["llm"]

        print(f"[{i}/{total}] {'LLM' if use_llm else 'RTR'} — {question[:70]}")

        if use_llm:
            result = generate(question, top_k=5, engine=engine)
            log_query(
                engine,
                question,
                result["sources"],
                result["retrieval_latency_ms"],
                answer=result["answer"],
                generation_latency_ms=result["generation_latency_ms"],
                source="cli",
            )
            print(f"        retrieval={result['retrieval_latency_ms']:.0f}ms  "
                  f"generation={result['generation_latency_ms']:.0f}ms  "
                  f"total={result['total_latency_ms']:.0f}ms")
        else:
            chunks, latency_ms = retrieve(question, top_k=5, engine=engine)
            log_query(engine, question, chunks, latency_ms, source="cli")
            print(f"        retrieval={latency_ms:.0f}ms")

        # Small pause to spread timestamps in Grafana time series
        time.sleep(1)

    print(f"\nDone — {total} queries logged to logs.queries")


if __name__ == "__main__":
    main()
