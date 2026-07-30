"""Bounded real-Temporal smoke test of ``CodingEvaluationWorkflow``.

This exists because the full demo is a poor detector. When a workflow task fails,
Temporal retries it forever, so a structurally broken workflow presents as a slow
one and only surfaces at the execution timeout — ten minutes of CI spent learning
nothing (run 30573185257).

So this runs the *smallest* execution that still crosses every structural feature
that failure touched:

* the workflow starts on a real server;
* the **validation conditional edge** is crossed (a sync route callback dies here);
* at least one **activity node** executes;
* the **diagnosis conditional edge** is crossed;
* the workflow reaches a terminal state;
* its history is non-empty.

It is bounded twice over — a short workflow execution timeout and a short client
wait — so a regression fails in under a minute with a diagnosis instead of hanging.

Usage:  python scripts/verify_workflow_smoke.py [--timeout SECONDS]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from datetime import timedelta
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from app.activities.patching import create_working_copy  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.domain.fixtures import build_problem_specification  # noqa: E402
from app.evidence.artifacts import (  # noqa: E402
    EvidenceError,
    event_types,
    events_of_type,
    require,
    write_evidence,
    write_history,
)
from app.workflows.coding_evaluation import (  # noqa: E402
    CodingEvaluationWorkflow,
    build_plugin,
    run_scoped_task_queue,
)

#: Deliberately short. A workflow that cannot make progress must fail fast.
DEFAULT_TIMEOUT_SECONDS = 240


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args()

    from temporalio.client import Client
    from temporalio.worker import Worker

    settings = load_settings()
    settings.ensure_directories()

    run_id = f"smoke-{int(time.time())}"
    workflow_id = f"coding-evaluation-{run_id}"
    specification = build_problem_specification()
    working_copy = create_working_copy(destination_root=settings.working_copies)

    started = time.monotonic()
    try:
        client = await Client.connect(
            settings.temporal_address, namespace=settings.temporal_namespace
        )
        task_queue = run_scoped_task_queue(settings, run_id)

        state = {
            "run_id": run_id,
            "solver_pseudonym": "model-5m0ke123",
            "solver_model": "mock-analyst",
            "specification": specification.model_dump(mode="json"),
            "working_copy_path": str(working_copy.path),
        }

        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[CodingEvaluationWorkflow],
            plugins=[build_plugin()],
        ):
            handle = await client.start_workflow(
                CodingEvaluationWorkflow.run,
                state,
                id=workflow_id,
                task_queue=task_queue,
                execution_timeout=timedelta(seconds=args.timeout),
            )
            try:
                result = await asyncio.wait_for(handle.result(), timeout=args.timeout)
            except TimeoutError as exc:
                raise EvidenceError(
                    f"workflow {workflow_id} did not complete within {args.timeout}s. "
                    "A workflow task that keeps failing is retried indefinitely, so "
                    "this is the shape a structural workflow error takes — check the "
                    "worker log for NotImplementedError from run_in_executor()."
                ) from exc

            described = await handle.describe()
            history = await handle.fetch_history()

        elapsed = round(time.monotonic() - started, 2)
        history_dict = history.to_json_dict()
        types = event_types(history_dict)

        # -- the structural claims -------------------------------------------
        require(len(history.events) > 0, "workflow history is empty")
        require(
            "EVENT_TYPE_WORKFLOW_EXECUTION_COMPLETED" in types,
            f"workflow did not complete; terminal events were {types[-3:]}",
        )
        require(
            str(described.status).endswith("COMPLETED"),
            f"terminal status was {described.status}",
        )

        activity_completions = events_of_type(history_dict, "EVENT_TYPE_ACTIVITY_TASK_COMPLETED")
        require(
            len(activity_completions) >= 1,
            "no activity node executed; the graph never got past workflow-local nodes",
        )

        span_names = result.get("span_names", [])

        # Crossing the validation edge is what the sync route callback broke.
        require(
            "validate-specification" in span_names,
            "the validation node did not run",
        )
        require(
            "inspect-repository" in span_names,
            "the validation conditional edge was not crossed into the activity branch",
        )
        require(
            "establish-diagnosis" in span_names,
            "the diagnosis node did not run",
        )
        require(
            "generate-repair-candidates" in span_names,
            "the diagnosis conditional edge was not crossed into the repair branch",
        )
        require(
            not result.get("abstained"),
            f"the investigation abstained: {result.get('abstention_reason')}",
        )

        history_path = write_history("workflow-smoke", history)
        evidence_path = write_evidence(
            "workflow-smoke",
            {
                "claim": "CodingEvaluationWorkflow executes on a real Temporal server, "
                "crosses both conditional edges, runs activity nodes, and completes "
                "with a non-empty history",
                "workflow_id": workflow_id,
                "run_id": history.run_id,
                "task_queue": task_queue,
                "temporal_address": settings.temporal_address,
                "elapsed_seconds": elapsed,
                "bound_seconds": args.timeout,
                "history_event_count": len(history.events),
                "activity_task_completed_events": len(activity_completions),
                "graph_phases_reached": span_names,
                "validation_edge_crossed": "inspect-repository" in span_names,
                "diagnosis_edge_crossed": "generate-repair-candidates" in span_names,
                "terminal_status": str(described.status),
                "history_artifact": str(history_path),
                "verified": True,
            },
        )

        print("workflow smoke VERIFIED")
        print(f"  workflow id       : {workflow_id}")
        print(f"  run id            : {history.run_id}")
        print(f"  elapsed           : {elapsed}s (bound {args.timeout}s)")
        print(f"  history events    : {len(history.events)}")
        print(f"  activities done   : {len(activity_completions)}")
        print(f"  phases reached    : {', '.join(span_names)}")
        print(f"  evidence          : {evidence_path}")
        return 0

    except EvidenceError as exc:
        write_evidence("workflow-smoke", {"verified": False, "failure": str(exc)})
        print(f"workflow smoke NOT VERIFIED: {exc}", file=sys.stderr)
        return 1
    finally:
        working_copy.cleanup()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
