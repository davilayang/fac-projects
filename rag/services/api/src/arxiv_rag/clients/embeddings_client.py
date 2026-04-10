from openai import OpenAI

from arxiv_rag.config import get_settings

settings = get_settings()

openai_client = OpenAI(api_key=settings.openai_key.get_secret_value())


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    response = openai_client.embeddings.create(
        input=texts,
        model=settings.embedding_model,
    )
    return [item.embedding for item in response.data]


def generate_embedding(text: str) -> list[float]:
    return generate_embeddings([text])[0]
