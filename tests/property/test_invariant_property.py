"""Hypothesis property-based test of the primary invariant.

Property: for **any** number of concurrent at-least-once deliveries of one job
identifier, a correct processor commits at most one result and fires the external
effect at most once.

Both directions are asserted, and the second matters as much as the first: the
known-bad implementation must *violate* the property. A property that passes on
broken code is measuring nothing.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.activities.patching import create_working_copy
from app.config import FIXTURE_ROOT

pytestmark = pytest.mark.property

# Subprocess work is legitimately slow, and Hypothesis' default deadline would
# flake on it. Bounded example count keeps the suite quick.
PROPERTY_SETTINGS = settings(
    max_examples=8,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)

_DRIVER = textwrap.dedent(
    """
    import json, sys
    sys.path.insert(0, ".")
    from src import sync
    from src.effects import effect_count
    from src.processor import Job
    from src.store import ResultStore
    from src.worker import deliver_concurrently

    database, job_id, workers = sys.argv[1], sys.argv[2], int(sys.argv[3])
    ResultStore.initialise(database)
    sync.set_coordinator(sync.BarrierCoordinator("after-duplicate-check", workers))
    try:
        deliver_concurrently(database, Job(job_id, "payload"), worker_count=workers)
    finally:
        sync.set_coordinator(None)

    store = ResultStore(database)
    try:
        rows = [r for r in store.raw_result_rows() if r[0] == job_id]
    finally:
        store.close()
    print(json.dumps({"rows": len(rows), "effects": effect_count(database, job_id)}))
    """
)


def _observe(working_copy: Path, job_id: str, workers: int) -> dict[str, int]:
    result = subprocess.run(
        [sys.executable, "-c", _DRIVER, f"{job_id}.db", job_id, str(workers)],
        cwd=str(working_copy),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, f"driver failed: {result.stderr[:400]}"
    import json

    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def fixed_copy(tmp_path_factory):
    """A working copy with the known-good repair applied."""
    root = tmp_path_factory.mktemp("property-fixed")
    copy = create_working_copy(destination_root=root)
    shutil.copyfile(FIXTURE_ROOT / "reference" / "processor.py", copy.path / "src" / "processor.py")
    yield copy.path
    copy.cleanup()


@pytest.fixture(scope="module")
def broken_copy(tmp_path_factory):
    root = tmp_path_factory.mktemp("property-broken")
    copy = create_working_copy(destination_root=root)
    yield copy.path
    copy.cleanup()


@PROPERTY_SETTINGS
@given(
    workers=st.integers(min_value=2, max_value=5),
    nonce=st.integers(min_value=0, max_value=10_000),
)
def test_repaired_processor_commits_at_most_once(
    fixed_copy: Path, workers: int, nonce: int
) -> None:
    """For any concurrency level, at most one commit and one effect."""
    observed = _observe(fixed_copy, f"prop-fixed-{workers}-{nonce}", workers)
    assert observed["rows"] <= 1, f"{observed['rows']} rows committed with {workers} workers"
    assert observed["effects"] <= 1, (
        f"external effect fired {observed['effects']} times with {workers} workers"
    )


@PROPERTY_SETTINGS
@given(
    workers=st.integers(min_value=2, max_value=5),
    nonce=st.integers(min_value=0, max_value=10_000),
)
def test_known_bad_processor_violates_the_property(
    broken_copy: Path, workers: int, nonce: int
) -> None:
    """The property must FAIL on the unrepaired code, or it is measuring nothing."""
    observed = _observe(broken_copy, f"prop-broken-{workers}-{nonce}", workers)
    assert observed["rows"] == workers
    assert observed["effects"] == workers
