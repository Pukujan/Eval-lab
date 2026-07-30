"""Reliability-gate tests: one passing and one failing case for every gate.

Driven entirely from synthetic artifacts — no model, no network, no subprocess.
That is only possible because the gates are pure functions of observable data
(ADR-0009), and it is the property that makes "deterministically rejected"
checkable rather than aspirational.
"""

from __future__ import annotations

import ast
from pathlib import Path

from app.domain.schemas import VerificationResult
from app.reliability.gates import (
    GATE_REQUIRED_SPAN_NAMES,
    DiagnosisClaim,
    GateContext,
    build_succeeds,
    decide,
    evaluate_gates,
    evidence_supports_diagnosis,
    hidden_tests_pass,
    no_prohibited_file_changes,
    no_test_regression,
    not_symptom_suppression,
    primary_invariant_holds,
    required_artifacts_present,
)


def _verification(**overrides) -> VerificationResult:
    defaults = dict(
        candidate_id="C-test",
        patch_id="patch-test",
        build_succeeded=True,
        visible_tests_passed=True,
        visible_tests_passing_before=("a::t1",),
        visible_tests_passing_after=("a::t1", "a::t2"),
        hidden_tests_passed=True,
        property_tests_passed=True,
        invariant_holds=True,
        effect_invocation_count=1,
        committed_result_count=1,
        prohibited_paths_touched=(),
    )
    defaults.update(overrides)
    return VerificationResult(**defaults)


def _claim(**overrides) -> DiagnosisClaim:
    defaults = dict(
        hypothesis_id="H-1",
        supporting_evidence_ids=frozenset({"E-1", "E-2"}),
        contradicting_evidence_ids=frozenset(),
        mechanism_linked_to_repair=True,
        surviving_hypothesis_ids=frozenset({"H-1"}),
    )
    defaults.update(overrides)
    return DiagnosisClaim(**defaults)


def _context(**overrides) -> GateContext:
    defaults = dict(
        verification=_verification(),
        diagnosis=_claim(),
        recorded_evidence_ids=frozenset({"E-1", "E-2"}),
        recorded_span_names=frozenset(GATE_REQUIRED_SPAN_NAMES),
        audit_run_recorded=True,
    )
    defaults.update(overrides)
    return GateContext(**defaults)


# -- the eight rejection conditions ------------------------------------------


def test_build_gate() -> None:
    assert build_succeeds(_context()).passed
    failing = _context(verification=_verification(build_succeeded=False))
    assert not build_succeeds(failing).passed


def test_regression_gate_detects_a_lost_pass() -> None:
    assert no_test_regression(_context()).passed
    regressed = _context(
        verification=_verification(
            visible_tests_passing_before=("a::t1", "a::t2"),
            visible_tests_passing_after=("a::t1",),
        )
    )
    result = no_test_regression(regressed)
    assert not result.passed
    assert "a::t2" in result.detail


def test_hidden_tests_gate() -> None:
    assert hidden_tests_pass(_context()).passed
    assert not hidden_tests_pass(
        _context(verification=_verification(hidden_tests_passed=False))
    ).passed


def test_primary_invariant_gate() -> None:
    assert primary_invariant_holds(_context()).passed
    violated = _context(verification=_verification(invariant_holds=False, committed_result_count=2))
    assert not primary_invariant_holds(violated).passed


def test_evidence_gate_rejects_unrecorded_evidence() -> None:
    assert evidence_supports_diagnosis(_context()).passed

    phantom = _context(
        diagnosis=_claim(supporting_evidence_ids=frozenset({"E-does-not-exist"})),
        recorded_evidence_ids=frozenset({"E-1"}),
    )
    result = evidence_supports_diagnosis(phantom)
    assert not result.passed
    assert "not present in the audit store" in result.detail


def test_evidence_gate_rejects_when_contradiction_outweighs_support() -> None:
    conflicted = _context(
        diagnosis=_claim(
            supporting_evidence_ids=frozenset({"E-1"}),
            contradicting_evidence_ids=frozenset({"E-2", "E-3"}),
        ),
        recorded_evidence_ids=frozenset({"E-1", "E-2", "E-3"}),
    )
    assert not evidence_supports_diagnosis(conflicted).passed


def test_prohibited_files_gate() -> None:
    assert no_prohibited_file_changes(_context()).passed
    touched = _context(
        verification=_verification(prohibited_paths_touched=("tests_hidden/test_x.py",))
    )
    assert not no_prohibited_file_changes(touched).passed


def test_symptom_suppression_gate_reads_the_effect_counter() -> None:
    """The gate that catches duct tape.

    Committed rows look clean and the invariant flag is set, but the external
    effect fired twice — so processing happened twice and the patch is a cover-up.
    """
    assert not_symptom_suppression(_context()).passed

    suppressed = _context(
        verification=_verification(
            committed_result_count=1,
            invariant_holds=True,
            visible_tests_passed=True,
            effect_invocation_count=2,
        )
    )
    result = not_symptom_suppression(suppressed)
    assert not result.passed
    assert "duplicate processing still occurred" in result.detail


def test_artifact_gate() -> None:
    assert required_artifacts_present(_context()).passed

    missing = _context(recorded_span_names=frozenset({"coding-evaluation"}))
    assert not required_artifacts_present(missing).passed

    no_audit = _context(audit_run_recorded=False)
    assert not required_artifacts_present(no_audit).passed


def test_all_eight_gates_are_evaluated() -> None:
    results = evaluate_gates(_context())
    assert len(results) == 8
    assert all(gate.passed for gate in results)


# -- decision composition -----------------------------------------------------


def test_clean_run_is_accepted_for_review_only() -> None:
    decision = decide("run-1", _context())

    # The outcome value is the load-bearing part: it is the only place a
    # stronger word could be claimed, and the schema restricts it to the four
    # terminal states.
    assert decision.outcome == "accepted_for_review"
    assert decision.outcome not in {"approved", "correct", "safe", "production_ready"}

    # The rationale is allowed — required, in fact — to use those words in the
    # course of denying them.
    rationale = decision.rationale.lower()
    assert "no claim is made that it is correct, safe, calibrated" in rationale
    assert "human" in rationale and "review" in rationale
    assert "not merged or deployed" in rationale


def test_infrastructure_failure_is_not_a_rejection() -> None:
    decision = decide(
        "run-2", _context(), infrastructure_failed=True, infrastructure_detail="disk full"
    )
    assert decision.outcome == "infrastructure_failure"
    assert "says nothing about whether the patch is correct" in decision.rationale
    assert "no patch verdict was reached" in decision.rationale


def test_observational_failure_outranks_abstention() -> None:
    """A measured failure must be reported as rejection, not as uncertainty."""
    context = _context(
        verification=_verification(effect_invocation_count=2, hidden_tests_passed=False),
        diagnosis=_claim(mechanism_linked_to_repair=False),
    )
    decision = decide("run-3", context)
    assert decision.outcome == "rejected"
    assert "not_symptom_suppression" in decision.failed_gates


def test_non_durable_execution_is_recorded_as_a_caveat() -> None:
    decision = decide("run-4", _context(durable_execution=False))
    assert any("NON_DURABLE_EXECUTION" in caveat for caveat in decision.caveats)
    assert decision.durable_execution is False


# -- the structural guarantee -------------------------------------------------


def test_gates_module_imports_no_model_client() -> None:
    """No model may sit in a verdict path — enforced by reading the imports."""
    source = Path("app/reliability/gates.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    forbidden = ("litellm", "openai", "anthropic", "httpx", "requests", "app.models")
    offenders = [name for name in imported if any(name.startswith(f) for f in forbidden)]
    assert not offenders, f"gates.py must not import a model client, found: {offenders}"
