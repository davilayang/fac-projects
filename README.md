# FAC Projects

AI & LiveKit initiatives for Apolitical.

- [Architecture Diagram](https://app.diagrams.net/#G1b9EFaT6Z02uhBsf_0o1GsCqXoUHfzkIQ)
- [Ideas & Roadmap](./IDEAS.md)

## Projects

| Project | Description | Stack |
|---------|-------------|-------|
| [`eva`](./eva/) | **Events Voice Agent** — LiveKit-powered voice AI for interactive event replay | Python (uv), LiveKit, Pinecone, OpenAI |
| [`rag`](./rag/) | **RAG Ingestion Pipeline** — arXiv document ingestion, chunking, and embedding | Python (uv), Prefect, PostgreSQL, pymupdf4llm |

## Getting Started

Each project is self-contained. To work on a project:

```bash
cd <project>       # e.g. cd eva
```

Then follow the project's own README for setup and running instructions.

### Common Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python projects)
- [pnpm](https://pnpm.io/) (Node.js projects)
- [Docker](https://docs.docker.com/get-docker/) with Compose v2
