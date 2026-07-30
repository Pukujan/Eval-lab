"""State-gated tool availability.

The rule the brief demands: *editing or patch-application tools must be
unavailable before the workflow reaches ``implementation``*.

The important design choice is **where** that is enforced. Telling a model "do not
edit files yet" is a request, and a request is negotiable. Building the toolset
from the current state means a disallowed tool is never handed over, so there is
nothing to negotiate with — the capability simply does not exist yet.

That is why :func:`available_tools` derives from state rather than filtering a
fixed list at call time, and why :func:`acquire` raises instead of returning a
tool that refuses.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain.states import WorkflowState, editing_permitted


class ToolCategory(StrEnum):
    READ = "read"
    ANALYSE = "analyse"
    PROBE = "probe"
    EDIT = "edit"


class ToolNotAvailableError(RuntimeError):
    """Raised when a tool is requested in a state that does not grant it."""


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    category: ToolCategory
    description: str


#: Every tool the investigation can ever use. Editing tools are declared here but
#: only *granted* from `implementation` onward.
TOOL_CATALOGUE: tuple[ToolDefinition, ...] = (
    ToolDefinition("read_file", ToolCategory.READ, "Read a solver-visible file."),
    ToolDefinition("list_repository", ToolCategory.READ, "List solver-visible paths."),
    ToolDefinition("search_repository", ToolCategory.READ, "Search solver-visible files."),
    ToolDefinition("run_probe", ToolCategory.PROBE, "Execute a deterministic probe."),
    ToolDefinition("record_evidence", ToolCategory.ANALYSE, "Persist an evidence record."),
    ToolDefinition("apply_patch", ToolCategory.EDIT, "Apply a patch to a working copy."),
    ToolDefinition("write_file", ToolCategory.EDIT, "Write file contents in a working copy."),
    ToolDefinition("revert_patch", ToolCategory.EDIT, "Revert an applied patch."),
)

EDITING_TOOL_NAMES: frozenset[str] = frozenset(
    tool.name for tool in TOOL_CATALOGUE if tool.category is ToolCategory.EDIT
)


def available_tools(state: WorkflowState) -> tuple[ToolDefinition, ...]:
    """The toolset granted in ``state``.

    Editing tools are absent — not disabled, absent — before ``implementation``.
    """
    if editing_permitted(state):
        return TOOL_CATALOGUE
    return tuple(tool for tool in TOOL_CATALOGUE if tool.category is not ToolCategory.EDIT)


def available_tool_names(state: WorkflowState) -> frozenset[str]:
    return frozenset(tool.name for tool in available_tools(state))


def acquire(state: WorkflowState, tool_name: str) -> ToolDefinition:
    """Return the tool, or raise :class:`ToolNotAvailableError`."""
    for tool in available_tools(state):
        if tool.name == tool_name:
            return tool

    known = {tool.name for tool in TOOL_CATALOGUE}
    if tool_name in known:
        raise ToolNotAvailableError(
            f"tool '{tool_name}' is not available in state '{state.value}'; "
            "editing and patch-application tools are granted only from "
            "'implementation' onward"
        )
    raise ToolNotAvailableError(f"unknown tool '{tool_name}'")
