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
