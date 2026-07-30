"""LangGraph transition tests."""

from __future__ import annotations

from langgraph.graph import END, START

from app.graphs.investigation import (
    MAX_HYPOTHESES,
    MAX_PROBES,
    _route_after_diagnosis,
    _route_after_validation,
    build_investigation_graph,
    establish_diagnosis,
    validate_specification,
)

ACTIVITY_NODES = {
    "inspect_repository",
    "generate_hypotheses",
    "design_probes",
    "execute_probes",
    "generate_repair_candidates",
}
WORKFLOW_NODES = {"validate_specification", "establish_diagnosis", "abstain"}


def test_graph_has_exactly_the_expected_nodes() -> None:
    graph = build_investigation_graph()
    assert set(graph.nodes) - {START, END} == ACTIVITY_NODES | WORKFLOW_NODES


def test_every_node_declares_execute_in() -> None:
    """The Temporal plugin refuses to default `execute_in`.

    A node without it would silently lose its retry policy and timeout, so this
    is checked structurally rather than trusted.
    """
    graph = build_investigation_graph()
    for name, node in graph.nodes.items():
        if name in {START, END}:
            continue
        metadata = node.metadata or {}
        assert "execute_in" in metadata, f"node '{name}' does not declare execute_in"
        assert metadata["execute_in"] in {"activity", "workflow"}


def test_work_runs_in_activities_and_decisions_in_the_workflow() -> None:
    graph = build_investigation_graph()
    for name in ACTIVITY_NODES:
        assert graph.nodes[name].metadata["execute_in"] == "activity"
    for name in WORKFLOW_NODES:
        assert graph.nodes[name].metadata["execute_in"] == "workflow"


def test_activity_nodes_carry_temporal_retry_and_timeout() -> None:
    """Retry and timeout are Temporal's, declared per node (ADR-0002)."""
    graph = build_investigation_graph()
    for name in ACTIVITY_NODES:
        metadata = graph.nodes[name].metadata
        assert "start_to_close_timeout" in metadata, f"{name} has no timeout"
        assert "retry_policy" in metadata, f"{name} has no retry policy"
        assert metadata["retry_policy"].maximum_attempts >= 1


def test_graph_compiles() -> None:
    assert build_investigation_graph().compile() is not None


def test_graph_is_bounded() -> None:
    assert MAX_HYPOTHESES <= 10
    assert MAX_PROBES <= 10


async def test_validation_failure_routes_to_abstain() -> None:
    assert await _route_after_validation({"abstained": True}) == "abstain"
    assert await _route_after_validation({}) == "inspect_repository"


async def test_diagnosis_failure_routes_to_abstain() -> None:
    assert await _route_after_diagnosis({"abstained": True}) == "abstain"
    assert await _route_after_diagnosis({}) == "generate_repair_candidates"


async def test_incomplete_specification_abstains_before_spending_anything() -> None:
    result = await validate_specification({"specification": {"repository_path": ""}})
    assert result["abstained"] is True
    assert "repository path" in result["abstention_reason"]


async def test_valid_specification_proceeds() -> None:
    result = await validate_specification(
        {
            "specification": {
                "repository_path": "/tmp/repo",
                "expected_behaviour": "no duplicates",
                "invariants": [{"invariant_id": "INV-1"}],
            }
        }
    )
    assert not result.get("abstained")
    assert result["span_names"] == ["validate-specification"]


async def test_diagnosis_abstains_when_every_hypothesis_is_falsified() -> None:
    state = {
        "hypotheses": [{"hypothesis_id": "H-1"}, {"hypothesis_id": "H-2"}],
        "probe_results": [
            {"hypothesis_id": "H-1", "outcome": "falsified", "evidence_ids": ["E-1"]},
            {"hypothesis_id": "H-2", "outcome": "falsified", "evidence_ids": ["E-2"]},
        ],
    }
    result = await establish_diagnosis(state)
    assert result["abstained"] is True
    assert result["diagnosis"]["hypothesis_id"] is None


async def test_diagnosis_prefers_an_actively_supported_survivor() -> None:
    """ "A probe predicted this and it held" beats "nothing disproved it"."""
    state = {
        "hypotheses": [
            {"hypothesis_id": "H-untested", "mechanism_class": "a"},
            {"hypothesis_id": "H-supported", "mechanism_class": "b"},
        ],
        "probe_results": [
            {"hypothesis_id": "H-supported", "outcome": "supported", "evidence_ids": ["E-1"]},
        ],
    }
    result = await establish_diagnosis(state)
    assert result["diagnosis"]["hypothesis_id"] == "H-supported"
    assert result["diagnosis"]["probe_supported"] is True
    assert result["diagnosis"]["supporting_evidence_ids"] == ["E-1"]
