"""Deterministic reliability gates.

**This module imports no model client and makes no network call, ever.** Every
gate is a pure function of observable artifacts: exit codes, counts, path sets,
and set relations over evidence ids (ADR-0009).

Models propose. Gates dispose. A model can influence what gets tried; it can never
influence whether a trial passed. If that separation blurs, "deterministically
rejected" stops being true and the whole result becomes a sample from a
distribution.

The gate that carries the weight is :func:`not_symptom_suppression`. It reads the
**external effect counter**, not the committed-row count and not the output log,
because deduplicating output is exactly what the tempting wrong patch does.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.domain.schemas import GateResult, ReliabilityDecision, VerificationResult

#: Spans that must exist for a run's artifacts to be considered complete.
REQUIRED_SPAN_NAMES: frozenset[str] = frozenset(
    {
        "coding-evaluation",
        "validate-specification",
        "inspect-repository",
        "generate-hypotheses",
        "design-probes",
        "execute-probes",
        "establish-diagnosis",
        "generate-repair-candidates",
        "apply-patch",
        "run-build",
        "run-tests",
        "run-property-tests",
        "apply-reliability-gates",
        "produce-report",
    }
)

#: What the artifact gate actually requires. ``produce-report`` is excluded for a
#: structural reason, not a convenient one: the report span cannot have completed
#: at the moment the decision is being made, so requiring it here would make every
#: run fail an artifact check on a span that by definition comes later. The full
#: tree — including ``produce-report`` — is asserted by the instrumentation test.
GATE_REQUIRED_SPAN_NAMES: frozenset[str] = REQUIRED_SPAN_NAMES - {"produce-report"}


@dataclass(frozen=True)
class DiagnosisClaim:
    """The diagnosis being tested, expressed only as ids and flags."""

    hypothesis_id: str | None
    supporting_evidence_ids: frozenset[str] = frozenset()
    contradicting_evidence_ids: frozenset[str] = frozenset()
    #: True when a probe result ties the chosen mechanism to the repair. A claim
    #: made by a model is not sufficient; this is set from probe observations.
    mechanism_linked_to_repair: bool = False
    surviving_hypothesis_ids: frozenset[str] = frozenset()


class InfrastructureIncident(StrEnum):
    """Conditions that are the harness's fault, never the patch's.

    Enumerated rather than free-text so a coding failure cannot be laundered into
    an infrastructure excuse: :func:`classify_infrastructure_incident` refuses any
    kind not on this list.
    """

    TEMPORAL_UNAVAILABLE = "temporal_unavailable"
    PHOENIX_UNAVAILABLE = "phoenix_unavailable"
    MISSING_MANDATORY_TRACE = "missing_mandatory_trace"
    WORKER_FAILURE_WITHOUT_RECOVERY = "worker_failure_without_recovery"
    CORRUPT_EVALUATION_ARTIFACT = "corrupt_evaluation_artifact"
    ACTIVITY_TIMEOUT = "activity_timeout"
    HARNESS_ERROR = "harness_error"


INFRASTRUCTURE_INCIDENT_KINDS: frozenset[str] = frozenset(
    incident.value for incident in InfrastructureIncident
)


def classify_infrastructure_incident(kind: str, *, detail: str = "") -> str:
    """Map an infrastructure incident to its terminal outcome.

    Always ``infrastructure_failure`` — that is the point. The value of this
    function is the guard: an unrecognised ``kind`` raises rather than quietly
    becoming an infrastructure excuse for something that was actually a patch
    failure.
    """
    del detail
    if kind not in INFRASTRUCTURE_INCIDENT_KINDS:
        raise ValueError(
            f"'{kind}' is not a recognised infrastructure incident; known kinds: "
            f"{sorted(INFRASTRUCTURE_INCIDENT_KINDS)}. Refusing to classify an "
            "unknown condition as infrastructure_failure."
        )
    return "infrastructure_failure"


@dataclass(frozen=True)
class GateContext:
    """Everything the gates are allowed to look at."""

    verification: VerificationResult
    diagnosis: DiagnosisClaim
    #: Evidence ids actually persisted in the audit store.
    recorded_evidence_ids: frozenset[str] = frozenset()
    recorded_span_names: frozenset[str] = frozenset()
    audit_run_recorded: bool = False
    durable_execution: bool = True
    caveats: tuple[str, ...] = field(default_factory=tuple)
    #: Infrastructure incidents observed during the run, as
    #: :class:`InfrastructureIncident` values. Any entry forces
    #: ``infrastructure_failure`` and short-circuits every patch verdict.
    infrastructure_incidents: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Rejection gates. Each returns a GateResult; False means reject.
# ---------------------------------------------------------------------------


def build_succeeds(ctx: GateContext) -> GateResult:
    ok = ctx.verification.build_succeeded
    return GateResult(
        gate_name="build_succeeds",
        passed=ok,
        detail="build exited 0" if ok else "the repository does not build",
    )


def no_test_regression(ctx: GateContext) -> GateResult:
    """No test that passed before the patch may fail after it."""
    before = set(ctx.verification.visible_tests_passing_before)
    after = set(ctx.verification.visible_tests_passing_after)
    regressed = sorted(before - after)
    return GateResult(
        gate_name="no_test_regression",
        passed=not regressed,
        detail=(
            "no previously passing test regressed"
            if not regressed
            else f"previously passing tests now fail: {', '.join(regressed)}"
        ),
    )


def hidden_tests_pass(ctx: GateContext) -> GateResult:
    ok = ctx.verification.hidden_tests_passed
    return GateResult(
        gate_name="hidden_tests_pass",
        passed=ok,
        detail="hidden acceptance suite passed" if ok else "hidden tests failed",
    )


def primary_invariant_holds(ctx: GateContext) -> GateResult:
    """One logical job id, at most one committed processing result."""
    result = ctx.verification
    ok = result.invariant_holds and result.committed_result_count <= 1
    return GateResult(
        gate_name="primary_invariant_holds",
        passed=ok,
        detail=(
            f"one committed result per job id (rows={result.committed_result_count})"
            if ok
            else (
                "primary invariant violated: "
                f"{result.committed_result_count} committed results for one job id"
            )
        ),
    )


def evidence_supports_diagnosis(ctx: GateContext) -> GateResult:
    """The diagnosis must cite evidence that actually exists and is not outweighed."""
    claim = ctx.diagnosis
    if claim.hypothesis_id is None:
        return GateResult(
            gate_name="evidence_supports_diagnosis",
            passed=False,
            detail="no diagnosis was established",
        )

    missing = sorted(claim.supporting_evidence_ids - ctx.recorded_evidence_ids)
    if missing:
        return GateResult(
            gate_name="evidence_supports_diagnosis",
            passed=False,
            detail=f"diagnosis cites evidence not present in the audit store: {missing}",
        )
    if not claim.supporting_evidence_ids:
        return GateResult(
            gate_name="evidence_supports_diagnosis",
            passed=False,
            detail="diagnosis cites no supporting evidence",
        )
    if len(claim.contradicting_evidence_ids) >= len(claim.supporting_evidence_ids):
        return GateResult(
            gate_name="evidence_supports_diagnosis",
            passed=False,
            detail=(
                f"contradicting evidence ({len(claim.contradicting_evidence_ids)}) is not "
                f"outweighed by supporting evidence ({len(claim.supporting_evidence_ids)})"
            ),
        )
    return GateResult(
        gate_name="evidence_supports_diagnosis",
        passed=True,
        detail=(
            f"{len(claim.supporting_evidence_ids)} supporting vs "
            f"{len(claim.contradicting_evidence_ids)} contradicting evidence records"
        ),
    )


def no_prohibited_file_changes(ctx: GateContext) -> GateResult:
    touched = ctx.verification.prohibited_paths_touched
    return GateResult(
        gate_name="no_prohibited_file_changes",
        passed=not touched,
        detail=(
            "no prohibited path modified"
            if not touched
            else f"patch modified prohibited paths: {', '.join(touched)}"
        ),
    )


def not_symptom_suppression(ctx: GateContext) -> GateResult:
    """The gate that catches the duct tape.

    Reads the **external effect counter**, which records how many times the
    irreversible work actually ran. A patch can deduplicate a result list; it
    cannot un-fire an effect. So a candidate whose committed rows look clean while
    the effect counter is still 2 has hidden the symptom and left the defect.
    """
    count = ctx.verification.effect_invocation_count
    ok = count <= 1
    return GateResult(
        gate_name="not_symptom_suppression",
        passed=ok,
        detail=(
            f"external effect executed {count} time(s) — duplicate processing prevented"
            if ok
            else (
                f"external effect executed {count} times for one job id: duplicate "
                "output was suppressed but duplicate processing still occurred"
            )
        ),
    )


def required_artifacts_present(ctx: GateContext) -> GateResult:
    """Trace and audit artifacts must exist, or the run cannot be accepted."""
    missing_spans = sorted(GATE_REQUIRED_SPAN_NAMES - ctx.recorded_span_names)
    if missing_spans:
        return GateResult(
            gate_name="required_artifacts_present",
            passed=False,
            detail=f"missing required spans: {', '.join(missing_spans)}",
        )
    if not ctx.audit_run_recorded:
        return GateResult(
            gate_name="required_artifacts_present",
            passed=False,
            detail="no audit record exists for this run",
        )
    return GateResult(
        gate_name="required_artifacts_present",
        passed=True,
        detail=f"{len(ctx.recorded_span_names)} spans and an audit record present",
    )


#: Gates that judge **the patch**. All must pass for a run to be eligible for
#: review. `required_artifacts_present` is deliberately NOT here — a missing trace
#: says nothing about the patch (ADR-0012).
REJECTION_GATES = (
    build_succeeds,
    no_test_regression,
    hidden_tests_pass,
    primary_invariant_holds,
    evidence_supports_diagnosis,
    no_prohibited_file_changes,
    not_symptom_suppression,
)

#: Preconditions on the harness itself. Failing one blocks acceptance — but as
#: `infrastructure_failure`, never as `rejected` (ADR-0012).
INFRASTRUCTURE_GATES = (required_artifacts_present,)

#: Human-readable detail per incident kind, used when composing the decision.
_INCIDENT_DETAIL: dict[str, str] = {
    InfrastructureIncident.TEMPORAL_UNAVAILABLE.value: (
        "the Temporal server could not be reached, so no durable execution occurred"
    ),
    InfrastructureIncident.PHOENIX_UNAVAILABLE.value: (
        "the Phoenix collector could not be reached, so the trace is incomplete"
    ),
    InfrastructureIncident.MISSING_MANDATORY_TRACE.value: (
        "a mandatory observability artifact is missing; acceptance is blocked, but "
        "this implies nothing about whether the patch is correct"
    ),
    InfrastructureIncident.WORKER_FAILURE_WITHOUT_RECOVERY.value: (
        "a worker failed and no replacement resumed the workflow"
    ),
    InfrastructureIncident.CORRUPT_EVALUATION_ARTIFACT.value: (
        "an evaluation artifact could not be read or failed validation"
    ),
    InfrastructureIncident.ACTIVITY_TIMEOUT.value: ("an activity exceeded its configured timeout"),
    InfrastructureIncident.HARNESS_ERROR.value: "the evaluation harness failed",
}

#: Every gate, for the record. Both sets are always evaluated and reported; only
#: the routing of a failure differs.
ALL_GATES = REJECTION_GATES + INFRASTRUCTURE_GATES

#: Gates that are **direct observations of the patched repository's behaviour**
#: and need no diagnosis to interpret. If one of these fails, the system has
#: measured something concrete and must say so.
#:
#: This set exists to order rejection ahead of abstention. Abstention means "we
#: could not tell"; a failing hidden test or an effect counter reading 2 means we
#: could tell. Reporting that as abstention would understate a finding the system
#: actually made — which is its own kind of dishonesty.
OBSERVATIONAL_GATE_NAMES: frozenset[str] = frozenset(
    {
        "build_succeeds",
        "no_test_regression",
        "hidden_tests_pass",
        "primary_invariant_holds",
        "no_prohibited_file_changes",
        "not_symptom_suppression",
    }
)


def evaluate_gates(ctx: GateContext) -> tuple[GateResult, ...]:
    """Run every gate. All of them, always — a full picture beats a fast exit."""
    return tuple(gate(ctx) for gate in ALL_GATES)


def infrastructure_incidents(ctx: GateContext) -> tuple[str, ...]:
    """Every infrastructure incident implied by this context.

    Combines incidents the caller observed (an unreachable Temporal server, a
    worker that never recovered) with those implied by the artifacts themselves
    (a missing mandatory span).
    """
    incidents = list(ctx.infrastructure_incidents)
    if not required_artifacts_present(ctx).passed:
        incidents.append(InfrastructureIncident.MISSING_MANDATORY_TRACE.value)
    # Validate every kind; an unknown one raises rather than silently excusing.
    for kind in incidents:
        classify_infrastructure_incident(kind)
    return tuple(dict.fromkeys(incidents))


# ---------------------------------------------------------------------------
# Abstention
# ---------------------------------------------------------------------------


def abstention_reason(ctx: GateContext) -> str | None:
    """Why the system should decline to judge, or ``None`` to proceed.

    Abstention is not a soft rejection. Rejection says "this patch is wrong";
    abstention says "this system could not establish whether it is right", which
    is a different and often more honest statement.
    """
    claim = ctx.diagnosis

    if not claim.surviving_hypothesis_ids:
        return "no hypothesis survived its falsification probes"

    if claim.hypothesis_id is None:
        return "no diagnosis could be selected from the surviving hypotheses"

    supporting = len(claim.supporting_evidence_ids)
    contradicting = len(claim.contradicting_evidence_ids)
    if supporting and contradicting and contradicting >= supporting:
        return (
            f"evidence remains materially contradictory "
            f"({supporting} supporting, {contradicting} contradicting)"
        )

    if not claim.mechanism_linked_to_repair:
        return (
            "the system could not establish that the patch addresses the causal "
            "mechanism identified by the diagnosis"
        )

    return None


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


def decide(
    run_id: str,
    ctx: GateContext,
    *,
    infrastructure_failed: bool = False,
    infrastructure_detail: str = "",
) -> ReliabilityDecision:
    """Produce the terminal decision.

    Order matters, and it is:

    1. **Infrastructure failure.** A broken harness must never be reported as a
       failed patch. This covers an explicit harness error, an unreachable
       Temporal or Phoenix, a worker that never recovered, a corrupt artifact —
       and, since ADR-0012, a **missing mandatory observability artifact**. A
       missing trace blocks acceptance but implies nothing about the patch, so
       routing it to ``rejected`` would have been a fabricated coding verdict.
    2. **Observational rejection.** If a direct measurement of the patched
       repository failed — it does not build, a test regressed, hidden tests
       failed, the invariant is violated, a prohibited file changed, or the effect
       counter shows duplicate processing — the system has established something
       concrete and says so, even if the investigation was otherwise inconclusive.
    3. **Abstention.** Only now, when nothing was directly observed to be wrong but
       the diagnosis could not be established.
    4. **Remaining gates**, then acceptance for review.

    Step 2 preceding step 3 is deliberate. The duct-tape patch reaches step 2 with
    an effect counter of 2: that is a measurement, not an uncertainty, and calling
    it "abstained" would understate a finding the system genuinely made.
    """
    caveats = list(ctx.caveats)
    if not ctx.durable_execution:
        caveats.append(
            "NON_DURABLE_EXECUTION: this run used the degraded local executor; it "
            "demonstrates nothing about crash recovery or retry behaviour"
        )

    results = evaluate_gates(ctx)
    failed = [gate.gate_name for gate in results if not gate.passed]

    # Step 1: anything wrong with the harness, before any verdict on the patch.
    incidents = infrastructure_incidents(ctx)
    if infrastructure_failed or incidents:
        if infrastructure_failed and InfrastructureIncident.HARNESS_ERROR.value not in incidents:
            incidents = (*incidents, InfrastructureIncident.HARNESS_ERROR.value)

        detail = infrastructure_detail or "the evaluation harness failed"
        incident_results = tuple(
            GateResult(
                gate_name=f"infrastructure:{kind}",
                passed=False,
                detail=(
                    detail
                    if kind == InfrastructureIncident.HARNESS_ERROR.value
                    else _INCIDENT_DETAIL.get(kind, kind)
                ),
            )
            for kind in incidents
        )
        return ReliabilityDecision(
            run_id=run_id,
            outcome="infrastructure_failure",
            # Patch-level gate results are still reported, so a reader can see
            # what was measured — but none of them decided this outcome.
            gate_results=incident_results + results,
            rationale=(
                "The harness could not complete the evaluation "
                f"({', '.join(incidents)}). This says nothing about whether the "
                "patch is correct: no patch verdict was reached."
            ),
            caveats=tuple(caveats),
            durable_execution=ctx.durable_execution,
        )

    # Step 2: a direct measurement that failed outranks "we could not tell".
    observational_failures = [name for name in failed if name in OBSERVATIONAL_GATE_NAMES]
    if observational_failures:
        return ReliabilityDecision(
            run_id=run_id,
            outcome="rejected",
            gate_results=results,
            rationale=(
                f"Rejected by {len(observational_failures)} observational gate(s): "
                f"{', '.join(observational_failures)}."
            ),
            caveats=tuple(caveats),
            durable_execution=ctx.durable_execution,
        )

    # Step 3: nothing measurably wrong, but the investigation is inconclusive.
    reason = abstention_reason(ctx)
    if reason is not None:
        return ReliabilityDecision(
            run_id=run_id,
            outcome="abstained",
            gate_results=(GateResult(gate_name="abstention", passed=False, detail=reason),),
            rationale=f"Abstained: {reason}.",
            caveats=tuple(caveats),
            durable_execution=ctx.durable_execution,
        )

    if failed:
        return ReliabilityDecision(
            run_id=run_id,
            outcome="rejected",
            gate_results=results,
            rationale=f"Rejected by {len(failed)} gate(s): {', '.join(failed)}.",
            caveats=tuple(caveats),
            durable_execution=ctx.durable_execution,
        )

    return ReliabilityDecision(
        run_id=run_id,
        outcome="accepted_for_review",
        gate_results=results,
        rationale=(
            "All reliability gates passed. This patch is forwarded for human "
            "review only. No claim is made that it is correct, safe, calibrated, "
            "or ready for production, and it is not merged or deployed."
        ),
        caveats=tuple(caveats),
        durable_execution=ctx.durable_execution,
    )
