"""Every callable that executes in Temporal workflow context must be a coroutine.

The failure this guards against does not look like a bug. LangGraph runs a
*synchronous* callable by handing it to
``langchain_core.runnables.config.run_in_executor``, which calls
``asyncio.get_running_loop().run_in_executor(...)``. Temporal's deterministic
workflow event loop has no executor and raises ``NotImplementedError``; the
workflow task fails, Temporal retries it forever, and the run simply never
finishes. CI run 30573185257 spent ten minutes in exactly that state before
hitting a timeout, having reported nothing wrong.

The trap is the **conditional-edge routing callbacks**. They are not nodes, they
carry no ``execute_in`` metadata, and nothing at their registration site suggests
they run inside the workflow — so a reviewer checking "are the workflow nodes
async?" would pass a graph that still deadlocks. This file therefore asserts over
routing callbacks as well as nodes.

Activity nodes are deliberately exempt: the Temporal LangGraph plugin executes
them as Activities, outside the workflow sandbox, where a synchronous callable is
fine. Converting them for consistency would be churn without a reason.
"""

from __future__ import annotations

import inspect

import pytest

from app.graphs.investigation import (
    _route_after_diagnosis,
    _route_after_validation,
    abstain,
    build_investigation_graph,
    establish_diagnosis,
    validate_specification,
)

#: Nodes registered with ``execute_in="workflow"``.
WORKFLOW_NODE_NAMES = frozenset({"validate_specification", "establish_diagnosis", "abstain"})

#: Conditional-edge callbacks. Not nodes; still workflow context.
ROUTING_CALLBACKS = {
    "_route_after_validation": _route_after_validation,
    "_route_after_diagnosis": _route_after_diagnosis,
}

WORKFLOW_CALLABLES = {
    "validate_specification": validate_specification,
    "establish_diagnosis": establish_diagnosis,
    "abstain": abstain,
    **ROUTING_CALLBACKS,
}


@pytest.mark.parametrize("name", sorted(WORKFLOW_CALLABLES))
def test_workflow_context_callable_is_a_coroutine_function(name: str) -> None:
    target = WORKFLOW_CALLABLES[name]
    assert inspect.iscoroutinefunction(target), (
        f"'{name}' runs in Temporal workflow context and must be `async def`. "
        "A synchronous callable is offloaded via run_in_executor(), which the "
        "deterministic workflow event loop cannot provide (NotImplementedError), "
        "and the workflow then retries forever instead of failing."
    )


@pytest.mark.parametrize("name", sorted(ROUTING_CALLBACKS))
def test_routing_callbacks_specifically_are_coroutines(name: str) -> None:
    """Called out separately because routing callbacks are the easy ones to miss."""
    assert inspect.iscoroutinefunction(ROUTING_CALLBACKS[name])


def test_every_workflow_bound_graph_node_is_a_coroutine() -> None:
    """Walk the compiled graph rather than trusting the list above.

    A node added later with ``execute_in="workflow"`` is caught here even if
    nobody remembers to extend this module.
    """
    graph = build_investigation_graph()
    offenders: list[str] = []

    for name, node in graph.nodes.items():
        metadata = node.metadata or {}
        if metadata.get("execute_in") != "workflow":
            continue
        runnable = getattr(node, "runnable", None)
        target = getattr(runnable, "func", None) or getattr(runnable, "afunc", None) or runnable
        if not inspect.iscoroutinefunction(target):
            offenders.append(name)

    assert not offenders, (
        f"workflow-bound nodes are not coroutine functions: {offenders}. "
        "They will be offloaded through run_in_executor() and hang the workflow."
    )


def test_the_workflow_node_set_is_what_we_think_it_is() -> None:
    """Guards the exemption below: if a node moves to workflow context, notice."""
    graph = build_investigation_graph()
    workflow_nodes = {
        name
        for name, node in graph.nodes.items()
        if (node.metadata or {}).get("execute_in") == "workflow"
    }
    assert workflow_nodes == WORKFLOW_NODE_NAMES


def test_activity_nodes_are_not_required_to_be_async() -> None:
    """The exemption, asserted so it stays a decision rather than an accident.

    Activity-bound nodes run outside the workflow sandbox, where a synchronous
    callable never reaches the executor path.
    """
    graph = build_investigation_graph()
    activity_nodes = {
        name
        for name, node in graph.nodes.items()
        if (node.metadata or {}).get("execute_in") == "activity"
    }
    assert activity_nodes, "expected at least one activity-bound node"
    assert not (activity_nodes & WORKFLOW_NODE_NAMES)


async def test_converted_callables_preserve_their_return_values() -> None:
    """Behaviour must be unchanged by the async conversion."""
    valid = {
        "specification": {
            "repository_path": "/tmp/repo",
            "expected_behaviour": "no duplicates",
            "invariants": [{"invariant_id": "INV-1"}],
        }
    }
    assert await validate_specification(valid) == {"span_names": ["validate-specification"]}

    invalid = await validate_specification({"specification": {"repository_path": ""}})
    assert invalid["abstained"] is True
    assert "repository path" in invalid["abstention_reason"]

    abstained = await abstain({"abstention_reason": "because"})
    assert abstained == {"abstained": True, "abstention_reason": "because"}


async def test_converted_routing_preserves_its_decisions() -> None:
    assert await _route_after_validation({"abstained": True}) == "abstain"
    assert await _route_after_validation({}) == "inspect_repository"
    assert await _route_after_diagnosis({"abstained": True}) == "abstain"
    assert await _route_after_diagnosis({}) == "generate_repair_candidates"


async def test_converted_diagnosis_preserves_its_selection() -> None:
    result = await establish_diagnosis(
        {
            "hypotheses": [
                {"hypothesis_id": "H-untested", "mechanism_class": "a"},
                {"hypothesis_id": "H-supported", "mechanism_class": "b"},
            ],
            "probe_results": [
                {"hypothesis_id": "H-supported", "outcome": "supported", "evidence_ids": ["E-1"]},
            ],
        }
    )
    assert result["diagnosis"]["hypothesis_id"] == "H-supported"
    assert result["diagnosis"]["probe_supported"] is True
    assert result["span_names"] == ["establish-diagnosis"]


# ---------------------------------------------------------------------------
# A second, unrelated trap found by the same CI run
# ---------------------------------------------------------------------------


def test_workflow_status_is_never_asserted_by_string_formatting() -> None:
    """``WorkflowExecutionStatus`` is an IntEnum: ``str(status)`` is ``"2"``.

    Run 30577856007 reported "terminal status was 2" for a workflow that had
    completed perfectly — the verification, not the workflow, was wrong. Any
    ``str(status).endswith("COMPLETED")`` is dead code that can only ever fail,
    so this scans the verification scripts for the pattern.
    """
    import re
    from pathlib import Path

    pattern = re.compile(r"str\([a-z_]*\.?status\)\.endswith")
    offenders = [
        str(path)
        for path in Path("scripts").glob("verify_*.py")
        if pattern.search(path.read_text(encoding="utf-8"))
    ]
    assert not offenders, (
        f"{offenders} compare a workflow status by string. WorkflowExecutionStatus "
        "is an IntEnum, so str() yields its number and the check can never pass. "
        "Compare against the enum member and render with workflow_status_name()."
    )


def test_workflow_status_name_renders_the_readable_name() -> None:
    from temporalio.client import WorkflowExecutionStatus

    from app.evidence.artifacts import workflow_status_name

    assert workflow_status_name(WorkflowExecutionStatus.COMPLETED) == "COMPLETED"
    assert workflow_status_name(WorkflowExecutionStatus.RUNNING) == "RUNNING"
    assert str(WorkflowExecutionStatus.COMPLETED) == "2", (
        "if this ever stops being true the trap is gone and the guard above can go"
    )
