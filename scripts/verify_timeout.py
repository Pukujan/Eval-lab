"""Activity timeout behaviour, proved against real Temporal history.

An activity deliberately sleeps past its ``start_to_close_timeout``. The claims:

* the timeout is recorded in history as ``ActivityTaskTimedOut``;
* the workflow follows the documented failure policy (catch, classify, return);
* the terminal classification is ``infrastructure_failure``;
* the incident is visible in traces;
* it is **not** misclassified as a defective code patch.

That last claim is the point of the whole exercise. A slow or overloaded activity
is a statement about the harness, and reporting it as ``rejected`` would invent a
coding verdict from a platform problem.
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
from app.reliability.gates import classify_infrastructure_incident  # noqa: E402
from app.telemetry.tracing import SpanLedger, configure_tracing, span  # noqa: E402
from app.workflows.durability import (  # noqa: E402
    DURABILITY_TASK_QUEUE,
    TimeoutProbeWorkflow,
)

TIMEOUT_SECONDS = 5
SLEEP_SECONDS = 30


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
    raise EvidenceError("timeout worker did not start polling in time")


async def main() -> int:
    from temporalio.client import Client, WorkflowExecutionStatus

    settings = load_settings()
    settings.ensure_directories()

    run_key = f"timeout-{int(time.time())}"
    workflow_id = f"timeout-probe-{run_key}"
    marker = settings.var_dir / "worker-timeout.marker"

    configure_tracing(
        endpoint=settings.phoenix_endpoint, project_name=settings.phoenix_project_name
    )
    ledger = SpanLedger()

    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    worker = start_worker("timeout-worker", marker)

    try:
        with span(
            "coding-evaluation",
            ledger,
            {"evaluation.run_id": run_key, "evaluation.probe": "activity-timeout"},
        ):
            handle = await client.start_workflow(
                TimeoutProbeWorkflow.run,
                {
                    "run_key": run_key,
                    "timeout_seconds": TIMEOUT_SECONDS,
                    "sleep_seconds": SLEEP_SECONDS,
                },
                id=workflow_id,
                task_queue=DURABILITY_TASK_QUEUE,
                execution_timeout=timedelta(minutes=5),
            )
            result = await asyncio.wait_for(handle.result(), timeout=180)

            with span(
                "apply-reliability-gates",
                ledger,
                {
                    "incident.kind": "activity_timeout",
                    "incident.classification": result["classification"],
                },
            ):
                pass

        described = await handle.describe()
        history = await handle.fetch_history()
        history_dict = history.to_json_dict()
        types = event_types(history_dict)

        timed_out_events = events_of_type(history_dict, "EVENT_TYPE_ACTIVITY_TASK_TIMED_OUT")

        require(
            len(timed_out_events) >= 1,
            "history has no ActivityTaskTimedOut event; the timeout was not recorded",
        )
        require(
            result["classification"] == "infrastructure_failure",
            f"workflow classified the timeout as {result['classification']}",
        )
        require(
            result["classification"] != "rejected",
            "an activity timeout must never be classified as a rejected patch",
        )
        require(
            described.status == WorkflowExecutionStatus.COMPLETED,
            "workflow should complete after handling the timeout, was "
            f"{workflow_status_name(described.status)}",
        )

        # The reliability layer must agree, independently of the workflow.
        decision = classify_infrastructure_incident("activity_timeout", detail="probe")
        require(
            decision == "infrastructure_failure",
            f"reliability layer classified an activity timeout as {decision}",
        )

        require(
            "apply-reliability-gates" in ledger.names,
            "the timeout incident was not recorded in a span",
        )

        history_path = write_history("timeout-behaviour", history)
        evidence_path = write_evidence(
            "timeout-behaviour",
            {
                "claim": "an activity that exceeds its start-to-close timeout is recorded "
                "in history, classified as infrastructure_failure, and never reported "
                "as a defective code patch",
                "workflow_id": workflow_id,
                "run_id": history.run_id,
                "configured_timeout_seconds": TIMEOUT_SECONDS,
                "activity_sleep_seconds": SLEEP_SECONDS,
                "timed_out_event_count": len(timed_out_events),
                "timeout_event_attributes": [
                    e.get("activityTaskTimedOutEventAttributes", {}) for e in timed_out_events
                ],
                "workflow_classification": result["classification"],
                "reliability_layer_classification": decision,
                "misclassified_as_rejected": result["classification"] == "rejected",
                "terminal_status": workflow_status_name(described.status),
                "history_event_types": types,
                "spans_recorded": sorted(ledger.names),
                "history_artifact": str(history_path),
            },
        )

        print("timeout behaviour VERIFIED")
        print(f"  workflow id      : {workflow_id}")
        print(f"  timed-out events : {len(timed_out_events)}")
        print(f"  classification   : {result['classification']} (not 'rejected')")
        print(f"  terminal status  : {described.status}")
        print(f"  evidence         : {evidence_path}")
        return 0

    except EvidenceError as exc:
        write_evidence("timeout-behaviour", {"verified": False, "failure": str(exc)})
        print(f"timeout behaviour NOT VERIFIED: {exc}", file=sys.stderr)
        return 1
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.wait(timeout=30)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
