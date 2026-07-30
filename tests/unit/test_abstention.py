"""The three abstention conditions."""

from __future__ import annotations

from app.domain.schemas import VerificationResult
from app.reliability.gates import (
    GATE_REQUIRED_SPAN_NAMES,
    DiagnosisClaim,
    GateContext,
    abstention_reason,
    decide,
)


def _clean_verification() -> VerificationResult:
    """A verification with nothing observably wrong.

    Necessary: abstention is only reachable when no direct measurement failed,
    because an observed failure is reported as rejection instead.
    """
    return VerificationResult(
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


def _context(claim: DiagnosisClaim) -> GateContext:
    return GateContext(
        verification=_clean_verification(),
        diagnosis=claim,
        recorded_evidence_ids=frozenset({"E-1", "E-2", "E-3"}),
        recorded_span_names=frozenset(GATE_REQUIRED_SPAN_NAMES),
        audit_run_recorded=True,
    )


def test_abstains_when_no_hypothesis_survives() -> None:
    claim = DiagnosisClaim(hypothesis_id=None, surviving_hypothesis_ids=frozenset())
    reason = abstention_reason(_context(claim))
    assert reason is not None and "no hypothesis survived" in reason

    decision = decide("run-a", _context(claim))
    assert decision.outcome == "abstained"


def test_abstains_when_evidence_remains_materially_contradictory() -> None:
    claim = DiagnosisClaim(
        hypothesis_id="H-1",
        supporting_evidence_ids=frozenset({"E-1"}),
        contradicting_evidence_ids=frozenset({"E-2", "E-3"}),
        mechanism_linked_to_repair=True,
        surviving_hypothesis_ids=frozenset({"H-1"}),
    )
    reason = abstention_reason(_context(claim))
    assert reason is not None and "materially contradictory" in reason
    assert decide("run-b", _context(claim)).outcome == "abstained"


def test_abstains_when_the_repair_is_not_tied_to_the_mechanism() -> None:
    claim = DiagnosisClaim(
        hypothesis_id="H-1",
        supporting_evidence_ids=frozenset({"E-1"}),
        contradicting_evidence_ids=frozenset(),
        mechanism_linked_to_repair=False,
        surviving_hypothesis_ids=frozenset({"H-1"}),
    )
    reason = abstention_reason(_context(claim))
    assert reason is not None and "causal mechanism" in reason
    assert decide("run-c", _context(claim)).outcome == "abstained"


def test_no_abstention_when_the_diagnosis_is_established() -> None:
    claim = DiagnosisClaim(
        hypothesis_id="H-1",
        supporting_evidence_ids=frozenset({"E-1", "E-2"}),
        contradicting_evidence_ids=frozenset(),
        mechanism_linked_to_repair=True,
        surviving_hypothesis_ids=frozenset({"H-1"}),
    )
    assert abstention_reason(_context(claim)) is None
    assert decide("run-d", _context(claim)).outcome == "accepted_for_review"


def test_abstention_is_not_a_rejection() -> None:
    """The two outcomes make different claims and must stay distinguishable."""
    claim = DiagnosisClaim(hypothesis_id=None, surviving_hypothesis_ids=frozenset())
    decision = decide("run-e", _context(claim))
    assert decision.outcome == "abstained"
    assert decision.outcome != "rejected"
