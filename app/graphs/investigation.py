"""The bounded investigation graph.

LangGraph owns the shape: state, nodes, transitions, conditional routing. Temporal
owns execution guarantees — every node that does real work is declared
``execute_in="activity"``, so the official plugin runs it as a Temporal Activity
with Temporal's retry policy and timeout (ADR-0002).

Nothing here implements persistence, retries, timers, or recovery. If you find
yourself adding a retry loop to a node, the node is in the wrong place.

**Bounded** means bounded: a fixed node set, no cycles, and hard caps on the number
of hypotheses and probes. An investigation that can loop is an investigation that
can bill forever.

State-carried span names matter. Activity nodes may run in a different process from
the workflow, so an in-process ledger cannot see them; each node therefore appends
its span name to the state, and that list is what the artifact gate reads.
"""

from __future__ import annotations

import functools
import operator
from collections.abc import Callable
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.activities.probes import PROBE_REGISTRY
from app.activities.repository import inspect_repository
from app.config import load_settings
from app.domain.schemas import EvidencePolarity, ProbeOutcome
from app.models.gateway import ModelGateway
from app.models.registry import build_default_registry
from app.telemetry.tracing import SpanLedger, span

MAX_HYPOTHESES = 5
MAX_PROBES = 5
MIN_DISTINCT_MECHANISMS = 3


class InvestigationState(TypedDict, total=False):
    """The investigation's state container.

    Everything is JSON-serialisable because it crosses the Temporal activity
    boundary through the payload converter.
    """

    run_id: str
    solver_pseudonym: str
    solver_model: str
    specification: dict[str, Any]
    working_copy_path: str

    inspection: dict[str, Any]
    hypotheses: list[dict[str, Any]]
    probes: list[dict[str, Any]]
    probe_results: list[dict[str, Any]]

    # Reducer note: `operator.add` APPENDS. A node returns only its NEW items —
    # returning the whole accumulated list double-appends it.
    evidence: Annotated[list[dict[str, Any]], operator.add]
    span_names: Annotated[list[str], operator.add]

    diagnosis: dict[str, Any]
    candidates: list[dict[str, Any]]
    abstained: bool
    abstention_reason: str


#: Process-local span ledger. In Temporal mode, activity nodes run in the worker
#: process and populate the worker's ledger, which is precisely why each node also
#: writes its span name into the graph state — the state crosses the boundary, an
#: in-process ledger does not.
_LEDGER = SpanLedger()


def get_ledger() -> SpanLedger:
    return _LEDGER


def traced(span_name: str) -> Callable[[Callable[..., dict]], Callable[..., dict]]:
    """Emit a real OTel span around a node, recording only observable attributes."""

    def decorate(node: Callable[..., dict]) -> Callable[..., dict]:
        @functools.wraps(node)
        def wrapper(state: InvestigationState) -> dict[str, Any]:
            with span(span_name, _LEDGER, {"investigation.node": span_name}):
                return node(state)

        return wrapper

    return decorate


def _gateway() -> ModelGateway:
    settings = load_settings()
    return ModelGateway(
        registry=build_default_registry(settings.enable_live_providers),
        base_url=settings.litellm_base_url,
        api_key=settings.litellm_master_key,
    )


def _evidence_record(
    evidence_id: str, source: str, polarity: EvidencePolarity, summary: str, payload: str
) -> dict[str, Any]:
    import hashlib

    return {
        "schema_version": 1,
        "evidence_id": evidence_id,
        "source": source,
        "polarity": str(polarity),
        "summary": summary,
        "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "artifact_reference": None,
    }


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def validate_specification(state: InvestigationState) -> dict[str, Any]:
    """Reject a request that cannot be investigated before spending anything on it."""
    specification = state.get("specification") or {}
    problems: list[str] = []

    if not specification.get("repository_path"):
        problems.append("specification has no repository path")
    if not specification.get("expected_behaviour"):
        problems.append("specification does not state expected behaviour")
    if not specification.get("invariants"):
        problems.append("specification declares no invariants")

    if problems:
        return {
            "abstained": True,
            "abstention_reason": "; ".join(problems),
            "span_names": ["validate-specification"],
        }

    return {"span_names": ["validate-specification"]}


def inspect_repository_node(state: InvestigationState) -> dict[str, Any]:
    """Read the solver-visible surface only."""
    specification = state.get("specification") or {}
    inspection = inspect_repository(specification.get("repository_path"))

    return {
        "inspection": {
            "root": inspection.root,
            "visible_files": list(inspection.visible_files),
            "declared_invariants": list(inspection.declared_invariants),
            "delivery_model": inspection.delivery_model,
            "content_digest": inspection.content_digest,
            "withheld_directories": list(inspection.withheld_directories),
        },
        "evidence": [
            _evidence_record(
                "E-inspection",
                "inspect_repository",
                EvidencePolarity.NEUTRAL,
                (
                    f"Repository declares {inspection.delivery_model} delivery with "
                    f"{len(inspection.declared_invariants)} invariants across "
                    f"{len(inspection.visible_files)} visible files."
                ),
                inspection.content_digest,
            )
        ],
        "span_names": ["inspect-repository"],
    }


def generate_hypotheses(state: InvestigationState) -> dict[str, Any]:
    """Ask the solver for causally distinct root-cause hypotheses."""
    gateway = _gateway()
    inspection = state.get("inspection") or {}
    specification = state.get("specification") or {}

    invocation = gateway.invoke(
        pseudonym=state.get("solver_pseudonym", "model-00000000"),
        logical_name=state.get("solver_model", "mock-analyst"),
        task={
            "task_type": "generate_hypotheses",
            "reported_symptom": specification.get("reported_symptom", ""),
            "expected_behaviour": specification.get("expected_behaviour", ""),
            "delivery_model": inspection.get("delivery_model", "undeclared"),
            "visible_files": inspection.get("visible_files", []),
            "required_fields": [
                "causal_mechanism",
                "assumptions",
                "predicted_observations",
                "falsification_condition",
                "proposed_probe_id",
            ],
            "minimum_distinct_mechanisms": MIN_DISTINCT_MECHANISMS,
        },
    )

    hypotheses = invocation.parsed().get("hypotheses", [])[:MAX_HYPOTHESES]
    distinct = {h.get("mechanism_class") for h in hypotheses}

    evidence = [
        _evidence_record(
            "E-hypotheses",
            "generate_hypotheses",
            EvidencePolarity.NEUTRAL,
            (
                f"{len(hypotheses)} hypotheses proposed spanning "
                f"{len(distinct)} distinct causal mechanism classes."
            ),
            invocation.content,
        )
    ]

    # Low mechanism diversity is itself a finding: three restatements of one idea
    # are not three hypotheses, and recording that keeps the count honest.
    if len(distinct) < MIN_DISTINCT_MECHANISMS:
        evidence.append(
            _evidence_record(
                "E-low-diversity",
                "generate_hypotheses",
                EvidencePolarity.CONTRADICTING,
                (
                    f"only {len(distinct)} distinct mechanism classes were proposed, "
                    f"below the required {MIN_DISTINCT_MECHANISMS}"
                ),
                invocation.content,
            )
        )

    return {
        "hypotheses": hypotheses,
        "evidence": evidence,
        "span_names": ["generate-hypotheses"],
    }


def design_probes(state: InvestigationState) -> dict[str, Any]:
    """Choose deterministic probes that discriminate between the hypotheses."""
    gateway = _gateway()
    hypotheses = state.get("hypotheses") or []

    invocation = gateway.invoke(
        pseudonym=state.get("solver_pseudonym", "model-00000000"),
        logical_name=state.get("solver_model", "mock-analyst"),
        task={
            "task_type": "design_probes",
            "hypotheses": [
                {
                    "hypothesis_id": h.get("hypothesis_id"),
                    "mechanism_class": h.get("mechanism_class"),
                    "falsification_condition": h.get("falsification_condition"),
                }
                for h in hypotheses
            ],
        },
    )

    proposed = invocation.parsed().get("probes", [])
    # Only probes we can actually execute deterministically. A probe that is not
    # in the registry is prose, and prose cannot falsify anything.
    executable = [p for p in proposed if p.get("probe_id") in PROBE_REGISTRY][:MAX_PROBES]

    return {"probes": executable, "span_names": ["design-probes"]}


def execute_probes(state: InvestigationState) -> dict[str, Any]:
    """Run each probe and turn its observations into evidence.

    Both supporting and contradicting evidence is retained. Dropping the
    inconvenient half is the most common way a wrong diagnosis survives.
    """
    from pathlib import Path

    working_copy = Path(state.get("working_copy_path") or "")
    results: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []

    for probe in state.get("probes") or []:
        probe_id = str(probe.get("probe_id") or "")
        runner = PROBE_REGISTRY.get(probe_id)
        if runner is None:
            continue

        execution = runner(working_copy)
        observations = execution.observations
        hypothesis_id = str(probe.get("hypothesis_id") or "")

        outcome, polarity, summary = _interpret(probe_id, observations)

        results.append(
            {
                "schema_version": 1,
                "probe_id": probe_id,
                "hypothesis_id": hypothesis_id,
                "outcome": str(outcome),
                "observations": [f"{k}={v}" for k, v in sorted(observations.items())],
                "evidence_ids": [f"E-{probe_id}"],
                "exit_code": execution.exit_code,
            }
        )
        evidence.append(
            _evidence_record(
                f"E-{probe_id}",
                probe_id,
                polarity,
                summary,
                execution.stdout or str(observations),
            )
        )

    return {
        "probe_results": results,
        "evidence": evidence,
        "span_names": ["execute-probes"],
    }


def _interpret(
    probe_id: str, observations: dict[str, Any]
) -> tuple[ProbeOutcome, EvidencePolarity, str]:
    """Map raw probe observations onto an outcome.

    Deliberately explicit per probe rather than a generic rule: each probe was
    designed to discriminate a specific hypothesis, and that intent belongs in
    code where it can be read and tested.
    """
    if probe_id == "P-concurrent-delivery":
        duplicated = bool(observations.get("duplicate_processing"))
        return (
            (
                ProbeOutcome.SUPPORTED,
                EvidencePolarity.SUPPORTING,
                f"Forced concurrency produced {observations.get('raw_result_rows')} committed "
                f"rows and {observations.get('effect_count')} external effects for one job id.",
            )
            if duplicated
            else (
                ProbeOutcome.FALSIFIED,
                EvidencePolarity.CONTRADICTING,
                "Forced concurrency produced no duplicate processing.",
            )
        )

    if probe_id == "P-sequential-redelivery":
        duplicated = bool(observations.get("duplicate_processing"))
        # Non-duplication here FALSIFIES "there is no duplicate check at all".
        return (
            (
                ProbeOutcome.SUPPORTED,
                EvidencePolarity.SUPPORTING,
                "Sequential redelivery also duplicated: the duplicate check is absent "
                "or ineffective even without concurrency.",
            )
            if duplicated
            else (
                ProbeOutcome.FALSIFIED,
                EvidencePolarity.CONTRADICTING,
                "Sequential redelivery committed exactly once: a duplicate check "
                "exists and works when deliveries do not overlap.",
            )
        )

    if probe_id == "P-delivery-contract":
        contractual = bool(observations.get("redelivery_is_contractual"))
        # At-least-once delivery FALSIFIES "the queue is broken".
        return (
            (
                ProbeOutcome.FALSIFIED,
                EvidencePolarity.CONTRADICTING,
                "Delivery is declared at-least-once, so redelivery is correct queue "
                "behaviour and the consumer is at fault.",
            )
            if contractual
            else (
                ProbeOutcome.INCONCLUSIVE,
                EvidencePolarity.NEUTRAL,
                "The delivery contract could not be determined.",
            )
        )

    return (ProbeOutcome.INCONCLUSIVE, EvidencePolarity.NEUTRAL, "Probe produced no verdict.")


def establish_diagnosis(state: InvestigationState) -> dict[str, Any]:
    """Select a hypothesis that survived its probes, or abstain."""
    results = state.get("probe_results") or []
    hypotheses = state.get("hypotheses") or []

    falsified = {r["hypothesis_id"] for r in results if r["outcome"] == str(ProbeOutcome.FALSIFIED)}
    supported = {r["hypothesis_id"] for r in results if r["outcome"] == str(ProbeOutcome.SUPPORTED)}
    surviving = [h for h in hypotheses if h.get("hypothesis_id") not in falsified]

    if not surviving:
        return {
            "abstained": True,
            "abstention_reason": "no hypothesis survived its falsification probes",
            "diagnosis": {"hypothesis_id": None, "surviving_hypothesis_ids": []},
            "span_names": ["establish-diagnosis"],
        }

    # Prefer a survivor that a probe actively supported over one that merely was
    # not attacked. "Nothing disproved it" is a much weaker claim than "a probe
    # predicted this and the prediction held".
    chosen = next((h for h in surviving if h.get("hypothesis_id") in supported), surviving[0])

    supporting_ids = [
        eid
        for r in results
        if r["hypothesis_id"] == chosen.get("hypothesis_id")
        and r["outcome"] == str(ProbeOutcome.SUPPORTED)
        for eid in r["evidence_ids"]
    ]
    contradicting_ids = [
        eid
        for r in results
        if r["hypothesis_id"] == chosen.get("hypothesis_id")
        and r["outcome"] == str(ProbeOutcome.FALSIFIED)
        for eid in r["evidence_ids"]
    ]

    return {
        "diagnosis": {
            "hypothesis_id": chosen.get("hypothesis_id"),
            "mechanism_class": chosen.get("mechanism_class"),
            "causal_mechanism": chosen.get("causal_mechanism"),
            "supporting_evidence_ids": supporting_ids,
            "contradicting_evidence_ids": contradicting_ids,
            "surviving_hypothesis_ids": [h.get("hypothesis_id") for h in surviving],
            "probe_supported": chosen.get("hypothesis_id") in supported,
        },
        "span_names": ["establish-diagnosis"],
    }


def generate_repair_candidates(state: InvestigationState) -> dict[str, Any]:
    """Ask for at least two repair candidates for the established diagnosis."""
    gateway = _gateway()
    diagnosis = state.get("diagnosis") or {}

    invocation = gateway.invoke(
        pseudonym=state.get("solver_pseudonym", "model-00000000"),
        logical_name=state.get("solver_model", "mock-analyst"),
        task={
            "task_type": "generate_repair_candidates",
            "diagnosis": {
                "hypothesis_id": diagnosis.get("hypothesis_id"),
                "mechanism_class": diagnosis.get("mechanism_class"),
                "causal_mechanism": diagnosis.get("causal_mechanism"),
            },
            "minimum_candidates": 2,
        },
    )

    candidates = invocation.parsed().get("candidates", [])
    return {"candidates": candidates, "span_names": ["generate-repair-candidates"]}


def abstain(state: InvestigationState) -> dict[str, Any]:
    """Terminal node for an investigation that cannot reach a diagnosis."""
    return {
        "abstained": True,
        "abstention_reason": state.get("abstention_reason")
        or "the investigation could not establish a diagnosis",
    }


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


def _route_after_validation(state: InvestigationState) -> str:
    return "abstain" if state.get("abstained") else "inspect_repository"


def _route_after_diagnosis(state: InvestigationState) -> str:
    return "abstain" if state.get("abstained") else "generate_repair_candidates"


#: Activity options applied to every node that does real work. Temporal supplies
#: the retry and the timeout; the node supplies none of it.
def _activity_metadata(seconds: int, attempts: int) -> dict[str, Any]:
    from datetime import timedelta

    from temporalio.common import RetryPolicy

    return {
        "execute_in": "activity",
        "start_to_close_timeout": timedelta(seconds=seconds),
        "retry_policy": RetryPolicy(maximum_attempts=attempts),
    }


def build_investigation_graph() -> StateGraph:
    """Construct the bounded investigation graph.

    Every node declares ``execute_in``; the Temporal plugin refuses to default it,
    and a node that quietly ran in the workflow would lose its retry and timeout.
    """
    graph: StateGraph = StateGraph(InvestigationState)

    # Pure decisions run in the workflow: no I/O, deterministic, replay-safe.
    graph.add_node(
        "validate_specification",
        traced("validate-specification")(validate_specification),
        metadata={"execute_in": "workflow"},
    )
    graph.add_node(
        "establish_diagnosis",
        traced("establish-diagnosis")(establish_diagnosis),
        metadata={"execute_in": "workflow"},
    )
    graph.add_node("abstain", abstain, metadata={"execute_in": "workflow"})

    # Real work runs as Temporal Activities.
    graph.add_node(
        "inspect_repository",
        traced("inspect-repository")(inspect_repository_node),
        metadata=_activity_metadata(60, 3),
    )
    graph.add_node(
        "generate_hypotheses",
        traced("generate-hypotheses")(generate_hypotheses),
        metadata=_activity_metadata(120, 3),
    )
    graph.add_node(
        "design_probes", traced("design-probes")(design_probes), metadata=_activity_metadata(120, 3)
    )
    graph.add_node(
        "execute_probes",
        traced("execute-probes")(execute_probes),
        metadata=_activity_metadata(300, 2),
    )
    graph.add_node(
        "generate_repair_candidates",
        traced("generate-repair-candidates")(generate_repair_candidates),
        metadata=_activity_metadata(120, 3),
    )

    graph.add_edge(START, "validate_specification")
    graph.add_conditional_edges(
        "validate_specification",
        _route_after_validation,
        {"abstain": "abstain", "inspect_repository": "inspect_repository"},
    )
    graph.add_edge("inspect_repository", "generate_hypotheses")
    graph.add_edge("generate_hypotheses", "design_probes")
    graph.add_edge("design_probes", "execute_probes")
    graph.add_edge("execute_probes", "establish_diagnosis")
    graph.add_conditional_edges(
        "establish_diagnosis",
        _route_after_diagnosis,
        {
            "abstain": "abstain",
            "generate_repair_candidates": "generate_repair_candidates",
        },
    )
    graph.add_edge("generate_repair_candidates", END)
    graph.add_edge("abstain", END)

    return graph


#: Name the Temporal plugin registers this graph under.
INVESTIGATION_GRAPH_NAME = "coding-investigation"
