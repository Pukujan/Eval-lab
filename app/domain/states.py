"""The explicit workflow state model.

Fourteen states, a legal-transition table, and the rule that editing tools do not
exist before ``implementation``.

Two design points worth stating, because both are easy to get subtly wrong:

* An illegal transition **raises**. A state machine that logs a warning and
  proceeds is not a state machine; it is a suggestion.
* ``INFRASTRUCTURE_FAILURE`` is a terminal state distinct from ``REJECTED``. A
  harness that breaks must never be reported as a patch that failed — conflating
  the two is how an evaluation lab quietly manufactures false negatives.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class WorkflowState(StrEnum):
    """Every state the coding-evaluation workflow can occupy."""

    INTAKE = "intake"
    SPECIFICATION = "specification"
    REPOSITORY_INSPECTION = "repository_inspection"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    PROBE_DESIGN = "probe_design"
    PROBE_EXECUTION = "probe_execution"
    DIAGNOSIS = "diagnosis"
    REPAIR_DESIGN = "repair_design"
    IMPLEMENTATION = "implementation"
    VERIFICATION = "verification"
    ACCEPTED_FOR_REVIEW = "accepted_for_review"
    REJECTED = "rejected"
    ABSTAINED = "abstained"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"


#: The only positive outcome this system can produce. Deliberately not
#: "approved", "correct", "safe", or "production_ready" — the system is
#: uncalibrated and a human still has to look.
POSITIVE_OUTCOME: Final = WorkflowState.ACCEPTED_FOR_REVIEW

TERMINAL_STATES: Final[frozenset[WorkflowState]] = frozenset(
    {
        WorkflowState.ACCEPTED_FOR_REVIEW,
        WorkflowState.REJECTED,
        WorkflowState.ABSTAINED,
        WorkflowState.INFRASTRUCTURE_FAILURE,
    }
)

#: States in which the investigation has not yet earned the right to edit code.
PRE_IMPLEMENTATION_STATES: Final[frozenset[WorkflowState]] = frozenset(
    {
        WorkflowState.INTAKE,
        WorkflowState.SPECIFICATION,
        WorkflowState.REPOSITORY_INSPECTION,
        WorkflowState.HYPOTHESIS_GENERATION,
        WorkflowState.PROBE_DESIGN,
        WorkflowState.PROBE_EXECUTION,
        WorkflowState.DIAGNOSIS,
        WorkflowState.REPAIR_DESIGN,
    }
)


def _abortable(*extra: WorkflowState) -> frozenset[WorkflowState]:
    """Every non-terminal state may abstain or hit an infrastructure failure."""
    return frozenset({WorkflowState.ABSTAINED, WorkflowState.INFRASTRUCTURE_FAILURE, *extra})


#: The legal transition table. Anything absent is illegal.
LEGAL_TRANSITIONS: Final[dict[WorkflowState, frozenset[WorkflowState]]] = {
    WorkflowState.INTAKE: _abortable(WorkflowState.SPECIFICATION),
    WorkflowState.SPECIFICATION: _abortable(
        WorkflowState.REPOSITORY_INSPECTION, WorkflowState.REJECTED
    ),
    WorkflowState.REPOSITORY_INSPECTION: _abortable(WorkflowState.HYPOTHESIS_GENERATION),
    WorkflowState.HYPOTHESIS_GENERATION: _abortable(WorkflowState.PROBE_DESIGN),
    WorkflowState.PROBE_DESIGN: _abortable(WorkflowState.PROBE_EXECUTION),
    WorkflowState.PROBE_EXECUTION: _abortable(WorkflowState.DIAGNOSIS),
    WorkflowState.DIAGNOSIS: _abortable(WorkflowState.REPAIR_DESIGN),
    WorkflowState.REPAIR_DESIGN: _abortable(WorkflowState.IMPLEMENTATION),
    WorkflowState.IMPLEMENTATION: _abortable(WorkflowState.VERIFICATION, WorkflowState.REJECTED),
    WorkflowState.VERIFICATION: _abortable(
        WorkflowState.ACCEPTED_FOR_REVIEW, WorkflowState.REJECTED
    ),
    # Terminal states go nowhere.
    WorkflowState.ACCEPTED_FOR_REVIEW: frozenset(),
    WorkflowState.REJECTED: frozenset(),
    WorkflowState.ABSTAINED: frozenset(),
    WorkflowState.INFRASTRUCTURE_FAILURE: frozenset(),
}


class IllegalTransitionError(RuntimeError):
    """Raised when a transition is not in :data:`LEGAL_TRANSITIONS`."""


def can_transition(source: WorkflowState, target: WorkflowState) -> bool:
    """Whether ``source -> target`` is a legal transition."""
    return target in LEGAL_TRANSITIONS[source]


def assert_transition(source: WorkflowState, target: WorkflowState) -> WorkflowState:
    """Return ``target``, or raise :class:`IllegalTransitionError`."""
    if not can_transition(source, target):
        allowed = ", ".join(sorted(s.value for s in LEGAL_TRANSITIONS[source])) or "(none)"
        raise IllegalTransitionError(
            f"illegal transition {source.value} -> {target.value}; allowed: {allowed}"
        )
    return target


def editing_permitted(state: WorkflowState) -> bool:
    """Whether code-editing / patch-application tools may exist in this state.

    Permitted only from ``implementation`` onward. This is consulted by
    :mod:`app.tools.broker` when it *builds* the toolset, so a disallowed tool is
    never handed over in the first place — a model cannot be argued into using a
    tool it does not have.
    """
    return state not in PRE_IMPLEMENTATION_STATES and state not in TERMINAL_STATES
