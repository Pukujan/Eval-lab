"""Deterministic Inspect AI scorers.

Inspect owns the runner, the sample loop, metric aggregation and the log format.
What it cannot own is *what counts as correct here* — so these scorers are the
custom part, and they are deliberately thin wrappers over the same gate predicates
the workflow uses (`app.reliability.gates`).

One definition, two consumers. If the scorers restated the rules, the eval and the
workflow would drift, and the eval would eventually certify something the gates
reject.

No model is consulted by any scorer.
"""

from __future__ import annotations

from typing import Any

from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    Score,
    Target,
    accuracy,
    scorer,
)
from inspect_ai.solver import TaskState

from app.reliability.gates import (
    build_succeeds,
    hidden_tests_pass,
    no_prohibited_file_changes,
    not_symptom_suppression,
    primary_invariant_holds,
)


def _context(state: TaskState):
    """The GateContext the solver stashed on the sample's metadata."""
    return state.metadata.get("gate_context")


def _outcome(state: TaskState) -> str:
    return str(state.metadata.get("outcome", "infrastructure_failure"))


def _score(passed: bool, detail: str, extra: dict[str, Any] | None = None) -> Score:
    return Score(
        value=CORRECT if passed else INCORRECT,
        answer=detail,
        metadata=extra or {},
    )


def _infrastructure_guard(state: TaskState) -> Score | None:
    """Distinguish harness failure from agent failure.

    Scored as ``INCORRECT`` but tagged so an infrastructure problem is never read
    as evidence about the patch.
    """
    if _outcome(state) == "infrastructure_failure":
        return _score(
            False,
            "infrastructure_failure",
            {"failure_kind": "infrastructure", "counts_as_agent_failure": False},
        )
    return None


@scorer(metrics=[accuracy()])
def build_success():
    async def score(state: TaskState, target: Target) -> Score:
        if (guard := _infrastructure_guard(state)) is not None:
            return guard
        result = build_succeeds(_context(state))
        return _score(result.passed, result.detail, {"failure_kind": "agent"})

    return score


@scorer(metrics=[accuracy()])
def visible_test_success():
    async def score(state: TaskState, target: Target) -> Score:
        if (guard := _infrastructure_guard(state)) is not None:
            return guard
        context = _context(state)
        passed = context.verification.visible_tests_passed
        return _score(
            passed,
            "visible suite passed" if passed else "visible suite failed",
            {"failure_kind": "agent"},
        )

    return score


@scorer(metrics=[accuracy()])
def hidden_test_success():
    async def score(state: TaskState, target: Target) -> Score:
        if (guard := _infrastructure_guard(state)) is not None:
            return guard
        result = hidden_tests_pass(_context(state))
        return _score(result.passed, result.detail, {"failure_kind": "agent"})

    return score


@scorer(metrics=[accuracy()])
def invariant_holds():
    async def score(state: TaskState, target: Target) -> Score:
        if (guard := _infrastructure_guard(state)) is not None:
            return guard
        result = primary_invariant_holds(_context(state))
        return _score(result.passed, result.detail, {"failure_kind": "agent"})

    return score


@scorer(metrics=[accuracy()])
def prohibited_files_untouched():
    async def score(state: TaskState, target: Target) -> Score:
        if (guard := _infrastructure_guard(state)) is not None:
            return guard
        result = no_prohibited_file_changes(_context(state))
        return _score(result.passed, result.detail, {"failure_kind": "agent"})

    return score


@scorer(metrics=[accuracy()])
def prevents_duplicate_processing():
    """The scorer that separates a repair from a cover-up."""

    async def score(state: TaskState, target: Target) -> Score:
        if (guard := _infrastructure_guard(state)) is not None:
            return guard
        result = not_symptom_suppression(_context(state))
        return _score(
            result.passed,
            result.detail,
            {
                "failure_kind": "agent",
                "effect_invocation_count": _context(state).verification.effect_invocation_count,
            },
        )

    return score


@scorer(metrics=[accuracy()])
def matches_expected_outcome():
    """Whether the reliability decision matched the sample's declared target.

    The target is a *terminal state name*, so this scorer is what actually asserts
    "the duct-tape patch is rejected" and "the known-good patch is accepted for
    review, and nothing stronger".
    """

    async def score(state: TaskState, target: Target) -> Score:
        actual = _outcome(state)
        expected = target.text.strip()
        return _score(
            actual == expected,
            f"expected {expected}, got {actual}",
            {
                "expected_outcome": expected,
                "actual_outcome": actual,
                "failure_kind": (
                    "infrastructure" if actual == "infrastructure_failure" else "agent"
                ),
            },
        )

    return score
