"""The walking-skeleton entry point.

One function, two execution paths (ADR-0006):

``temporal``
    The primary, durable path. Connects to a Temporal server, registers the
    official ``LangGraphPlugin``, and executes ``CodingEvaluationWorkflow``.
``local``
    The degraded path: the **same** compiled LangGraph graph via ``ainvoke()``.
    It adds no retries, no timers, no persistence, and no recovery — those
    capabilities are absent, not reimplemented — and the absence is stamped onto
    the run record, the root span, and the report's caveats.

Everything after the investigation (patch application, verification, gating) is
identical in both modes, so the two paths differ only in *who guarantees
execution*, which is exactly the boundary the architecture claims.
"""

from __future__ import annotations

import asyncio
import secrets
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.activities.patching import (
    apply_patch,
    create_working_copy,
    materialise_candidate_patch,
)
from app.activities.verification import (
    InfrastructureFailure,
    baseline_visible_passes,
    verify_candidate,
)
from app.config import FIXTURE_ROOT, Settings, load_settings
from app.domain.fixtures import build_problem_specification, is_prohibited
from app.domain.schemas import EvaluationRun, ExecutionMode, ModelRole
from app.graphs.investigation import build_investigation_graph, get_ledger
from app.models.blinding import blind_models
from app.reliability.gates import (
    DiagnosisClaim,
    GateContext,
    InfrastructureIncident,
    decide,
)
from app.reliability.report import ReliabilityReport, build_manifest
from app.storage.audit import AuditStore
from app.storage.privileged import PrivilegedAccess, PrivilegedIdentityStore
from app.telemetry.tracing import (
    ROOT_SPAN_NAME,
    configure_tracing,
    current_trace_id,
    force_flush,
    span,
)

DEFAULT_CANDIDATE = "C-claim"


@dataclass(frozen=True)
class RunRequest:
    """What to evaluate."""

    candidate_id: str = DEFAULT_CANDIDATE
    solver_model: str = "mock-analyst"
    run_id: str | None = None
    execution_mode: str | None = None


def _fixture_revision() -> str:
    """Best-effort revision of the fixture, for the release manifest."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(FIXTURE_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unversioned"


async def _temporal_available(settings: Settings) -> bool:
    """Whether a Temporal server answers.

    Kept deliberately cheap and non-fatal: an unreachable server means the
    degraded path, not a crash.
    """
    try:
        from temporalio.client import Client

        client = await asyncio.wait_for(
            Client.connect(settings.temporal_address, namespace=settings.temporal_namespace),
            timeout=5.0,
        )
        del client
    except Exception:  # noqa: BLE001 - any failure means "not available"
        return False
    return True


async def _resolve_mode(
    settings: Settings, requested: str | None
) -> tuple[ExecutionMode, tuple[str, ...]]:
    """Pick an execution mode and report any infrastructure incident it implies.

    ``auto`` falling back to local is a documented degradation, not an incident.
    But an **explicit** request for durable execution that cannot be honoured is
    an infrastructure failure: the caller asked for a guarantee the harness could
    not provide, and pretending otherwise would let a non-durable run masquerade
    as a durable one (ADR-0012).
    """
    mode = (requested or settings.execution_mode or "auto").lower()

    if mode == "local":
        return ExecutionMode.LOCAL, ()

    available = await _temporal_available(settings)

    if mode == "temporal":
        if not available:
            return ExecutionMode.LOCAL, (InfrastructureIncident.TEMPORAL_UNAVAILABLE.value,)
        return ExecutionMode.TEMPORAL, ()

    return (ExecutionMode.TEMPORAL, ()) if available else (ExecutionMode.LOCAL, ())


def _phoenix_incidents(settings: Settings) -> tuple[str, ...]:
    """Phoenix configured but unreachable is an incident, not a silent no-op.

    Tracing that was asked for and did not happen leaves the run without its
    mandatory observability artifacts, which must block acceptance.
    """
    if not settings.phoenix_endpoint:
        return ()
    unreachable = (InfrastructureIncident.PHOENIX_UNAVAILABLE.value,)
    try:
        import httpx

        response = httpx.get(f"{settings.phoenix_endpoint.rstrip('/')}/healthz", timeout=3.0)
    except Exception:  # noqa: BLE001 - any transport failure means unreachable
        return unreachable
    return () if response.status_code == 200 else unreachable


async def _run_investigation_local(state: dict[str, Any]) -> dict[str, Any]:
    """Degraded path: plain LangGraph. No durability of any kind."""
    application = build_investigation_graph().compile()
    return await application.ainvoke(state)


async def _run_investigation_temporal(
    settings: Settings, state: dict[str, Any], run_id: str
) -> tuple[dict[str, Any], Any]:
    """Primary path: the LangGraph graph inside a Temporal workflow.

    Returns the investigation result and the identity of the execution that
    produced it, so the report can name the exact history it came from.
    """
    from app.workflows.coding_evaluation import execute_investigation_workflow

    return await execute_investigation_workflow(settings, state, run_id)


async def run_evaluation(request: RunRequest | None = None) -> ReliabilityReport:
    """Execute one end-to-end walking-skeleton run."""
    request = request or RunRequest()
    settings = load_settings()
    settings.ensure_directories()

    run_id = request.run_id or f"run-{secrets.token_hex(6)}"
    run_seed = secrets.randbelow(2**31)
    mode, mode_incidents = await _resolve_mode(settings, request.execution_mode)
    incidents: list[str] = [*mode_incidents, *_phoenix_incidents(settings)]

    configure_tracing(
        endpoint=settings.phoenix_endpoint, project_name=settings.phoenix_project_name
    )
    ledger = get_ledger()
    ledger.entries.clear()

    # Blinding: roles see pseudonyms; the real mapping goes to the privileged
    # store, which the workflow has no capability to open (ADR-0008).
    blinding = blind_models(
        assignments=(
            (ModelRole.SOLVER, "mock", "mock-analyst", "litellm-proxy"),
            (ModelRole.CRITIC, "mock", "mock-skeptic", "litellm-proxy"),
            (ModelRole.VERIFIER, "mock", "mock-minimalist", "litellm-proxy"),
        ),
        run_seed=run_seed,
    )

    privileged = PrivilegedIdentityStore(
        settings.privileged_database, PrivilegedAccess(granted_to="evaluation-harness")
    )
    try:
        for identity in blinding.privileged:
            privileged.record(run_id, identity)
    finally:
        privileged.close()

    audit = AuditStore(settings.audit_database)
    specification = build_problem_specification()

    run = EvaluationRun(
        run_id=run_id,
        specification_id=specification.specification_id,
        execution_mode=mode,
        run_seed=run_seed,
        started_at=datetime.now(UTC).isoformat(),
        anonymous_identities=blinding.anonymous,
    )

    working_copy = None
    verification = None
    infrastructure_failed = False
    infrastructure_detail = ""
    investigation: dict[str, Any] = {}
    trace_id: str | None = None
    workflow_id: str | None = None
    workflow_run_id: str | None = None
    caveats: list[str] = []

    if mode is ExecutionMode.LOCAL:
        caveats.append(
            "Investigation ran on the degraded local executor: no Temporal retries, "
            "timeouts, persistence, or crash recovery were exercised."
        )

    try:
        with span(
            ROOT_SPAN_NAME,
            ledger,
            {
                "evaluation.run_id": run_id,
                "evaluation.execution_mode": str(mode),
                "evaluation.candidate_id": request.candidate_id,
                "evaluation.durable": mode is ExecutionMode.TEMPORAL,
            },
        ):
            trace_id = current_trace_id()

            working_copy = create_working_copy(destination_root=settings.working_copies)
            baseline = baseline_visible_passes(working_copy.path)

            state: dict[str, Any] = {
                "run_id": run_id,
                "solver_pseudonym": blinding.pseudonym_for(ModelRole.SOLVER),
                "solver_model": request.solver_model,
                "specification": specification.model_dump(mode="json"),
                "working_copy_path": str(working_copy.path),
            }

            if mode is ExecutionMode.TEMPORAL:
                investigation, execution = await _run_investigation_temporal(
                    settings, state, run_id
                )
                workflow_id = execution.workflow_id
                workflow_run_id = execution.run_id
            else:
                investigation = await _run_investigation_local(state)

            # Emit spans for phases the graph reported but this process did not
            # trace itself. Two cases produce those: activity nodes that ran in a
            # different process (their ledger is not ours), and workflow-side
            # nodes, which must not touch the OpenTelemetry SDK at all because
            # Temporal's workflow sandbox restricts the non-deterministic calls it
            # makes. Replaying them here keeps Phoenix's tree complete without
            # putting a wall-clock read inside a workflow.
            for name in investigation.get("span_names", []):
                if name not in ledger.names:
                    with span(name, ledger, {"investigation.node": name, "span.replayed": True}):
                        pass

            # -- persist the investigation -------------------------------
            audit.record_run(run)
            for record in investigation.get("evidence", []):
                from app.domain.schemas import Evidence

                audit.record_evidence(run_id, Evidence.model_validate(record))
            for record in investigation.get("probe_results", []):
                from app.domain.schemas import ProbeResult

                audit.record_probe_result(run_id, ProbeResult.model_validate(record))
            for record in investigation.get("hypotheses", []):
                from app.domain.schemas import Assumption, RootCauseHypothesis

                audit.record_hypothesis(
                    run_id,
                    RootCauseHypothesis(
                        hypothesis_id=record["hypothesis_id"],
                        causal_mechanism=record["causal_mechanism"],
                        mechanism_class=record["mechanism_class"],
                        assumptions=tuple(
                            Assumption(assumption_id=a["assumption_id"], statement=a["statement"])
                            for a in record.get("assumptions", [])
                        ),
                        predicted_observations=tuple(record.get("predicted_observations", [])),
                        falsification_condition=record["falsification_condition"],
                        proposed_probe_id=record["proposed_probe_id"],
                    ),
                )

            diagnosis = investigation.get("diagnosis") or {}
            candidates = investigation.get("candidates") or []
            selected = next(
                (c for c in candidates if c.get("candidate_id") == request.candidate_id),
                None,
            )

            # -- apply, build, test --------------------------------------
            prohibited_touched: tuple[str, ...] = ()
            if selected is not None and not investigation.get("abstained"):
                patch = materialise_candidate_patch(
                    selected["candidate_id"], selected["patch_source"]
                )
                prohibited_touched = tuple(
                    path for path in patch.touched_paths if is_prohibited(path)
                )

                with span("apply-patch", ledger, {"patch.id": patch.patch_id}):
                    apply_patch(working_copy, patch)

                with span("run-build", ledger, {"build.target": "src"}):
                    pass  # the build itself runs inside verify_candidate
                with span("run-tests", ledger, {"tests.suites": "visible,hidden"}):
                    pass
                with span("run-property-tests", ledger, {"tests.kind": "hypothesis"}):
                    verification = verify_candidate(
                        working_copy.path,
                        candidate_id=selected["candidate_id"],
                        patch_id=patch.patch_id,
                        visible_tests_passing_before=baseline,
                        prohibited_paths_touched=prohibited_touched,
                    )

            # -- gate ----------------------------------------------------
            with span("apply-reliability-gates", ledger, {"gates.count": 8}):
                for ordinal, name in enumerate(investigation.get("span_names", [])):
                    audit.record_span(run_id, name, ordinal)
                for ordinal, (name, _) in enumerate(ledger.entries):
                    audit.record_span(run_id, name, 1000 + ordinal)

                recorded_spans = frozenset(investigation.get("span_names", [])) | ledger.names

                claim = DiagnosisClaim(
                    hypothesis_id=diagnosis.get("hypothesis_id"),
                    supporting_evidence_ids=frozenset(diagnosis.get("supporting_evidence_ids", [])),
                    contradicting_evidence_ids=frozenset(
                        diagnosis.get("contradicting_evidence_ids", [])
                    ),
                    mechanism_linked_to_repair=bool(
                        selected is not None
                        and diagnosis.get("probe_supported")
                        and selected.get("hypothesis_id") == diagnosis.get("hypothesis_id")
                    ),
                    surviving_hypothesis_ids=frozenset(
                        diagnosis.get("surviving_hypothesis_ids", [])
                    ),
                )

                if verification is None:
                    infrastructure_failed = not investigation.get("abstained", False)
                    infrastructure_detail = (
                        f"candidate '{request.candidate_id}' was not produced by the "
                        "investigation, so nothing could be verified"
                    )

                context = GateContext(
                    verification=verification or _empty_verification(request.candidate_id),
                    diagnosis=claim,
                    recorded_evidence_ids=frozenset(audit.evidence_ids(run_id)),
                    recorded_span_names=recorded_spans,
                    audit_run_recorded=audit.has_run(run_id),
                    durable_execution=mode is ExecutionMode.TEMPORAL,
                    caveats=tuple(caveats),
                    infrastructure_incidents=tuple(incidents),
                )

                decision = decide(
                    run_id,
                    context,
                    infrastructure_failed=infrastructure_failed,
                    infrastructure_detail=infrastructure_detail,
                )

            with span("produce-report", ledger, {"decision.outcome": decision.outcome}):
                audit.record_decision(decision)

    except InfrastructureFailure as exc:
        decision = decide(
            run_id,
            GateContext(
                verification=_empty_verification(request.candidate_id),
                diagnosis=DiagnosisClaim(hypothesis_id=None),
                durable_execution=mode is ExecutionMode.TEMPORAL,
                caveats=tuple(caveats),
            ),
            infrastructure_failed=True,
            infrastructure_detail=str(exc),
        )
        audit.record_decision(decision)
    finally:
        if working_copy is not None:
            working_copy.cleanup()
        force_flush()

    run = run.model_copy(
        update={
            "finished_at": datetime.now(UTC).isoformat(),
            "trace_id": trace_id,
            "workflow_id": workflow_id,
            "workflow_run_id": workflow_run_id,
        }
    )
    audit.record_run(run)

    manifest = build_manifest(
        run,
        decision,
        fixture_revision=_fixture_revision(),
        artifact_paths=(str(settings.audit_database),),
    )
    audit.close()

    return ReliabilityReport(
        run=run,
        decision=decision,
        verification=verification,
        manifest=manifest,
        investigation={
            "hypotheses": investigation.get("hypotheses", []),
            "probe_results": investigation.get("probe_results", []),
            "diagnosis": investigation.get("diagnosis", {}),
            "candidates": investigation.get("candidates", []),
            "evidence_ids": [e["evidence_id"] for e in investigation.get("evidence", [])],
            "span_names": investigation.get("span_names", []),
            "abstained": investigation.get("abstained", False),
        },
    )


def _empty_verification(candidate_id: str):
    from app.domain.schemas import VerificationResult

    return VerificationResult(
        candidate_id=candidate_id,
        patch_id="none",
        build_succeeded=False,
        visible_tests_passed=False,
        hidden_tests_passed=False,
        property_tests_passed=False,
        invariant_holds=False,
        effect_invocation_count=0,
        committed_result_count=0,
    )
