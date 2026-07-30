"""Activity retry behaviour, proved against real Temporal history.

An activity fails a known number of times and then succeeds. The claims:

* the configured retry policy is the one Temporal actually recorded;
* the expected number of attempts occurred;
* backoff stayed inside the configured bound;
* the workflow completed;
* the consequential side effect happened exactly once.

A note on where the attempt count comes from. Temporal does **not** write an event
per failed activity attempt — intermediate failures are not in history, by design.
The attempt number lives on the ``ActivityTaskStarted`` event, and that is what is
asserted here, cross-checked against the activity's own durable ledger. Two
independent witnesses; no custom history parser.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from app.config import load_settings  # noqa: E402
from app.evidence.artifacts import (  # noqa: E402
    EvidenceError,
    event_types,
    events_of_type,
    require,
    workflow_status_name,
    write_evidence,
    write_history,
)
from app.workflows.durability import (  # noqa: E402
    DURABILITY_TASK_QUEUE,
    RETRY_PROBE_POLICY,
    RetryProbeWorkflow,
    effect_count,
    effect_rows,
)

FAIL_TIMES = 3
EXPECTED_ATTEMPTS = FAIL_TIMES + 1


def start_worker(identity: str, marker: Path) -> subprocess.Popen:
    marker.unlink(missing_ok=True)
    process = subprocess.Popen(
        [
            sys.executable,
            str(REPOSITORY_ROOT / "scripts" / "durability_worker.py"),
            "--identity",
            identity,
            "--marker",
            str(marker),
        ],
        cwd=str(REPOSITORY_ROOT),
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if marker.is_file():
            return process
        if process.poll() is not None:
            raise EvidenceError(f"worker {identity} exited early (rc={process.returncode})")
        time.sleep(0.5)
    process.kill()
    raise EvidenceError("retry worker did not start polling in time")


async def main() -> int:
    from temporalio.client import Client, WorkflowExecutionStatus

    settings = load_settings()
    settings.ensure_directories()

    run_key = f"retry-{int(time.time())}"
    workflow_id = f"retry-probe-{run_key}"
    ledger_path = str(settings.var_dir / "durability-ledger.db")
    marker = settings.var_dir / "worker-retry.marker"

    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    worker = start_worker("retry-worker", marker)

    try:
        started_at = time.monotonic()
        handle = await client.start_workflow(
            RetryProbeWorkflow.run,
            {"run_key": run_key, "ledger_path": ledger_path, "fail_times": FAIL_TIMES},
            id=workflow_id,
            task_queue=DURABILITY_TASK_QUEUE,
            execution_timeout=timedelta(minutes=5),
        )
        result = await asyncio.wait_for(handle.result(), timeout=240)
        elapsed = time.monotonic() - started_at

        described = await handle.describe()
        history = await handle.fetch_history()
        history_dict = history.to_json_dict()
        types = event_types(history_dict)

        scheduled = events_of_type(history_dict, "EVENT_TYPE_ACTIVITY_TASK_SCHEDULED")
        started_events = events_of_type(history_dict, "EVENT_TYPE_ACTIVITY_TASK_STARTED")
        completed = events_of_type(history_dict, "EVENT_TYPE_ACTIVITY_TASK_COMPLETED")

        require(len(scheduled) == 1, f"expected one ActivityTaskScheduled, got {len(scheduled)}")
        require(len(completed) == 1, f"expected one ActivityTaskCompleted, got {len(completed)}")
        require(len(started_events) >= 1, "history has no ActivityTaskStarted event")

        # The retry policy Temporal actually recorded, not the one we think we set.
        recorded_policy = (
            scheduled[0].get("activityTaskScheduledEventAttributes", {}).get("retryPolicy", {})
        )
        require(
            int(recorded_policy.get("maximumAttempts", 0)) == RETRY_PROBE_POLICY.maximum_attempts,
            f"recorded maximumAttempts {recorded_policy.get('maximumAttempts')} != configured "
            f"{RETRY_PROBE_POLICY.maximum_attempts}",
        )
        require(
            float(recorded_policy.get("backoffCoefficient", 0))
            == RETRY_PROBE_POLICY.backoff_coefficient,
            "recorded backoffCoefficient does not match configuration",
        )

        history_attempt = int(
            started_events[-1].get("activityTaskStartedEventAttributes", {}).get("attempt", 0)
        )
        activity_attempt = int(result["activity_result"]["final_attempt"])

        require(
            history_attempt == EXPECTED_ATTEMPTS,
            f"history shows {history_attempt} attempts, expected {EXPECTED_ATTEMPTS}",
        )
        require(
            activity_attempt == EXPECTED_ATTEMPTS,
            f"activity reported attempt {activity_attempt}, expected {EXPECTED_ATTEMPTS}",
        )

        ledger_attempts = effect_count(ledger_path, run_key, "attempt")
        require(
            ledger_attempts == EXPECTED_ATTEMPTS,
            f"durable ledger recorded {ledger_attempts} attempts, expected {EXPECTED_ATTEMPTS}",
        )

        committed = effect_count(ledger_path, run_key, "committed")
        require(
            committed == 1,
            f"consequential side effect happened {committed} times, expected exactly 1",
        )

        require(
            "EVENT_TYPE_WORKFLOW_EXECUTION_COMPLETED" in types,
            "workflow did not complete",
        )
        require(
            described.status == WorkflowExecutionStatus.COMPLETED,
            f"terminal status was {workflow_status_name(described.status)}",
        )

        # Backoff bound: 1s + 2s + 4s = 7s of waiting, plus execution. A generous
        # ceiling still falsifies unbounded or mis-scaled backoff.
        max_backoff_seconds = 1 + 2 + 4
        require(
            elapsed < max_backoff_seconds + 60,
            f"elapsed {elapsed:.1f}s exceeds the configured backoff bound plus slack",
        )

        history_path = write_history("retry-behaviour", history)
        evidence_path = write_evidence(
            "retry-behaviour",
            {
                "claim": "Temporal applied the configured retry policy; the activity was "
                "attempted the expected number of times and committed once",
                "workflow_id": workflow_id,
                "run_id": history.run_id,
                "configured_policy": {
                    "initial_interval_seconds": RETRY_PROBE_POLICY.initial_interval.total_seconds(),
                    "backoff_coefficient": RETRY_PROBE_POLICY.backoff_coefficient,
                    "maximum_interval_seconds": RETRY_PROBE_POLICY.maximum_interval.total_seconds(),
                    "maximum_attempts": RETRY_PROBE_POLICY.maximum_attempts,
                },
                "recorded_policy_from_history": recorded_policy,
                "induced_failures": FAIL_TIMES,
                "expected_attempts": EXPECTED_ATTEMPTS,
                "attempts_from_history": history_attempt,
                "attempts_from_activity": activity_attempt,
                "attempts_from_durable_ledger": ledger_attempts,
                "consequential_effect_count": committed,
                "elapsed_seconds": round(elapsed, 3),
                "backoff_bound_seconds": max_backoff_seconds,
                "terminal_status": workflow_status_name(described.status),
                "history_event_types": types,
                "effect_ledger": effect_rows(ledger_path, run_key),
                "history_artifact": str(history_path),
            },
        )

        print("retry behaviour VERIFIED")
        print(f"  workflow id        : {workflow_id}")
        print(f"  attempts (history) : {history_attempt} (expected {EXPECTED_ATTEMPTS})")
        print(f"  attempts (ledger)  : {ledger_attempts}")
        print(f"  committed effects  : {committed} (must be 1)")
        print(f"  elapsed            : {elapsed:.1f}s (bound {max_backoff_seconds}s + slack)")
        print(f"  evidence           : {evidence_path}")
        return 0

    except EvidenceError as exc:
        write_evidence("retry-behaviour", {"verified": False, "failure": str(exc)})
        print(f"retry behaviour NOT VERIFIED: {exc}", file=sys.stderr)
        return 1
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.wait(timeout=30)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
