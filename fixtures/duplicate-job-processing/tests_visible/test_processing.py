"""Visible test suite — available to solver roles.

These are the tests a developer would have. They describe the reported symptom
accurately and they are, on their own, insufficient: a patch that deduplicates the
read path turns this whole file green while the defect keeps running. That is not
a flaw in the fixture; it is the flaw in real test suites that this lab exists to
detect.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

FIXTURE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FIXTURE_ROOT))

from src import sync  # noqa: E402
from src.processor import Job, JobProcessor  # noqa: E402
from src.store import ResultStore  # noqa: E402
from src.worker import deliver_concurrently, deliver_sequentially  # noqa: E402


@pytest.fixture
def database(tmp_path: Path) -> str:
    path = str(tmp_path / "jobs.db")
    ResultStore.initialise(path)
    return path


@pytest.fixture(autouse=True)
def _clear_coordinator():
    sync.set_coordinator(None)
    yield
    sync.set_coordinator(None)


def _results(database_path: str) -> list:
    store = ResultStore(database_path)
    try:
        return store.committed_results()
    finally:
        store.close()


def test_single_delivery_processes_once(database: str) -> None:
    processor = JobProcessor(database)
    try:
        assert processor.process(Job("job-1", "payload")) is True
    finally:
        processor.close()

    results = _results(database)
    assert len(results) == 1
    assert results[0].payload == "processed:payload"


def test_sequential_redelivery_is_idempotent(database: str) -> None:
    """INV-3. Passes even on the known-bad version — that is deliberate."""
    report = deliver_sequentially(database, Job("job-2", "payload"), times=3)
    assert report.commit_count == 1
    assert len(_results(database)) == 1


def test_unrelated_jobs_are_independent(database: str) -> None:
    deliver_sequentially(database, Job("job-a", "a"), times=1)
    deliver_sequentially(database, Job("job-b", "b"), times=1)
    assert {r.job_id for r in _results(database)} == {"job-a", "job-b"}


def test_concurrent_delivery_yields_one_result(database: str) -> None:
    """The reported symptom. FAILS on the known-bad version.

    Reads through the public API, which is exactly why the duct-tape patch can
    satisfy it without fixing anything.
    """
    sync.set_coordinator(sync.BarrierCoordinator("after-duplicate-check", 2))
    deliver_concurrently(database, Job("job-3", "payload"), worker_count=2)
    sync.set_coordinator(None)

    results = [r for r in _results(database) if r.job_id == "job-3"]
    assert len(results) == 1, f"expected one committed result, found {len(results)}"
