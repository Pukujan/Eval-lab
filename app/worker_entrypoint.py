"""Long-lived Temporal worker process (the Compose `worker` service)."""

from __future__ import annotations

import asyncio
import logging

from app.config import load_settings
from app.telemetry.tracing import configure_tracing
from app.workflows.coding_evaluation import run_worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("worker")


def main() -> None:
    settings = load_settings()
    settings.ensure_directories()
    configure_tracing(
        endpoint=settings.phoenix_endpoint, project_name=settings.phoenix_project_name
    )
    logger.info(
        "starting worker: temporal=%s queue=%s phoenix=%s",
        settings.temporal_address,
        settings.temporal_task_queue,
        settings.phoenix_endpoint or "(export disabled)",
    )
    asyncio.run(run_worker(settings))


if __name__ == "__main__":
    main()
