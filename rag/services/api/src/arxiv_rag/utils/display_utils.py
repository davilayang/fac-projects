import re
import textwrap

from arxiv_rag.services.retrieval import RetrievalResult

_CITATION_SEP = "-" * 60


def _format_authors(authors: list[str] | None) -> str:
    if not authors:
        return "Unknown"
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return f"{authors[0]} & {authors[1]}"
    return f"{authors[0]} et al."


def _strip_markdown(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text).strip()


def print_citations(
    chunks: list[RetrievalResult], numbers: list[int] | None = None
) -> None:
    numbers = numbers or list(range(1, len(chunks) + 1))
    print(f"\n{_CITATION_SEP}")
    print("References")
    print(_CITATION_SEP)
    for n, chunk in zip(numbers, chunks):
        authors = _format_authors(chunk.authors)
        year = chunk.published.strftime("%Y") if chunk.published else "n.d."
        section = _strip_markdown(chunk.section)
        print(f"[{n}] {authors} ({year}). {chunk.title}.")
        print(f"     arXiv:{chunk.arxiv_id} — §{section}")
    print(_CITATION_SEP)


_COL_WIDTHS = {
    "score": 6,
    "arxiv_id": 12,
    "title": 35,
    "authors": 25,
    "categories": 20,
    "section": 30,
    "text": 55,
}
_SEP = "-" * (sum(_COL_WIDTHS.values()) + len(_COL_WIDTHS) * 3 + 1)


def _cell(value: str | None, width: int) -> str:
    value = value or ""
    return textwrap.shorten(value, width=width, placeholder="…").ljust(width)


def print_results(results: list[RetrievalResult]) -> None:
    header = (
        "| "
        + " | ".join(col.upper().ljust(width) for col, width in _COL_WIDTHS.items())
        + " |"
    )
    print(_SEP)
    print(header)
    print(_SEP)
    for r in sorted(results, key=lambda r: r.score, reverse=True):
        row = (
            "| "
            + " | ".join(
                [
                    f"{r.score:.4f}".ljust(_COL_WIDTHS["score"]),
                    _cell(r.arxiv_id, _COL_WIDTHS["arxiv_id"]),
                    _cell(r.title, _COL_WIDTHS["title"]),
                    _cell(", ".join(r.authors or []), _COL_WIDTHS["authors"]),
                    _cell(", ".join(r.categories or []), _COL_WIDTHS["categories"]),
                    _cell(r.section, _COL_WIDTHS["section"]),
                    _cell(r.text, _COL_WIDTHS["text"]),
                ]
            )
            + " |"
        )
        print(row)
    print(_SEP)
    print(f"{len(results)} result(s)")
