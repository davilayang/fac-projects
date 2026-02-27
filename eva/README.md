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

See [Environment Variables](#environment-variables) above.

### 2. Start the agent

```bash
docker compose up --build
```

To run in the background:

```bash
docker compose up --build -d
```

### 3. Stop the agent

```bash
docker compose down
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
