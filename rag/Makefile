# --- Dagster dev ---

.PHONY: dev build up down logs tunnel clean

dev:  ## Launch Dagster UI at localhost:3000
	-pkill -f dagster; uv run poe dev

# --- Docker Compose ---

build:  ## Build Docker images
	docker compose build

up:  ## Start Dagster cluster (Postgres, code server, webserver, daemon)
	docker compose up -d --build

up-prod:  ## Start full production stack (dagster + API + nginx + certbot)
	docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d --build

down:  ## Stop and remove containers
	docker compose down

down-prod:  ## Stop full production stack
	docker compose -f docker-compose.yaml -f docker-compose.prod.yaml down

logs:  ## Tail logs from all services
	docker compose logs -f

tunnel:  ## SSH tunnel to remote services (dagster or all)
	uv run poe tunnel $(or $(target),all)

# --- Cleanup ---

clean:  ## Remove caches, temp Dagster homes, and build artifacts
	find . -type d -name '__pycache__' -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.pytest_cache' -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.mypy_cache' -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.ruff_cache' -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.tmp_dagster_home_*' -exec rm -rf {} + 2>/dev/null || true
	@echo "Done."

# --- Helpers ---

.PHONY: help clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN {FS = ":.*## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
