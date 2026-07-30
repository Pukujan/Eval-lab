"""Deterministic duplication probe.

Reproduces the defect on demand — not statistically, but every single run — by
holding every worker at the ``after-duplicate-check`` checkpoint until all of them
have passed the duplicate check.

Reports three numbers, deliberately from three different vantage points:

``raw_result_rows``
    What was actually written. Immune to read-side de-duplication.
``effect_count``
    How many times the irreversible external effect fired. Immune to everything a
    patch can do short of preventing the second execution.
``reported_commits``
    How many worker calls believed they committed.

A patch that changes the first number but not the second has hidden the symptom.
A patch that changes both has prevented duplicate processing. Reporting all three
is what lets a gate tell those apart.

Usage:  python probe.py <database-path> [worker-count]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src import sync  # noqa: E402
from src.effects import effect_count  # noqa: E402
from src.processor import Job  # noqa: E402
from src.store import ResultStore  # noqa: E402
from src.worker import deliver_concurrently  # noqa: E402

JOB_ID = "job-duplicate-probe"


def run_probe(database_path: str, worker_count: int = 2) -> dict[str, int | bool]:
    """Force the check-then-write window open and report what happened."""
    ResultStore.initialise(database_path)
    job = Job(job_id=JOB_ID, payload="probe-payload")

    sync.set_coordinator(sync.BarrierCoordinator("after-duplicate-check", worker_count))
    try:
        report = deliver_concurrently(database_path, job, worker_count=worker_count)
    finally:
        sync.set_coordinator(None)

    store = ResultStore(database_path)
    try:
        rows = [row for row in store.raw_result_rows() if row[0] == JOB_ID]
    finally:
        store.close()

    effects = effect_count(database_path, JOB_ID)
    return {
        "worker_count": worker_count,
        "raw_result_rows": len(rows),
        "effect_count": effects,
        "reported_commits": report.commit_count,
        # The primary invariant, evaluated against what was written.
        "invariant_holds": len(rows) <= 1,
        # Duplicate *processing*, which is a stronger statement than duplicate output.
        "duplicate_processing": effects > 1,
    }


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "probe.db"
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    print(json.dumps(run_probe(path, workers), indent=2, sort_keys=True))
