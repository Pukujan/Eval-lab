"""Failure-classification tests (ADR-0012).

The distinction this file defends:

* an incorrect patch or a failed invariant -> ``rejected``
* insufficient or contradictory evidence    -> ``abstained``
* anything wrong with the harness           -> ``infrastructure_failure``

The last row is the one that changed in Task 2A. A missing mandatory observability
artifact used to be a rejection gate, which meant a dropped span could be reported
as "your patch is wrong". It now blocks acceptance as an infrastructure failure and
says explicitly that no patch verdict was reached.
"""

from __future__ import annotations

import pytest

from app.domain.schemas import VerificationResult
from app.reliability.gates import (
    GATE_REQUIRED_SPAN_NAMES,
    INFRASTRUCTURE_INCIDENT_KINDS,
    REJECTION_GATES,
    DiagnosisClaim,
    GateContext,
    InfrastructureIncident,
    classify_infrastructure_incident,
    decide,
    infrastructure_incidents,
)


def _verification(**overrides) -> VerificationResult:
    defaults = dict(
        candidate_id="C",
        patch_id="P",
        build_succeeded=True,
        visible_tests_passed=True,
        visible_tests_passing_before=("a::t1",),
        visible_tests_passing_after=("a::t1",),
        hidden_tests_passed=True,
        property_tests_passed=True,
        invariant_holds=True,
        effect_invocation_count=1,
        committed_result_count=1,
    )
    defaults.update(overrides)
    return VerificationResult(**defaults)


def _healthy_context(**overrides) -> GateContext:
    defaults = dict(
        verification=_verification(),
        diagnosis=DiagnosisClaim(
            hypothesis_id="H-1",
            supporting_evidence_ids=frozenset({"E-1"}),
            contradicting_evidence_ids=frozenset(),
            mechanism_linked_to_repair=True,
            surviving_hypothesis_ids=frozenset({"H-1"}),
        ),
        recorded_evidence_ids=frozenset({"E-1"}),
        recorded_span_names=frozenset(GATE_REQUIRED_SPAN_NAMES),
        audit_run_recorded=True,
    )
    defaults.update(overrides)
    return GateContext(**defaults)


# -- the classifier guard ----------------------------------------------------


@pytest.mark.parametrize("kind", sorted(INFRASTRUCTURE_INCIDENT_KINDS))
def test_every_known_incident_classifies_as_infrastructure_failure(kind: str) -> None:
    assert classify_infrastructure_incident(kind) == "infrastructure_failure"


def test_unknown_conditions_cannot_be_laundered_into_infrastructure() -> None:
    """A patch failure must not be excusable by calling it infrastructure."""
    for bogus in ("hidden_tests_failed", "invariant_violated", "patch_is_bad", ""):
        with pytest.raises(ValueError, match="not a recognised infrastructure incident"):
            classify_infrastructure_incident(bogus)


# -- missing observability artifacts -----------------------------------------


def test_missing_mandatory_trace_is_infrastructure_not_rejection() -> None:
    """The headline behaviour change: a dropped span is not a bad patch."""
    context = _healthy_context(recorded_span_names=frozenset({"coding-evaluation"}))

    incidents = infrastructure_incidents(context)
    assert InfrastructureIncident.MISSING_MANDATORY_TRACE.value in incidents

    decision = decide("run-missing-trace", context)
    assert decision.outcome == "infrastructure_failure"
    assert decision.outcome != "rejected"


def test_missing_trace_blocks_acceptance(_=None) -> None:
    context = _healthy_context(recorded_span_names=frozenset({"coding-evaluation"}))
    assert decide("run-block", context).outcome != "accepted_for_review"


def test_missing_trace_decision_states_no_patch_verdict_was_reached() -> None:
    context = _healthy_context(recorded_span_names=frozenset())
    decision = decide("run-detail", context)
    assert "implies nothing about whether the patch is correct" in " ".join(
        gate.detail for gate in decision.gate_results
    )
    assert "no patch verdict was reached" in decision.rationale


def test_missing_audit_record_is_infrastructure() -> None:
    context = _healthy_context(audit_run_recorded=False)
    assert decide("run-no-audit", context).outcome == "infrastructure_failure"


# -- explicit incidents ------------------------------------------------------


@pytest.mark.parametrize(
    "incident",
    [
        InfrastructureIncident.TEMPORAL_UNAVAILABLE,
        InfrastructureIncident.PHOENIX_UNAVAILABLE,
        InfrastructureIncident.WORKER_FAILURE_WITHOUT_RECOVERY,
        InfrastructureIncident.CORRUPT_EVALUATION_ARTIFACT,
        InfrastructureIncident.ACTIVITY_TIMEOUT,
    ],
)
def test_declared_incidents_force_infrastructure_failure(incident) -> None:
    """Even with a perfect patch, a broken harness yields no patch verdict."""
    context = _healthy_context(infrastructure_incidents=(incident.value,))
    decision = decide("run-incident", context)

    assert decision.outcome == "infrastructure_failure"
    assert any(g.gate_name == f"infrastructure:{incident.value}" for g in decision.gate_results)


def test_infrastructure_outranks_a_genuinely_bad_patch() -> None:
    """When the harness is broken we cannot honestly judge the patch at all.

    The duct-tape patch really is wrong, but if the trace is missing we did not
    establish that *this run*; claiming otherwise would be reporting a verdict we
    did not reach.
    """
    context = _healthy_context(
        verification=_verification(effect_invocation_count=2, hidden_tests_passed=False),
        infrastructure_incidents=(InfrastructureIncident.TEMPORAL_UNAVAILABLE.value,),
    )
    decision = decide("run-both", context)
    assert decision.outcome == "infrastructure_failure"

    # The measurements are still reported, so nothing is hidden from a reader.
    names = {g.gate_name for g in decision.gate_results}
    assert "not_symptom_suppression" in names
    assert "hidden_tests_pass" in names


# -- the other two rows of the table remain intact ---------------------------


def test_bad_patch_still_rejects_when_the_harness_is_healthy() -> None:
    context = _healthy_context(
        verification=_verification(
            effect_invocation_count=2, hidden_tests_passed=False, invariant_holds=False
        )
    )
    assert decide("run-bad-patch", context).outcome == "rejected"


def test_contradictory_evidence_still_abstains_when_the_harness_is_healthy() -> None:
    context = _healthy_context(
        diagnosis=DiagnosisClaim(
            hypothesis_id="H-1",
            supporting_evidence_ids=frozenset({"E-1"}),
            contradicting_evidence_ids=frozenset({"E-2", "E-3"}),
            mechanism_linked_to_repair=True,
            surviving_hypothesis_ids=frozenset({"H-1"}),
        ),
        recorded_evidence_ids=frozenset({"E-1", "E-2", "E-3"}),
    )
    assert decide("run-contradictory", context).outcome == "abstained"


def test_healthy_run_still_reaches_accepted_for_review() -> None:
    assert decide("run-clean", _healthy_context()).outcome == "accepted_for_review"


# -- structural guarantees ---------------------------------------------------


def test_artifact_gate_is_not_a_patch_rejection_gate() -> None:
    """`required_artifacts_present` must not sit among the patch verdicts."""
    names = {gate.__name__ for gate in REJECTION_GATES}
    assert "required_artifacts_present" not in names
    assert len(REJECTION_GATES) == 7


def test_all_four_terminal_outcomes_remain_reachable() -> None:
    outcomes = {
        decide("a", _healthy_context()).outcome,
        decide(
            "b", _healthy_context(verification=_verification(hidden_tests_passed=False))
        ).outcome,
        decide(
            "c",
            _healthy_context(
                diagnosis=DiagnosisClaim(hypothesis_id=None, surviving_hypothesis_ids=frozenset())
            ),
        ).outcome,
        decide(
            "d",
            _healthy_context(
                infrastructure_incidents=(InfrastructureIncident.TEMPORAL_UNAVAILABLE.value,)
            ),
        ).outcome,
    }
    assert outcomes == {"accepted_for_review", "rejected", "abstained", "infrastructure_failure"}
