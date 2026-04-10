import argparse
import logging
from datetime import datetime

from arxiv_rag.config import get_settings
from arxiv_rag.log import configure_logging, new_trace_id


def main():
    settings = get_settings()
    configure_logging(settings.db_url, level=logging.getLevelName(settings.log_level))
    new_trace_id()
    parser = argparse.ArgumentParser(description="ArXiv RAG")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Build command
    subparsers.add_parser("build-embeddings")

    # Retrieve command
    def add_search_args(parser):
        parser.add_argument("--query", type=str)
        parser.add_argument("--k", type=int, default=5)
        parser.add_argument("--author", type=str, default=None)
        parser.add_argument("--category", type=str, default=None)
        parser.add_argument("--published-after", type=str, default=None)
        parser.add_argument("--published-before", type=str, default=None)

    retrieve_parser = subparsers.add_parser("retrieve")
    retrieve_parser.add_argument("--no-rerank", action="store_true", default=False)
    add_search_args(retrieve_parser)

    # Generate command
    generate_parser = subparsers.add_parser("generate")
    add_search_args(generate_parser)

    args = parser.parse_args()

    match args.command:
        case "build-embeddings":
            from arxiv_rag.services import build_embeddings

            build_embeddings()
        case "retrieve":
            from arxiv_rag.services import (
                QueryFilters,
                rerank_retrieval_results,
                retrieve_embeddings,
            )
            from arxiv_rag.utils import print_results

            if not args.no_rerank:
                passages = retrieve_embeddings(
                    args.query,
                    top_k=args.k * 4,
                    filters=QueryFilters(
                        author=args.author,
                        category=args.category,
                        published_after=datetime.fromisoformat(args.published_after)
                        if args.published_after
                        else None,
                        published_before=datetime.fromisoformat(args.published_before)
                        if args.published_before
                        else None,
                    ),
                )
                print_results(rerank_retrieval_results(args.query, passages, top_k=args.k))
            else:
                print_results(retrieve_embeddings(args.query, top_k=args.k))
            return
        case "generate":
            from arxiv_rag.services import (
                QueryFilters,
                generate_answer,
                rerank_retrieval_results,
                retrieve_embeddings,
            )
            from arxiv_rag.utils import print_citations

            passages = retrieve_embeddings(
                args.query,
                top_k=args.k * 4,
                filters=QueryFilters(
                    author=args.author,
                    category=args.category,
                    published_after=datetime.fromisoformat(args.published_after)
                    if args.published_after
                    else None,
                    published_before=datetime.fromisoformat(args.published_before)
                    if args.published_before
                    else None,
                ),
            )
            reranked_chunks = rerank_retrieval_results(args.query, passages, top_k=args.k)

            system_prompt = (
                "You are a scientific research assistant specialising in machine learning"
                " and AI papers. Answer using only the provided documents."
                " Be precise and technical."
            )

            cited_answer = generate_answer(args.query, reranked_chunks, system_prompt)
            if cited_answer:
                sorted_citations = sorted(cited_answer)
                print_citations(
                    [reranked_chunks[i] for i in sorted_citations],
                    numbers=[i + 1 for i in sorted_citations],
                )
            return
        case _:
            raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
