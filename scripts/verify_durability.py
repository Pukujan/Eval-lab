"""Worker-interruption recovery, proved against real Temporal history.

Sequence:

1. start worker A as a subprocess;
2. start ``DurableCheckpointWorkflow``; it records a durable checkpoint effect and
   then blocks on a signal;
3. **SIGKILL worker A** — abrupt, no graceful drain;
4. confirm the workflow does not progress while no worker is polling;
5. start worker B;
6. signal it to resume; the workflow completes under the new worker;
7. assert the checkpoint effect was **not** repeated.

The last point is the one that matters: activity results live in workflow history,
so worker B replays the checkpoint's *result* instead of re-running the work. One
row in the effect ledger, not two.

Exits non-zero on any unproved claim. Writes evidence + the full history.
"""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import time
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
    DurableCheckpointWorkflow,
    effect_count,
    effect_rows,
)

WORKER_START_TIMEOUT = 60.0
CHECKPOINT_TIMEOUT = 60.0


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
    deadline = time.monotonic() + WORKER_START_TIMEOUT
    while time.monotonic() < deadline:
        if marker.is_file():
            return process
        if process.poll() is not None:
            raise EvidenceError(
                f"worker {identity} exited before polling (rc={process.returncode})"
            )
        time.sleep(0.5)
    process.kill()
    raise EvidenceError(f"worker {identity} did not start polling within {WORKER_START_TIMEOUT}s")


def kill_worker(process: subprocess.Popen) -> int:
    """SIGKILL and reap. Returns the exit status actually observed."""
    if process.poll() is not None:
        return int(process.returncode)
    process.send_signal(signal.SIGKILL)
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:  # pragma: no cover
        process.terminate()
        process.wait(timeout=10)
    return int(process.returncode)


async def main() -> int:
    from temporalio.client import Client, WorkflowExecutionStatus

    settings = load_settings()
    settings.ensure_directories()

    run_key = f"durability-{int(time.time())}"
    workflow_id = f"durable-checkpoint-{run_key}"
    ledger_path = str(settings.var_dir / "durability-ledger.db")
    marker_a = settings.var_dir / "worker-a.marker"
    marker_b = settings.var_dir / "worker-b.marker"

    params = {
        "run_key": run_key,
        "ledger_path": ledger_path,
        "resume_timeout": 300,
    }

    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)

    worker_a = start_worker("durability-worker-a", marker_a)
    worker_a_pid = worker_a.pid
    worker_b = None

    try:
        handle = await client.start_workflow(
            DurableCheckpointWorkflow.run,
            params,
            id=workflow_id,
            task_queue=DURABILITY_TASK_QUEUE,
            execution_timeout=__import__("datetime").timedelta(minutes=10),
        )

        # Wait for the checkpoint activity to complete under worker A.
        deadline = time.monotonic() + CHECKPOINT_TIMEOUT
        checkpointed = False
        while time.monotonic() < deadline:
            if await handle.query(DurableCheckpointWorkflow.checkpoint_recorded):
                checkpointed = True
                break
            await asyncio.sleep(0.5)
        require(checkpointed, "checkpoint activity did not complete under the first worker")

        effects_after_checkpoint = effect_count(ledger_path, run_key, "checkpoint")
        require(
            effects_after_checkpoint == 1,
            "expected exactly 1 checkpoint effect before interruption, got "
            f"{effects_after_checkpoint}",
        )

        # -- interrupt -------------------------------------------------------
        worker_a_status = kill_worker(worker_a)
        require(worker_a.poll() is not None, "worker A was still running after SIGKILL")

        # The workflow must still be open with no worker polling.
        described = await handle.describe()
        require(
            described.status == WorkflowExecutionStatus.RUNNING,
            "workflow should still be RUNNING while no worker polls, was "
            f"{workflow_status_name(described.status)}",
        )

        # -- resume under a new worker ---------------------------------------
        worker_b = start_worker("durability-worker-b", marker_b)
        await handle.signal(DurableCheckpointWorkflow.resume)
        result = await asyncio.wait_for(handle.result(), timeout=180)

        described_final = await handle.describe()
        history = await handle.fetch_history()
        history_dict = history.to_json_dict()
        types = event_types(history_dict)

        checkpoint_effects = effect_count(ledger_path, run_key, "checkpoint")
        terminal_effects = effect_count(ledger_path, run_key, "terminal")

        # -- the claims ------------------------------------------------------
        require(bool(handle.result_run_id or handle.first_execution_run_id), "no run id recorded")
        require(len(types) > 0, "workflow history is empty")
        require(
            "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED" in types,
            "history has no WorkflowExecutionStarted event",
        )
        require(
            "EVENT_TYPE_WORKFLOW_EXECUTION_COMPLETED" in types,
            "history has no WorkflowExecutionCompleted event",
        )
        require(
            len(events_of_type(history_dict, "EVENT_TYPE_ACTIVITY_TASK_COMPLETED")) == 2,
            "expected exactly two completed activities in history",
        )
        require(
            described_final.status == WorkflowExecutionStatus.COMPLETED,
            f"workflow did not reach COMPLETED, was {workflow_status_name(described_final.status)}",
        )
        require(
            checkpoint_effects == 1,
            f"checkpoint effect was repeated after recovery: {checkpoint_effects} rows",
        )
        require(terminal_effects == 1, f"terminal effect count was {terminal_effects}, expected 1")

        rows = effect_rows(ledger_path, run_key)

        history_path = write_history("durability-recovery", history)
        evidence_path = write_evidence(
            "durability-recovery",
            {
                "claim": "a Temporal workflow survives an abrupt worker loss and resumes "
                "under a new worker without repeating a committed external effect",
                "workflow_id": workflow_id,
                "run_id": history.run_id,
                "temporal_address": settings.temporal_address,
                "namespace": settings.temporal_namespace,
                "task_queue": DURABILITY_TASK_QUEUE,
                "history_event_count": len(types),
                "history_event_types": types,
                "terminal_status": workflow_status_name(described_final.status),
                "first_worker": {
                    "identity": "durability-worker-a",
                    "pid": worker_a_pid,
                    "killed_with": "SIGKILL",
                    "exit_status": worker_a_status,
                    "confirmed_stopped": True,
                },
                "second_worker": {"identity": "durability-worker-b", "pid": worker_b.pid},
                "effect_ledger": rows,
                "checkpoint_effect_count": checkpoint_effects,
                "terminal_effect_count": terminal_effects,
                "invariant": "one logical checkpoint produced at most one committed effect",
                "invariant_holds": checkpoint_effects == 1,
                "workflow_result": result,
                "history_artifact": str(history_path),
            },
        )

        print("durability recovery VERIFIED")
        print(f"  workflow id      : {workflow_id}")
        print(f"  run id           : {history.run_id}")
        print(f"  history events   : {len(types)}")
        print(f"  worker A         : pid {worker_a_pid} SIGKILLed, exit {worker_a_status}")
        print(f"  worker B         : pid {worker_b.pid} resumed the workflow")
        print(f"  checkpoint effects: {checkpoint_effects} (must be 1)")
        print(f"  terminal status  : {described_final.status}")
        print(f"  evidence         : {evidence_path}")
        return 0

    except EvidenceError as exc:
        write_evidence("durability-recovery", {"verified": False, "failure": str(exc)})
        print(f"durability recovery NOT VERIFIED: {exc}", file=sys.stderr)
        return 1
    finally:
        for process in (worker_a, worker_b):
            if process is not None and process.poll() is None:
                kill_worker(process)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
