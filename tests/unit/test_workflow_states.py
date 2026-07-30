"""Workflow-state model tests."""

from __future__ import annotations

import pytest

from app.domain.states import (
    LEGAL_TRANSITIONS,
    PRE_IMPLEMENTATION_STATES,
    TERMINAL_STATES,
    IllegalTransitionError,
    WorkflowState,
    assert_transition,
    can_transition,
    editing_permitted,
)

REQUIRED_STATES = {
    "intake",
    "specification",
    "repository_inspection",
    "hypothesis_generation",
    "probe_design",
    "probe_execution",
    "diagnosis",
    "repair_design",
    "implementation",
    "verification",
    "accepted_for_review",
    "rejected",
    "abstained",
    "infrastructure_failure",
}


def test_all_required_states_exist() -> None:
    assert {state.value for state in WorkflowState} == REQUIRED_STATES


def test_every_state_has_a_transition_entry() -> None:
    assert set(LEGAL_TRANSITIONS) == set(WorkflowState)


def test_terminal_states_go_nowhere() -> None:
    for state in TERMINAL_STATES:
        assert LEGAL_TRANSITIONS[state] == frozenset()


def test_happy_path_is_legal() -> None:
    path = [
        WorkflowState.INTAKE,
        WorkflowState.SPECIFICATION,
        WorkflowState.REPOSITORY_INSPECTION,
        WorkflowState.HYPOTHESIS_GENERATION,
        WorkflowState.PROBE_DESIGN,
        WorkflowState.PROBE_EXECUTION,
        WorkflowState.DIAGNOSIS,
        WorkflowState.REPAIR_DESIGN,
        WorkflowState.IMPLEMENTATION,
        WorkflowState.VERIFICATION,
        WorkflowState.ACCEPTED_FOR_REVIEW,
    ]
    for source, target in zip(path, path[1:], strict=False):
        assert can_transition(source, target), f"{source} -> {target} should be legal"


def test_skipping_the_investigation_is_illegal() -> None:
    """You cannot jump from intake straight to implementation."""
    with pytest.raises(IllegalTransitionError):
        assert_transition(WorkflowState.INTAKE, WorkflowState.IMPLEMENTATION)


def test_cannot_accept_without_verification() -> None:
    with pytest.raises(IllegalTransitionError):
        assert_transition(WorkflowState.IMPLEMENTATION, WorkflowState.ACCEPTED_FOR_REVIEW)


def test_every_non_terminal_state_can_abstain_or_fail_infrastructure() -> None:
    for state in WorkflowState:
        if state in TERMINAL_STATES:
            continue
        assert can_transition(state, WorkflowState.ABSTAINED)
        assert can_transition(state, WorkflowState.INFRASTRUCTURE_FAILURE)


def test_editing_is_not_permitted_before_implementation() -> None:
    for state in PRE_IMPLEMENTATION_STATES:
        assert not editing_permitted(state), f"editing must be blocked in {state}"
    assert editing_permitted(WorkflowState.IMPLEMENTATION)
    assert editing_permitted(WorkflowState.VERIFICATION)


def test_positive_outcome_is_accepted_for_review_only() -> None:
    from app.domain.states import POSITIVE_OUTCOME

    assert POSITIVE_OUTCOME is WorkflowState.ACCEPTED_FOR_REVIEW
