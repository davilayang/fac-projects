#!/bin/bash
# Deploy to Hetzner via private Docker registry.
#
# Usage:
#   First deploy:  bash scripts/deploy.sh <tag> --init   (gets SSL cert)
#   Re-deploy:     bash scripts/deploy.sh <tag>
set -euo pipefail

SERVER="hetzner"
REMOTE_DIR="/opt/arxiv-rag"
REGISTRY="localhost:5000"
IMAGE="arxiv-rag-api"
TAG="${1:-}"

if [[ -z "$TAG" ]]; then
    echo "Usage: bash scripts/deploy.sh <tag> [--init]"
    echo "  e.g. bash scripts/deploy.sh v1.0.0"
    exit 1
fi

echo "==> Building image (linux/amd64)..."
docker build --platform linux/amd64 -t "$REGISTRY/$IMAGE:$TAG" .

echo "==> Opening SSH tunnel to registry..."
ssh -L 5000:localhost:5000 "$SERVER" -N -f
trap 'pkill -f "ssh -L 5000:localhost:5000"' EXIT

echo "==> Pushing image to registry..."
docker push "$REGISTRY/$IMAGE:$TAG"

echo "==> Syncing config files..."
ssh "$SERVER" "sudo mkdir -p $REMOTE_DIR/nginx/conf.d $REMOTE_DIR/scripts && sudo chown -R \$(whoami) $REMOTE_DIR"

scp docker-compose.yml               "$SERVER:$REMOTE_DIR/"
scp nginx/conf.d/arxiv-rag.conf      "$SERVER:$REMOTE_DIR/nginx/conf.d/"
scp scripts/init-ssl.sh              "$SERVER:$REMOTE_DIR/scripts/"
ssh "$SERVER" "chmod +x $REMOTE_DIR/scripts/init-ssl.sh"

# Copy .env only if it doesn't already exist on the server
ssh "$SERVER" "test -f $REMOTE_DIR/.env" 2>/dev/null || {
    echo "==> No .env found on server — copying local .env..."
    scp .env "$SERVER:$REMOTE_DIR/"
}

if [[ "${2:-}" == "--init" ]]; then
    echo "==> Getting SSL certificate..."
    ssh "$SERVER" "cd $REMOTE_DIR && TAG=$TAG bash scripts/init-ssl.sh"
fi

echo "==> Pulling image and restarting services..."
ssh "$SERVER" "cd $REMOTE_DIR && TAG=$TAG docker compose pull api && TAG=$TAG docker compose up -d"

echo ""
echo "✓ Deployed to https://arxiv-rag.45weeks.com"
