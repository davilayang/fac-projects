# EVA Voice Agent

A LiveKit-powered voice AI assistant using STT → LLM → TTS

## Testing Without the UI

The agent runs as a LiveKit worker and waits for job dispatches. Because a cloud-deployed agent may also be registered under the same name, use a distinct agent name locally to avoid conflicts.

### 1. Set a unique agent name for local testing

In `agent.py`, change the agent name:

```python
@server.rtc_session(agent_name="eva-dev")
```

### 2. Start the local agent

```bash
uv run python agent.py dev
```

Wait for the `registered worker` log line before proceeding.

### 3. Dispatch the agent to a room

To dispatch to a new auto-generated room:

```bash
lk dispatch create --agent-name eva-dev --new-room
```

To dispatch to an existing room (e.g. from the LiveKit Playground):

```bash
lk dispatch create --agent-name eva-dev --room <room-name>
```

Your local agent terminal should show a `received job request` log confirming it picked up the dispatch.

### 4. Join the room

Generate a token and join via the [LiveKit Playground](https://agents-playground.livekit.io):

```bash
lk token create \
  --join \
  --room <room-name> \
  --identity test-user \
  --valid-for 1h
```

In the Playground, set the server URL to your `LIVEKIT_URL` and paste the token.

> **Note:** The video control tools (`play_video`, `pause_video`, etc.) require a UI participant in the room and will return a `ToolError` without one. The LLM conversation works regardless.

## MCP Tools (Pinecone)

The agent connects to a Pinecone MCP server at session start. To verify tools are discovered, check the startup logs for tool names after connecting to a room.

If you see `Access denied: Permission control::index::describe is required`, the Pinecone API key is missing required permissions — update `PINECONE_BETA_TOKEN` in `.env.local` with a key that has full index and data access.
