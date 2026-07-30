"""Editing tools must not exist before the workflow reaches `implementation`.

Enforced at *acquisition*: the toolset is built from the state, so a disallowed
tool is never handed over. A model cannot be argued into using a capability it
does not have (threat model T-8).
"""

from __future__ import annotations

import pytest

from app.domain.states import PRE_IMPLEMENTATION_STATES, WorkflowState
from app.tools.broker import (
    EDITING_TOOL_NAMES,
    TOOL_CATALOGUE,
    ToolCategory,
    ToolNotAvailableError,
    acquire,
    available_tool_names,
    available_tools,
)


def test_editing_tools_are_absent_in_every_pre_implementation_state() -> None:
    for state in PRE_IMPLEMENTATION_STATES:
        granted = available_tool_names(state)
        leaked = granted & EDITING_TOOL_NAMES
        assert not leaked, f"state '{state.value}' granted editing tools: {sorted(leaked)}"


@pytest.mark.parametrize("state", sorted(PRE_IMPLEMENTATION_STATES, key=lambda s: s.value))
@pytest.mark.parametrize("tool_name", sorted(EDITING_TOOL_NAMES))
def test_acquiring_an_editing_tool_raises_before_implementation(
    state: WorkflowState, tool_name: str
) -> None:
    with pytest.raises(ToolNotAvailableError, match="implementation"):
        acquire(state, tool_name)


def test_editing_tools_become_available_at_implementation() -> None:
    for state in (WorkflowState.IMPLEMENTATION, WorkflowState.VERIFICATION):
        granted = available_tool_names(state)
        assert EDITING_TOOL_NAMES.issubset(granted), f"{state.value} should grant editing tools"
        for tool_name in EDITING_TOOL_NAMES:
            assert acquire(state, tool_name).category is ToolCategory.EDIT


def test_read_and_probe_tools_are_available_throughout_the_investigation() -> None:
    for state in PRE_IMPLEMENTATION_STATES:
        granted = available_tool_names(state)
        assert {"read_file", "list_repository", "run_probe"}.issubset(granted)


def test_editing_tools_are_absent_in_terminal_states() -> None:
    """The investigation is over; nothing should still be able to edit."""
    from app.domain.states import TERMINAL_STATES

    for state in TERMINAL_STATES:
        assert not (available_tool_names(state) & EDITING_TOOL_NAMES)


def test_unknown_tools_are_refused() -> None:
    with pytest.raises(ToolNotAvailableError, match="unknown tool"):
        acquire(WorkflowState.IMPLEMENTATION, "rm_rf_slash")


def test_gating_is_by_construction_not_by_filtering() -> None:
    """The disallowed tool is genuinely absent from the returned set."""
    granted = available_tools(WorkflowState.DIAGNOSIS)
    assert all(tool.category is not ToolCategory.EDIT for tool in granted)
    assert len(granted) < len(TOOL_CATALOGUE)
