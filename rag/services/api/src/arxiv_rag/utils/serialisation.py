from arxiv_rag.services.retrieval import RetrievalResult


def chunks_to_xml(chunks: list[RetrievalResult]) -> str:
    doc_parts = []
    for i, chunk in enumerate(chunks):
        authors = ", ".join(chunk.authors) if chunk.authors else "Unknown"
        source = f"{chunk.arxiv_id} | {chunk.title} | {authors} | {chunk.section}"
        doc_parts.append(
            f'<document index="{i + 1}">\n'
            f"  <source>{source}</source>\n"
            f"  <document_content>\n{chunk.text}\n  </document_content>\n"
            f"</document>"
        )
    return "<documents>\n" + "\n".join(doc_parts) + "\n</documents>"
