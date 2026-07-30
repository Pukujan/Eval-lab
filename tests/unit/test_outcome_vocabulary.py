"""Prohibited outcome vocabulary must not appear anywhere.

The brief forbids "approved", "correct", "safe", and "production_ready" as
outcomes. This test greps the tree so the constraint survives future edits by
people who did not read the brief.

It checks *outcome-shaped* usage, not any mention of the words: documentation
that says "no claim of correctness is made" is exactly the sort of sentence this
project should contain.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.domain.states import TERMINAL_STATES, WorkflowState

FORBIDDEN = ("approved", "correct", "safe", "production_ready")

#: Assignment- or comparison-shaped usage, e.g. outcome="approved" or == 'safe'.
_PATTERNS = tuple(
    re.compile(
        rf"""(outcome|decision|verdict|status|result)\s*(=|==|:)\s*["']{word}["']""",
        re.IGNORECASE,
    )
    for word in FORBIDDEN
)

SEARCH_ROOTS = ("app", "evals", "scripts")


def _python_files() -> list[Path]:
    files: list[Path] = []
    for root in SEARCH_ROOTS:
        files.extend(path for path in Path(root).rglob("*.py") if "__pycache__" not in path.parts)
    return files


def test_terminal_states_are_exactly_the_four_allowed() -> None:
    assert {state.value for state in TERMINAL_STATES} == {
        "accepted_for_review",
        "rejected",
        "abstained",
        "infrastructure_failure",
    }


def test_no_workflow_state_uses_forbidden_vocabulary() -> None:
    for state in WorkflowState:
        assert state.value not in FORBIDDEN


@pytest.mark.parametrize("path", _python_files(), ids=str)
def test_no_forbidden_outcome_assignment(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    for pattern in _PATTERNS:
        matches = [
            match.group(0)
            for match in pattern.finditer(source)
            # The vocabulary test itself and the negative-assertion lines that
            # prove the words are refused are legitimate.
            if "forbidden" not in source[max(0, match.start() - 200) : match.start()].lower()
        ]
        assert not matches, f"{path} assigns a forbidden outcome: {matches}"


def test_decision_schema_rejects_forbidden_outcomes() -> None:
    from pydantic import ValidationError

    from app.domain.schemas import GateResult, ReliabilityDecision

    for word in FORBIDDEN:
        with pytest.raises(ValidationError):
            ReliabilityDecision(
                run_id="r",
                outcome=word,
                gate_results=(GateResult(gate_name="g", passed=True, detail="d"),),
                rationale="x",
            )


def test_report_states_acceptance_means_review_only() -> None:
    from app.reliability.report import OUTCOME_MEANING

    meaning = OUTCOME_MEANING["accepted_for_review"].lower()
    assert "human reviewer" in meaning
    assert "not" in meaning
    assert "merged or deployed" in meaning
