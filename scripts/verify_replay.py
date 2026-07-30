"""Replay / determinism verification using the SDK's supported Replayer.

Two halves, and the second is the one that gives the first any weight:

1. **Positive** — replay a real recorded history against the workflow that
   produced it. Must succeed.
2. **Negative** — replay the same history against a deliberately incompatible
   variation registered under the same workflow name. Must **fail** with a
   nondeterminism error.

A replay check that can only pass proves nothing about its ability to detect
nondeterministic workflow evolution, which is the entire reason to run one.

Uses :class:`temporalio.worker.Replayer` and
:meth:`temporalio.client.WorkflowHistory.from_json` — the officially supported
facilities for the pinned SDK. No custom history parser.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from app.evidence.artifacts import (  # noqa: E402
    EvidenceError,
    evidence_directory,
    require,
    write_evidence,
)
from app.workflows.durability import DurableCheckpointWorkflow  # noqa: E402
from app.workflows.replay_variants import IncompatibleDurableCheckpointWorkflow  # noqa: E402


def load_history(name: str):
    """Load a preserved history artifact written by an earlier verification."""
    from temporalio.client import WorkflowHistory

    path = evidence_directory() / f"{name}.history.json"
    if not path.is_file():
        raise EvidenceError(
            f"no preserved history at {path}; run scripts/verify_durability.py first"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    workflow_id = (
        payload.get("events", [{}])[0]
        .get("workflowExecutionStartedEventAttributes", {})
        .get("workflowId")
        or "durable-checkpoint-replay"
    )
    return WorkflowHistory.from_json(workflow_id, payload), path


async def main() -> int:
    from temporalio.worker import Replayer

    try:
        history, history_path = load_history("durability-recovery")

        # -- 1. positive: the workflow that wrote this history replays cleanly --
        replayer = Replayer(workflows=[DurableCheckpointWorkflow])
        positive_error: str | None = None
        try:
            await replayer.replay_workflow(history, raise_on_replay_failure=True)
            positive_ok = True
        except Exception as exc:  # noqa: BLE001 - any failure is a failed claim
            positive_ok = False
            positive_error = f"{type(exc).__name__}: {exc}"

        require(
            positive_ok,
            f"replaying a real history against its own workflow failed: {positive_error}",
        )

        # -- 2. negative: an incompatible variation must be detected -----------
        incompatible_replayer = Replayer(workflows=[IncompatibleDurableCheckpointWorkflow])
        detected = False
        detection_error = ""
        try:
            await incompatible_replayer.replay_workflow(history, raise_on_replay_failure=True)
        except Exception as exc:  # noqa: BLE001 - detection is the success path here
            detected = True
            detection_error = f"{type(exc).__name__}: {str(exc)[:400]}"

        require(
            detected,
            "replaying an incompatible workflow variation SUCCEEDED — the determinism "
            "check cannot detect nondeterministic workflow evolution and is worthless",
        )

        evidence_path = write_evidence(
            "replay-determinism",
            {
                "claim": "the SDK replayer accepts the workflow that produced a real "
                "history and rejects a deliberately incompatible variation of it",
                "facility": "temporalio.worker.Replayer (officially supported)",
                "history_artifact": str(history_path),
                "history_workflow_id": history.workflow_id,
                "history_run_id": history.run_id,
                "history_event_count": len(history.events),
                "positive_replay": {
                    "workflow": "app.workflows.durability.DurableCheckpointWorkflow",
                    "passed": positive_ok,
                },
                "negative_replay": {
                    "workflow": "app.workflows.replay_variants."
                    "IncompatibleDurableCheckpointWorkflow",
                    "registered_as": "DurableCheckpointWorkflow",
                    "variation": "commits the terminal effect before the checkpoint and "
                    "never waits for the resume signal",
                    "detected_nondeterminism": detected,
                    "error": detection_error,
                },
            },
        )

        print("replay / determinism VERIFIED")
        print(f"  history          : {history_path.name} ({len(history.events)} events)")
        print(f"  workflow id      : {history.workflow_id}")
        print("  positive replay  : PASSED (genuine workflow replays cleanly)")
        print(f"  negative replay  : DETECTED -> {detection_error[:120]}")
        print(f"  evidence         : {evidence_path}")
        return 0

    except EvidenceError as exc:
        write_evidence("replay-determinism", {"verified": False, "failure": str(exc)})
        print(f"replay / determinism NOT VERIFIED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
