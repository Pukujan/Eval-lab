"""Inspect AI evaluation of the walking skeleton.

Two samples, deliberately:

* ``known-good`` — the repair that establishes the invariant. Expected outcome
  ``accepted_for_review``.
* ``incorrect-patch`` — the duct-tape patch that suppresses the symptom. Expected
  outcome ``rejected``.

An eval with only the passing case proves nothing about a gate. The second sample
is the one that shows the gate can say no.

Inspect owns the runner, samples, scoring and logs. The solver here drives our own
coding workflow rather than a chat loop, which is why ``mockllm/model`` is enough
to satisfy Inspect's model requirement — nothing calls ``generate``. Our own model
calls go through the LiteLLM gateway (ADR-0004).
"""

from __future__ import annotations

import sys
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.solver import Generate, TaskState, solver

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from evals.scorers.deterministic import (  # noqa: E402
    build_success,
    hidden_test_success,
    invariant_holds,
    matches_expected_outcome,
    prevents_duplicate_processing,
    prohibited_files_untouched,
    visible_test_success,
)

SANDBOX = "local"


@solver
def run_coding_workflow():
    """Execute the walking-skeleton workflow for the sample's candidate.

    Every run gets its own temporary working copy (`app.activities.patching`), so
    samples cannot observe or disturb each other. Infrastructure failures are
    caught and recorded as such rather than being allowed to look like a wrong
    patch.
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        del generate  # this solver drives a workflow, not a chat loop

        from app.reliability.gates import DiagnosisClaim, GateContext
        from app.runner import RunRequest, run_evaluation

        candidate_id = state.metadata["candidate_id"]

        try:
            report = await run_evaluation(
                RunRequest(
                    candidate_id=candidate_id,
                    run_id=f"inspect-{state.sample_id}",
                )
            )
        except Exception as exc:  # noqa: BLE001 - harness failure, not agent failure
            state.metadata["outcome"] = "infrastructure_failure"
            state.metadata["infrastructure_detail"] = str(exc)[:500]
            return state

        verification = report.verification
        if verification is None:
            state.metadata["outcome"] = "infrastructure_failure"
            state.metadata["infrastructure_detail"] = "no verification result produced"
            return state

        diagnosis = report.investigation.get("diagnosis") or {}

        # Scorers read the same GateContext the workflow gated on — not a
        # re-derivation of it.
        state.metadata["gate_context"] = GateContext(
            verification=verification,
            diagnosis=DiagnosisClaim(
                hypothesis_id=diagnosis.get("hypothesis_id"),
                supporting_evidence_ids=frozenset(diagnosis.get("supporting_evidence_ids", [])),
                contradicting_evidence_ids=frozenset(
                    diagnosis.get("contradicting_evidence_ids", [])
                ),
                surviving_hypothesis_ids=frozenset(diagnosis.get("surviving_hypothesis_ids", [])),
            ),
            durable_execution=report.decision.durable_execution,
        )
        state.metadata["outcome"] = report.decision.outcome
        state.metadata["failed_gates"] = list(report.decision.failed_gates)
        state.metadata["execution_mode"] = str(report.run.execution_mode)
        state.metadata["trace_id"] = report.run.trace_id
        state.output.completion = report.decision.outcome
        return state

    return solve


def _samples() -> list[Sample]:
    return [
        Sample(
            id="known-good",
            input=(
                "Evaluate the repair candidate that establishes the duplicate-processing "
                "invariant via an atomic claim."
            ),
            target="accepted_for_review",
            metadata={"candidate_id": "C-claim", "kind": "known-good"},
        ),
        Sample(
            id="incorrect-patch",
            input=(
                "Evaluate the repair candidate that de-duplicates results on read "
                "without preventing duplicate processing."
            ),
            target="rejected",
            metadata={"candidate_id": "C-dedupe-read", "kind": "deliberately-incorrect"},
        ),
    ]


@task
def coding_reliability_eval() -> Task:
    """Both outcomes in one evaluation: an accepted candidate and a rejected one."""
    return Task(
        dataset=_samples(),
        solver=run_coding_workflow(),
        scorer=[
            matches_expected_outcome(),
            build_success(),
            visible_test_success(),
            hidden_test_success(),
            invariant_holds(),
            prevents_duplicate_processing(),
            prohibited_files_untouched(),
        ],
        sandbox=SANDBOX,
    )
