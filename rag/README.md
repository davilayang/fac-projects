# fnc-ingestion

arXiv documents ingestion, chunking and embedding Pipeline

## Prerequisites

- Python >= 3.13
- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Setup

```bash
# Install dependencies
uv sync
```

### Local Development

- First, setup `.env` from `.env.example`, then initialise the Prefect clustter

```bash
cp .env .env.example
# Then, setup the file with right credentials

# Build and Start cluster (Postgres, Redis, Prefect server, worker, and creates "local-pool" work pool)
docker compose up --build

# Initialise database (for ingestions data store, using Prefect cluster's Postgres)
uv run poe db-setup
```

- The Prefect UI is available at http://localhost:4200.
- When finished, stop the cluster by `Ctrl-C`

```bash
# Take down the cluster and its containers and volumes
docker compose down --volumes
```

## Deploying & Running Flows

**Deploy all Flows** in /flows

This registers all of the flows defined in flows/deploy.py to the cluster, only 
metadata. So if additional changes are made in any of the flow, they'll be reflected 
when the flow runs without redeploying the flow.  
The worker container mounts the project directory, so local code changes are 
picked up on the next run without restarting.

```bash
uv run --env-file .env poe deploy
# If "Work pool "local-pool" not found." wait a bit and then re-run
```

**Trigger Flow Run**

- Option A: from the Prefect UI at http://localhost:4200
  - Navigate to Deployments => "<flow-name>" => Run => Quick Run
- Option B: from the CLI  (single Run, not the deployment)
  - `uv run --env-file .env python -m flows.extraction`

## Airflow vs Prefect

### Concept Mapping

| Airflow | Prefect v3 | Notes |
|---|---|---|
| DAG | `@flow` | Top-level orchestration unit |
| Operator / Task | `@task` | Unit of work — just a decorated Python function |
| `dag_id` / `task_id` | Flow / task name | Auto-derived from function name |
| XCom | Return values | Tasks return Python objects directly, no push/pull |
| Connections | Blocks / env vars | Plain env vars or Prefect Blocks |
| Scheduler | Deployments + schedules | Cron/interval schedules attached to deployments |
| Worker / Executor | Work pool + worker | `prefect worker start --pool <pool>` |
| DAG bag (file scan) | `flow.deploy()` | Explicit registration, no folder scanning |
| `airflow dags trigger` | `prefect deployment run` | Or trigger from UI |

### Key Differences

- **Pure Python, no Operators** — no `PythonOperator`, `BashOperator`, or `>>` chains. Dependencies are implicit from normal Python control flow.
- **Local-first dev** — run any flow as `python flows/extraction.py` with no server or DB required. Airflow needs the metadata DB + scheduler just to test.
- **Dynamic workflows are native** — use loops and conditionals directly. No `Dynamic Task Mapping` needed.
- **No graph view** — Prefect UI shows a timeline of task runs and logs, not a DAG graph. Works well for linear pipelines but less visual for complex branching.

### Deployment Model

| | `flow.serve()` | `flow.deploy()` |
|---|---|---|
| Use case | Local dev | Production |
| How it works | Long-running process that schedules + executes | Registers with server; a separate worker executes |
| Infra needed | None (single process) | Prefect server + work pool + worker |
| Analogy | N/A | Putting a DAG file in Airflow's `dags/` folder |

### Dependency Isolation

| Approach | Airflow | Prefect |
|---|---|---|
| Virtualenv | `PythonVirtualenvOperator` | Not built-in; manage venv yourself |
| Docker | `DockerOperator` / KubernetesExecutor | Docker work pool — each run gets its own container |
| Per-flow image | `KubernetesPodOperator` | `flow.deploy(image="...")` per deployment |

There is no per-task isolation within a single flow. If tasks need conflicting deps, split them into separate flows with separate images.

## References

- https://docs.prefect.io/v3/how-to-guides/self-hosted/docker-compose
