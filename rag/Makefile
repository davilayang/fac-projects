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

.PHONY: help install up down reset db-setup ingest query eval seed check

help:
	@echo ""
	@echo "  install    Install Python dependencies"
	@echo "  up         Start all services (Postgres, Redis, Prefect, Metabase, Grafana)"
	@echo "  down       Stop all services, keep data"
	@echo "  reset      Stop all services and delete all data volumes"
	@echo "  db-setup   Create schema, tables, and vector index"
	@echo "  ingest     Run full pipeline: extract → chunk → embed"
	@echo "  query      Retrieve chunks (Q='question'); add LLM=1 to generate an answer"
	@echo "  eval       Run all test queries and report recall@5; add LLM=1 for generated answers"
	@echo "  seed       Run a batch of sample queries to populate logs for Grafana/Metabase"
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
	$(UV_RUN) python query.py $(if $(Q),--question "$(Q)",) $(if $(LLM),--llm,)

eval:
	$(UV_RUN) python eval.py $(if $(LLM),--llm,)

seed:
	$(UV_RUN) python seed_queries.py

check:
	$(UV_RUN) poe check
