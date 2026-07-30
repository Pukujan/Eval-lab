"""A killable Temporal worker for the durability probes.

Run as a subprocess so the worker-interruption test can SIGKILL it. SIGKILL, not
SIGTERM: a graceful shutdown would let the SDK drain, which would prove far less
than an abrupt loss of the process.

Usage:  python scripts/durability_worker.py --identity worker-a [--marker FILE]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import load_settings  # noqa: E402
from app.workflows.durability import (  # noqa: E402
    DURABILITY_ACTIVITIES,
    DURABILITY_TASK_QUEUE,
    DURABILITY_WORKFLOWS,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("durability-worker")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", required=True, help="worker identity, recorded in history")
    parser.add_argument("--task-queue", default=DURABILITY_TASK_QUEUE)
    parser.add_argument(
        "--marker",
        default=None,
        help="file touched once the worker is polling; lets the caller wait without sleeping",
    )
    args = parser.parse_args()

    settings = load_settings()

    from temporalio.client import Client
    from temporalio.worker import Worker

    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        identity=args.identity,
    )

    async with Worker(
        client,
        task_queue=args.task_queue,
        workflows=DURABILITY_WORKFLOWS,
        activities=DURABILITY_ACTIVITIES,
        identity=args.identity,
    ):
        logger.info("worker %s polling task queue %s", args.identity, args.task_queue)
        if args.marker:
            Path(args.marker).write_text(args.identity, encoding="utf-8")
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:  # pragma: no cover - signal path
        pass
