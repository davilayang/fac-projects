# EVA Voice Agent

A LiveKit-powered voice AI assistant using STT → LLM → TTS

## Deveolopment Instructions  

The Voice Agent runs as a LiveKit worker and waits for job dispatches.

### Start local agent 

In the "voice-agent" working directory, run: 

```bash
uv run --env-file .env python agent.py dev
```

Wait for the `registered worker` log line before proceeding.

### Join a manual created session on Playground

```bash
AGENT_NAME=eva

# Dispatch the agent to a new room
PG_ROOM=$(
  lk dispatch create --agent-name eva --new-room 2>&1 | grep -o 'room:"[^"]*"' | cut -d'"' -f2
)
echo $PG_ROOM

# Get token to join the room
lk token create --join \
  --room $PG_ROOM \
  --identity test-user \
  --valid-for 10m
```

- Visit Playground: https://agents-playground.livekit.io
- On Manual Page, uses the output URL and token to join

### 3. Dispatch the agent to a room

To dispatch to an existing room (e.g. from the LiveKit Playground):

```bash
lk dispatch create --agent-name eva --room <room-name>
```

Your local agent terminal should show a `received job request` log confirming it picked up the dispatch.

### 4. Join the room

Generate a token and join via the [LiveKit Playground](https://agents-playground.livekit.io):

```bash
lk token create \
  --join \
  --room <room-name> \
  --identity test-user \
  --valid-for 10m
```

In the Playground, set the server URL to your `LIVEKIT_URL` and paste the token.

> **Note:** The video control tools (`play_video`, `pause_video`, etc.) require a UI participant in the room and will return a `ToolError` without one. The LLM conversation works regardless.

## MCP Tools (Pinecone)

The agent connects to a Pinecone MCP server at session start. To verify tools are discovered, check the startup logs for tool names after connecting to a room.

If you see `Access denied: Permission control::index::describe is required`, the Pinecone API key is missing required permissions — update `PINECONE_BETA_TOKEN` in `.env.local` with a key that has full index and data access.
