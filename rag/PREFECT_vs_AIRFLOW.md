# Airflow vs Prefect

## Concept Mapping

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

## Key Differences

- **Pure Python, no Operators** — no `PythonOperator`, `BashOperator`, or `>>` chains. Dependencies are implicit from normal Python control flow.
- **Local-first dev** — run any flow as `python flows/extraction.py` with no server or DB required. Airflow needs the metadata DB + scheduler just to test.
- **Dynamic workflows are native** — use loops and conditionals directly. No `Dynamic Task Mapping` needed.
- **No graph view** — Prefect UI shows a timeline of task runs and logs, not a DAG graph. Works well for linear pipelines but less visual for complex branching.

## Deployment Model

| | `flow.serve()` | `flow.deploy()` |
|---|---|---|
| Use case | Local dev | Production |
| How it works | Long-running process that schedules + executes | Registers with server; a separate worker executes |
| Infra needed | None (single process) | Prefect server + work pool + worker |
| Analogy | N/A | Putting a DAG file in Airflow's `dags/` folder |

## Dependency Isolation

| Approach | Airflow | Prefect |
|---|---|---|
| Virtualenv | `PythonVirtualenvOperator` | Not built-in; manage venv yourself |
| Docker | `DockerOperator` / KubernetesExecutor | Docker work pool — each run gets its own container |
| Per-flow image | `KubernetesPodOperator` | `flow.deploy(image="...")` per deployment |

There is no per-task isolation within a single flow. If tasks need conflicting deps, split them into separate flows with separate images.

## Concurrency

### Concept Mapping

| Airflow | Prefect v3 | Notes |
|---|---|---|
| `parallelism` (global) | Work pool concurrency limit | Max concurrent task instances across all DAGs / flow runs |
| `dag_concurrency` | `--limit` on `prefect worker start` | Max concurrent runs of a specific DAG / within a worker |
| `max_active_tasks_per_dag` | `ThreadPoolTaskRunner(max_workers=N)` | Max concurrent tasks within a single DAG run / flow run |
| `pool` (Airflow pool) | Global concurrency limit (`prefect gcl create`) | Named shared resource slots (e.g., "database: 5 slots") |
| N/A | `rate_limit()` | Token-bucket rate limiting (no Airflow equivalent without custom plugin) |

### Two levels of concurrency

| Level | What controls it | Default |
|---|---|---|
| **Flow runs** (how many flows execute in parallel) | Worker `--limit` flag + work pool concurrency | Sequential (1 at a time per worker) |
| **Tasks within a flow** (how many tasks run concurrently) | `ThreadPoolTaskRunner(max_workers=N)` + `.submit()` | Sequential (tasks called directly block) |

### Key difference
Airflow has **multiple knobs at multiple levels** (global `parallelism`, per-DAG `max_active_tasks`, per-pool slots, per-task `max_active_tis_per_dag`) that interact in confusing ways. Prefect keeps it simpler:
- **Task-level:** Use `ThreadPoolTaskRunner` + `.submit()` for in-process thread concurrency, or `task.map()` as shorthand
- **Cross-flow:** Use global concurrency limits (`prefect gcl create`) as named semaphores shared across all flow runs
- **Rate limiting:** Built-in `rate_limit()` with token-bucket semantics — no equivalent in Airflow without a custom operator/plugin

### Example: concurrent downloads with rate limiting
```python
from prefect import flow, task
from prefect.task_runners import ThreadPoolTaskRunner
from prefect.concurrency.sync import concurrency

@task(retries=3, retry_delay_seconds=[5, 15, 30])
def download_pdf(paper, pdf_dir):
    with concurrency("arxiv-downloads", occupy=1):  # server-side limit
        ...

@flow(task_runner=ThreadPoolTaskRunner(max_workers=5), log_prints=True)
def arxiv_ingestion_flow(...):
    futures = [download_pdf.submit(p, pdf_dir) for p in pending]
    for f in futures:
        f.wait()
```

```bash
# Create the server-side limit (once):
prefect gcl create arxiv-downloads --limit 5
```
