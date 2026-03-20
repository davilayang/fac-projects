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
