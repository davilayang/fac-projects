# flows/deploy.py
# Register flow deployments with the Prefect server
# Run: PREFECT_API_URL=http://localhost:4200/api python -m flows.deploy

from dataclasses import dataclass, field
from typing import Any

from prefect import Flow
from prefect.deployments.runner import RunnerDeployment
from prefect.runner.storage import LocalStorage

from flows.arxiv_search import arxiv_ingestion_flow
from flows.extraction import extraction_flow

# The worker container mounts the project at /app (docker-compose volume).
WORKER_STORAGE = LocalStorage("/app")


@dataclass
class DeploymentConfig:
    flow: Flow[..., Any]
    name: str
    entrypoint: str
    parameters: dict[str, Any] = field(default_factory=dict)


# Add new deployments here
DEPLOYMENTS = [
    DeploymentConfig(
        flow=extraction_flow,
        name="extraction",
        entrypoint="flows/extraction.py:extraction_flow",
        parameters={
            "raw_dir": "data/pdfs",
            "output_dir": "data/extracted",
        },
    ),
    DeploymentConfig(
        flow=arxiv_ingestion_flow,
        name="arxiv-search",
        entrypoint="flows/arxiv_search.py:arxiv_ingestion_flow",
        # Parameters resolve from Prefect Variables at runtime.
        # Override per-run via the UI or pass here for deployment defaults.
    ),
]

if __name__ == "__main__":
    for config in DEPLOYMENTS:
        deployment = RunnerDeployment.from_flow(
            flow=config.flow,
            name=config.name,
            work_pool_name="local-pool",
            parameters=config.parameters,
        )
        deployment.storage = WORKER_STORAGE
        deployment.entrypoint = config.entrypoint

        deployment_id = deployment.apply()
        print(f"Deployment '{config.name}' registered (id={deployment_id}).")
