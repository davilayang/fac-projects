# Events Audio Agent (EVA)

A LiveKit-powered voice AI assistant with a Next.js web interface.

## Services

| Service | Description |
|---|---|
| `voice-agent` | Python LiveKit agent (STT → LLM → TTS) with Pinecone MCP tool |
| `web-ui` | Next.js frontend for interacting with the agent |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose v2
- A [LiveKit Cloud](https://cloud.livekit.io) project

## Local Setup

### 1. Configure environment variables

Copy `default.env` as `.env` in the this repo and add your credentials:

```env
# LiveKit API
LIVEKIT_URL=wss://<project-subdomain>.livekit.cloud
LIVEKIT_API_KEY=<your_api_key>
LIVEKIT_API_SECRET=<your_api_secret>

# Agent 
AGENT_NAME=eva

# Open AI API
OPENAI_API_KEY=...

# Pinecone (already set)
PINECONE_API_KEY=...
```

### 2. Start all services

```bash
docker compose up --build
```

The web UI will be available at http://localhost:3000.

To run in the background:

```bash
docker compose up --build -d
```

### 3. Stop services

```bash
docker compose down
```

## Development (without Docker)

**voice-agent** — requires [uv](https://docs.astral.sh/uv/)

```bash
cd voice-agent

uv run python agent.py dev
```

**web-ui** — requires [pnpm](https://pnpm.io/)

```bash
cd web-ui

pnpm install
pnpm dev
```
