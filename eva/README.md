# Events Audio Agent (EVA)

A LiveKit-powered voice AI assistant for interactive video.

## Services

| Service | Description |
|---|---|
| `voice-agent` | Python LiveKit agent (STT → LLM → TTS) with vector search and video control tools |
| `embeddings` | Notebooks and scripts for transcribing videos and indexing them into Pinecone |

## Architecture

```
User ──voice──► LiveKit Room ──► EVA Agent
                                    │
                    ┌───────────────┼──────────────────┐
                    │               │                   │
              Deepgram STT    GPT-4.1-mini LLM    Inworld TTS
                                    │
                              ┌─────┴──────┐
                         Pinecone Search  Video RPC
                      (OpenAI embeddings)  (play/pause/seek/
                                           bookmark/note)
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose v2
- A [LiveKit Cloud](https://cloud.livekit.io) project
- OpenAI API key (embeddings + LLM)
- Deepgram API key (STT)
- Pinecone index with video transcript embeddings

## Environment Variables

Copy `default.env` as `.env` and fill in your credentials:

```env
# LiveKit
LIVEKIT_URL=wss://<project-subdomain>.livekit.cloud
LIVEKIT_API_KEY=<your_api_key>
LIVEKIT_API_SECRET=<your_api_secret>

# Agent
AGENT_NAME=eva

# OpenAI (LLM + embeddings)
OPENAI_API_KEY=...

# Deepgram (STT)
DEEPGRAM_API_KEY=...

# Pinecone (vector search)
PINECONE_API_TOKEN=...
PINECONE_INDEX_HOST=...
```

## Local Setup

### 1. Configure environment variables

```bash
cp .env.example .env  # fill in your values
```

See [Environment Variables](#environment-variables) above.

### 2. Tilt (recommended for local dev)

[Tilt](https://tilt.dev) runs all services, streams logs in a single UI, and live-updates containers on file changes without full rebuilds.

```bash
# Install Tilt (macOS)
brew install tilt

# Start everything — opens the Tilt UI at http://localhost:10350
./tilt-up.sh

# Stop everything (tears down containers and releases port 10350)
./tilt-down.sh
```

Services available at:
- UI: http://localhost:8080
- Auth server: http://localhost:4000

### 3. Docker Compose (all services)

```bash
# Start all services (builds images if needed)
docker compose up -d

# Tail logs for all services
docker compose logs -f

# Tail logs for one service
docker compose logs -f auth-server

# Rebuild after code changes
docker compose up -d --build

# Stop everything
docker compose down

# Stop and remove volumes (clears persisted sessions)
docker compose down -v
```

### 4. Individual services

#### Auth server

```bash
cd auth-server

docker build -t auth-server .
docker run -d -p 4000:4000 --env-file .env --name auth-server auth-server

# Logs / stop
docker logs -f auth-server
docker rm -f auth-server
```

#### UI

```bash
cd ui

# VITE_ vars are baked into the JS bundle at build time and are
# visible in the browser — they are not server-side secrets.
docker build \
  --build-arg VITE_AGENT_NAME=eva \
  -t eva-ui .

docker run -d -p 8080:80 --name eva-ui eva-ui

# Logs / stop
docker logs -f eva-ui
docker rm -f eva-ui
```

#### Voice agent

```bash
cd voice-agent

docker build -t eva-voice-agent .
docker run -d --env-file .env.local --name eva-voice-agent eva-voice-agent

# Logs / stop
docker logs -f eva-voice-agent
docker rm -f eva-voice-agent
```

## Development (without Docker)

Requires [uv](https://docs.astral.sh/uv/).

```bash
cd voice-agent

uv run python agent.py dev
```

## Agent Tools

| Tool | Description |
|---|---|
| `search_video_content` | Semantic search over the video transcript using OpenAI embeddings + Pinecone. Supports filters for speaker, time range, section, and granularity. |
| `play_video` | Resume or start video playback |
| `pause_video` | Pause the video |
| `set_video_timestamp` | Jump to an absolute position in the video |
| `seek_video_by` | Seek forward or backward by a relative offset |
| `add_video_bookmark` | Save a labeled bookmark at a video position |
| `add_video_note` | Save a text note at a video position |

## Indexing Video Content

See [`embeddings/`](./embeddings/) for notebooks and scripts to:
1. Transcribe videos with speaker diarization
2. Chunk and embed transcripts using OpenAI `text-embedding-3-large`
3. Upload vectors to Pinecone
