"""OpenAI embeddings client. Pure Python — no Dagster dependency."""

from openai import OpenAI


def get_openai_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def generate_embeddings(
    client: OpenAI,
    texts: list[str],
    model: str = "text-embedding-3-small",
) -> list[list[float]]:
    """Call OpenAI embeddings API. Returns list of float vectors."""
    response = client.embeddings.create(input=texts, model=model)
    return [item.embedding for item in response.data]
