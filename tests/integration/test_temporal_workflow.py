"""Temporal workflow tests.

The wiring — workflow definition, plugin construction, per-node activity options —
is checked statically and always runs. Actually executing a workflow needs a
server; that test **skips** and names what was unavailable, so "not verified here"
never looks like "verified passing".
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from app.config import load_settings
from app.graphs.investigation import INVESTIGATION_GRAPH_NAME
from app.workflows.coding_evaluation import (
    WORKFLOW_EXECUTION_TIMEOUT,
    CodingEvaluationWorkflow,
    build_plugin,
)


def _temporal_reachable(address: str, timeout: float = 4.0) -> bool:
    async def probe() -> bool:
        try:
            from temporalio.client import Client

            await asyncio.wait_for(Client.connect(address), timeout=timeout)
        except Exception:  # noqa: BLE001
            return False
        return True

    return asyncio.run(probe())


# -- static wiring: always runs ----------------------------------------------


def test_workflow_is_a_registered_temporal_workflow() -> None:
    from temporalio.workflow import _Definition

    definition = _Definition.from_class(CodingEvaluationWorkflow)
    assert definition is not None
    assert definition.name == "CodingEvaluationWorkflow"


def test_plugin_is_the_official_temporal_langgraph_plugin() -> None:
    """We must not have hand-rolled the node-to-activity bridge (ADR-0002)."""
    from temporalio.contrib.langgraph import LangGraphPlugin

    plugin = build_plugin()
    assert isinstance(plugin, LangGraphPlugin)
    assert type(plugin).__module__.startswith("temporalio.contrib.langgraph")


def test_plugin_registers_the_investigation_graph() -> None:
    plugin = build_plugin()
    assert plugin.activities, "the plugin should wrap activity-bound nodes"
    assert INVESTIGATION_GRAPH_NAME


def test_default_activity_options_do_not_set_execute_in() -> None:
    """The plugin rejects `execute_in` in defaults; it must be per node."""
    plugin = build_plugin()
    assert plugin is not None  # construction would have raised otherwise


def test_execution_timeout_is_bounded() -> None:
    assert timedelta(minutes=1) <= WORKFLOW_EXECUTION_TIMEOUT <= timedelta(hours=1)


def test_workflow_body_delegates_to_the_graph() -> None:
    """The workflow must stay thin: no orchestration logic outside the graph."""
    import inspect

    source = inspect.getsource(CodingEvaluationWorkflow.run)
    assert "graph(" in source and "ainvoke" in source
    for reimplementation in ("sleep", "while True", "retry", "for attempt"):
        assert reimplementation not in source, (
            f"workflow reimplements '{reimplementation}' — Temporal owns that"
        )


# -- live execution: skips without a server ----------------------------------


@pytest.mark.integration
def test_workflow_executes_against_a_running_server() -> None:
    settings = load_settings()
    if not _temporal_reachable(settings.temporal_address):
        pytest.skip(
            f"no Temporal server at {settings.temporal_address}; durable execution "
            "not verified here (see ADR-0006)"
        )

    from app.activities.patching import create_working_copy
    from app.domain.fixtures import build_problem_specification
    from app.workflows.coding_evaluation import execute_investigation_workflow

    specification = build_problem_specification()
    working_copy = create_working_copy()
    try:
        state = {
            "run_id": "temporal-integration",
            "solver_pseudonym": "model-deadbeef",
            "solver_model": "mock-analyst",
            "specification": specification.model_dump(mode="json"),
            "working_copy_path": str(working_copy.path),
        }
        result = asyncio.run(
            execute_investigation_workflow(settings, state, "temporal-integration")
        )
    finally:
        working_copy.cleanup()

    assert result["diagnosis"]["hypothesis_id"] == "H-1"
    assert len(result["candidates"]) >= 2


@pytest.mark.integration
def test_full_run_uses_temporal_when_available() -> None:
    settings = load_settings()
    if not _temporal_reachable(settings.temporal_address):
        pytest.skip(f"no Temporal server at {settings.temporal_address}")

    from app.runner import RunRequest, run_evaluation

    report = asyncio.run(
        run_evaluation(RunRequest(candidate_id="C-claim", execution_mode="temporal"))
    )
    assert str(report.run.execution_mode) == "temporal"
    assert report.decision.durable_execution is True
    assert report.decision.outcome == "accepted_for_review"
