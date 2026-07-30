"""At-least-once delivery across two workers.

The delivery guarantee is the premise, not the bug: a queue that redelivers on
uncertain acknowledgement is behaving correctly. The defect is that the consumer
is not idempotent under it.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from .processor import Job, JobProcessor


@dataclass
class DeliveryReport:
    """Which worker calls reported committing a result."""

    committed_by: list[str]

    @property
    def commit_count(self) -> int:
        return len(self.committed_by)


def deliver_concurrently(
    database_path: str, job: Job, worker_count: int = 2
) -> DeliveryReport:
    """Deliver the same job to ``worker_count`` workers at the same time.

    Each worker builds its own processor and therefore its own database
    connection, matching two independent consumer processes.
    """
    committed_by: list[str] = []
    lock = threading.Lock()

    def run(worker_name: str) -> None:
        processor = JobProcessor(database_path)
        try:
            if processor.process(job):
                with lock:
                    committed_by.append(worker_name)
        finally:
            processor.close()

    threads = [
        threading.Thread(target=run, args=(f"worker-{index}",), name=f"worker-{index}")
        for index in range(worker_count)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30.0)

    return DeliveryReport(committed_by=committed_by)


def deliver_sequentially(database_path: str, job: Job, times: int = 2) -> DeliveryReport:
    """Redeliver the same job one call after another.

    The sequential path is *correct even in the known-bad version* — the check
    sees the committed result the second time. Keeping it here matters: it is what
    makes the concurrent failure a race rather than a plain missing check, and it
    is why a hypothesis blaming "no duplicate check at all" is falsifiable.
    """
    committed_by: list[str] = []
    for index in range(times):
        processor = JobProcessor(database_path)
        try:
            if processor.process(job):
                committed_by.append(f"delivery-{index}")
        finally:
            processor.close()
    return DeliveryReport(committed_by=committed_by)
