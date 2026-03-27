# RAG Ingestion Pipeline
#
# Quickstart:
#   make install
#   cp .env.example .env  # fill in credentials
#   make up               # second terminal
#   make db-setup
#   make ingest

ENV_FILE := .env
UV_RUN := uv run $(if $(wildcard $(ENV_FILE)),--env-file $(ENV_FILE),)

.PHONY: help install up down reset db-setup ingest query eval check

help:
	@echo ""
	@echo "  install    Install Python dependencies"
	@echo "  up         Start all services (Postgres, Redis, Prefect)"
	@echo "  down       Stop all services, keep data"
	@echo "  reset      Stop all services and delete all data volumes"
	@echo "  db-setup   Create schema, tables, and vector index"
	@echo "  ingest     Run full pipeline: extract → chunk → embed"
	@echo "  query      Run a test retrieval query (usage: make query Q='your question')"
	@echo "  eval       Run all test queries and report recall@5"
	@echo "  check      Run fmt, lint, type checks, and tests"
	@echo ""

install:
	uv sync

up:
	docker compose up --build

down:
	docker compose down

reset:
	docker compose down --volumes

db-setup:
	$(UV_RUN) poe db-setup

ingest:
	$(UV_RUN) python -m flows.extraction
	$(UV_RUN) python -m flows.chunking
	$(UV_RUN) python -m flows.embedding

query:
	$(UV_RUN) python query.py $(if $(Q),--question "$(Q)",)

eval:
	$(UV_RUN) python eval.py

check:
	$(UV_RUN) poe check
