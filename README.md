# livekit-project

## EVA

Three services: **ui** (React/Vite/nginx), **auth-server** (Express/TypeScript), **voice-agent** (Python/LiveKit).

### Tilt (recommended for local dev)

[Tilt](https://tilt.dev) runs all services, streams logs in a single UI, and live-updates containers on file changes without full rebuilds.

```bash
# Install Tilt (macOS)
brew install tilt

cd eva

# First-time setup
cp .env.example .env  # fill in your values

# Start everything — opens the Tilt UI at http://localhost:10350
./tilt-up.sh

# Stop everything (tears down containers and releases port 10350)
./tilt-down.sh
```

Services available at:
- UI: http://localhost:8080
- Auth server: http://localhost:4000

### Docker Compose (all services)

```bash
cd eva

# First-time setup: copy the example env and fill in your values
cp .env.example .env

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

### Auth server

```bash
cd eva/auth-server

# Build
docker build -t auth-server .

# Run
docker run -d -p 4000:4000 --env-file .env --name auth-server auth-server

# Logs / stop
docker logs -f auth-server
docker rm -f auth-server
```

### UI

```bash
cd eva/ui

# Build (VITE_ vars are baked into the JS bundle at build time and are
# visible in the browser — they are not server-side secrets.
# They also appear in `docker history`; do not pass genuinely secret
# values here. Use runtime environment injection for anything sensitive.)
docker build \
  --build-arg VITE_AGENT_NAME=eva \
  -t eva-ui .

# Run
docker run -d -p 8080:80 --name eva-ui eva-ui

# Logs / stop
docker logs -f eva-ui
docker rm -f eva-ui
```

### Voice agent

```bash
cd eva/voice-agent

# Build
docker build -t eva-voice-agent .

# Run
docker run -d --env-file .env.local --name eva-voice-agent eva-voice-agent

# Logs / stop
docker logs -f eva-voice-agent
docker rm -f eva-voice-agent
- [Projects Architecture](https://app.diagrams.net/#G1b9EFaT6Z02uhBsf_0o1GsCqXoUHfzkIQ)

## EVA, Events Voice Agent

Before running commands, change directory to "eva"

```bash
cd eva
```

Start Local Server

```bash

```
