# Airflow vs Dagster

## Concept Mapping

| Airflow | Dagster | Notes |
|---|---|---|
| DAG | Job (asset selection or op graph) | Top-level orchestration unit |
| Operator / Task | `@asset` (declarative) or `@op` (imperative) | Assets for data lineage, ops for side effects |
| `dag_id` / `task_id` | Asset key / op name | Auto-derived from function name |
| XCom | Asset materializations / op outputs | Assets pass data via IO managers, not push/pull |
| Connections | Resources (`ConfigurableResource`) | Dependency-injected, typed, testable |
| Scheduler | `ScheduleDefinition` (cron) | Attached to jobs |
| Sensor | `SensorDefinition` | Event-driven triggers (file arrival, external state) |
| Worker / Executor | Run launcher + code server | Code server (gRPC) loads definitions; launcher executes |
| DAG bag (file scan) | `Definitions` + code location | Explicit registration via `workspace.yaml` |
| `airflow dags trigger` | `dagster job execute` or UI | Or via schedule/sensor |

## Key Differences

- **Asset-centric, not task-centric** — Dagster models the *data* (assets) rather than the *tasks*. The framework tracks what was produced, when, and whether it's stale.
- **Local-first dev** — `dagster dev` auto-reloads on code changes. No metadata DB or scheduler required for basic testing (uses in-memory storage by default).
- **Resources as first-class citizens** — database connections, configs, and external services are `ConfigurableResource` objects injected into assets/ops. Easy to swap for testing.
- **Software-defined assets** — dependencies are declared, not imperative (`>>` chains). Dagster builds the graph from asset dependencies automatically.
- **Built-in asset lineage** — the UI shows a global asset graph with materialization history, partition status, and staleness indicators.

## Deployment Model

| | `dagster dev` | Docker Compose / Dagster+ |
|---|---|---|
| Use case | Local dev | Production |
| How it works | Single process, auto-reload, ephemeral storage | Code server + webserver + daemon + Postgres |
| Infra needed | None | Postgres + 3 services (code, webserver, daemon) |
| Analogy | `airflow standalone` | Full Airflow deployment |

## Architecture (Production)

| Service | Role | Airflow Equivalent |
|---|---|---|
| `dagster-code` (gRPC) | Loads definitions, serves code location | DAG processor |
| `dagster-webserver` | UI + GraphQL API | Airflow webserver |
| `dagster-daemon` | Schedules, sensors, run queue | Airflow scheduler |
| Postgres | Run storage, event log, schedule state | Airflow metadata DB |

## Dependency Isolation

| Approach | Airflow | Dagster |
|---|---|---|
| Virtualenv | `PythonVirtualenvOperator` | Not built-in; manage venv yourself |
| Docker | `DockerOperator` / KubernetesExecutor | Docker run launcher — each run gets its own container |
| Per-job image | `KubernetesPodOperator` | Separate code locations with different images |
| Multiple code locations | N/A | Each code location can have its own deps and Python version |

Multiple code locations in Dagster are the primary isolation mechanism — each loads in its own gRPC process with its own dependencies.

## Concurrency

### Concept Mapping

| Airflow | Dagster | Notes |
|---|---|---|
| `parallelism` (global) | Run queue concurrency limit | Max concurrent runs across all jobs |
| `dag_concurrency` | Per-job concurrency via run queue tags | Max concurrent runs of a specific job |
| `max_active_tasks_per_dag` | Op-level concurrency limits | Max concurrent ops within a single run |
| `pool` (Airflow pool) | `ConcurrencyLimit` (instance-level) | Named shared resource slots |
| N/A | Asset backfill concurrency | Controls parallelism during partition backfills |

### Two levels of concurrency

| Level | What controls it | Default |
|---|---|---|
| **Runs** (how many jobs execute in parallel) | `QueuedRunCoordinator` max concurrent runs | Unlimited (DefaultRunLauncher) |
| **Ops/assets within a run** | `Executor` config (multiprocess, in-process) | In-process (sequential) |

### Key difference
Airflow has **multiple knobs at multiple levels** (global `parallelism`, per-DAG `max_active_tasks`, per-pool slots, per-task `max_active_tis_per_dag`) that interact in confusing ways. Dagster keeps it cleaner:
- **Run-level:** `QueuedRunCoordinator` with tag-based concurrency rules
- **Op-level:** Multiprocess executor with `max_concurrent` config
- **Instance-level:** `ConcurrencyLimit` as named semaphores shared across all runs
- **In-code:** Standard Python concurrency (`ThreadPoolExecutor`) in asset/op bodies for I/O-bound work

### Example: concurrent downloads in an asset
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

import dagster as dg

@dg.asset(group_name="arxiv_ingestion", compute_kind="filesystem")
def downloaded_pdfs(
    context: dg.AssetExecutionContext,
    database: DatabaseResource,
    download_config: DownloadConfig,
) -> dg.MaterializeResult:
    pending = get_pending_downloads(database.get_engine())

    downloaded = 0
    with ThreadPoolExecutor(max_workers=download_config.max_workers) as pool:
        futures = {pool.submit(download_one, p): p for p in pending}
        for future in as_completed(futures):
            if future.result():
                downloaded += 1

    return dg.MaterializeResult(
        metadata={"downloaded": dg.MetadataValue.int(downloaded)}
    )
```
