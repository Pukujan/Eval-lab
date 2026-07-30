"""Inspect AI evaluation smoke test.

Runs the real evaluation with `mockllm/model` — no credentials — and asserts that
**both** outcomes are recorded: the known-good sample accepted for review, and the
deliberately incorrect sample rejected.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.inspect.coding_eval import coding_reliability_eval

pytestmark = pytest.mark.integration


def test_task_declares_both_a_known_good_and_an_incorrect_sample() -> None:
    task = coding_reliability_eval()
    samples = {sample.id: sample for sample in task.dataset}

    assert set(samples) == {"known-good", "incorrect-patch"}
    assert samples["known-good"].target == "accepted_for_review"
    assert samples["incorrect-patch"].target == "rejected"
    assert samples["incorrect-patch"].metadata["kind"] == "deliberately-incorrect"


def test_task_declares_the_deterministic_scorers() -> None:
    task = coding_reliability_eval()
    names = {getattr(scorer, "__name__", str(scorer)) for scorer in task.scorer}
    assert len(task.scorer) >= 6
    del names  # names are wrapped by Inspect; the count is the meaningful check


def test_evaluation_records_both_outcomes(tmp_path: Path) -> None:
    from inspect_ai import eval as inspect_eval

    logs = inspect_eval(
        coding_reliability_eval(),
        model="mockllm/model",
        log_dir=str(tmp_path / "logs"),
        display="none",
    )

    assert len(logs) == 1
    log = logs[0]
    assert log.status == "success", f"eval did not complete: {log.status}"
    assert log.samples is not None and len(log.samples) == 2

    outcomes = {sample.id: sample.metadata.get("outcome") for sample in log.samples}
    assert outcomes["known-good"] == "accepted_for_review"
    assert outcomes["incorrect-patch"] == "rejected"


def test_evaluation_distinguishes_agent_from_infrastructure_failure(tmp_path: Path) -> None:
    """A broken harness must never be scored as a wrong patch."""
    from inspect_ai import eval as inspect_eval

    logs = inspect_eval(
        coding_reliability_eval(),
        model="mockllm/model",
        log_dir=str(tmp_path / "logs"),
        display="none",
    )
    log = logs[0]

    for sample in log.samples or []:
        assert sample.metadata.get("outcome") != "infrastructure_failure"
        for score in (sample.scores or {}).values():
            kind = (score.metadata or {}).get("failure_kind")
            if kind is not None:
                assert kind in {"agent", "infrastructure"}


def test_incorrect_patch_fails_the_duplicate_processing_scorer(tmp_path: Path) -> None:
    from inspect_ai import eval as inspect_eval

    logs = inspect_eval(
        coding_reliability_eval(),
        model="mockllm/model",
        log_dir=str(tmp_path / "logs"),
        display="none",
    )
    samples = {sample.id: sample for sample in (logs[0].samples or [])}

    incorrect = samples["incorrect-patch"]
    duplicate_scores = [
        score for name, score in (incorrect.scores or {}).items() if "duplicate" in name.lower()
    ]
    assert duplicate_scores, "no duplicate-processing scorer recorded"
    assert all(score.value == "I" for score in duplicate_scores)
    assert any(
        (score.metadata or {}).get("effect_invocation_count") == 2 for score in duplicate_scores
    )


def test_scorers_reuse_the_workflow_gate_predicates() -> None:
    """One definition, two consumers — otherwise the eval and the gates drift."""
    source = Path("evals/scorers/deterministic.py").read_text(encoding="utf-8")
    assert "from app.reliability.gates import" in source
    for predicate in ("hidden_tests_pass", "primary_invariant_holds", "not_symptom_suppression"):
        assert predicate in source
