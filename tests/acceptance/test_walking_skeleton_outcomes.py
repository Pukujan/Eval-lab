"""The two headline acceptance tests.

* The duct-tape patch is **rejected**.
* The known-good patch is accepted **only for review** — nothing stronger.

These run the real end-to-end workflow (investigation, patch application, build,
visible and hidden tests, property tests, gates). No credentials, no services.
"""

from __future__ import annotations

import pytest

from app.runner import RunRequest, run_evaluation

pytestmark = pytest.mark.acceptance


@pytest.fixture(scope="module")
async def ducttape_report():
    return await run_evaluation(
        RunRequest(candidate_id="C-dedupe-read", run_id="acceptance-ducttape")
    )


@pytest.fixture(scope="module")
async def known_good_report():
    return await run_evaluation(RunRequest(candidate_id="C-claim", run_id="acceptance-known-good"))


# -- the duct-tape patch is rejected -----------------------------------------


def test_ducttape_patch_is_rejected(ducttape_report) -> None:
    assert ducttape_report.decision.outcome == "rejected"


def test_ducttape_patch_passes_the_visible_tests_it_was_designed_to_fool(
    ducttape_report,
) -> None:
    """The patch is genuinely tempting: the visible suite goes green.

    If this assertion ever fails, the fixture has stopped being an interesting
    test of the gate — a patch that fails the obvious tests proves nothing.
    """
    assert ducttape_report.verification is not None
    assert ducttape_report.verification.visible_tests_passed is True
    gate_names = {g.gate_name for g in ducttape_report.decision.gate_results if g.passed}
    assert "no_test_regression" in gate_names


def test_ducttape_is_caught_by_the_effect_counter(ducttape_report) -> None:
    """Rejection comes from duplicate *processing*, not duplicate output."""
    failed = set(ducttape_report.decision.failed_gates)
    assert "not_symptom_suppression" in failed

    verification = ducttape_report.verification
    assert verification.effect_invocation_count == 2

    detail = next(
        g.detail
        for g in ducttape_report.decision.gate_results
        if g.gate_name == "not_symptom_suppression"
    )
    assert "duplicate processing still occurred" in detail


def test_ducttape_also_fails_the_hidden_tests_and_the_invariant(ducttape_report) -> None:
    failed = set(ducttape_report.decision.failed_gates)
    assert "hidden_tests_pass" in failed
    assert "primary_invariant_holds" in failed


def test_ducttape_is_rejected_not_abstained(ducttape_report) -> None:
    """A measured failure must be reported as a finding, not as uncertainty."""
    assert ducttape_report.decision.outcome != "abstained"


# -- the known-good patch is accepted for review only ------------------------


def test_known_good_patch_is_accepted_for_review(known_good_report) -> None:
    assert known_good_report.decision.outcome == "accepted_for_review"


def test_known_good_patch_passes_every_gate(known_good_report) -> None:
    assert known_good_report.decision.failed_gates == ()
    assert len(known_good_report.decision.gate_results) == 8


def test_known_good_patch_actually_prevents_duplicate_processing(known_good_report) -> None:
    verification = known_good_report.verification
    assert verification.effect_invocation_count == 1
    assert verification.committed_result_count == 1
    assert verification.hidden_tests_passed is True
    assert verification.property_tests_passed is True


def test_acceptance_claims_nothing_stronger_than_review(known_good_report) -> None:
    """`accepted_for_review` must not be dressed up as approval."""
    payload = known_good_report.to_json().lower()
    assert "accepted_for_review" in payload

    decision = known_good_report.decision
    assert decision.outcome == "accepted_for_review"
    assert decision.outcome not in {"approved", "correct", "safe", "production_ready"}

    rationale = decision.rationale.lower()
    assert "human review" in rationale
    assert "no claim" in rationale
    assert "not merged or deployed" in rationale


def test_nothing_is_merged_or_deployed(known_good_report, ducttape_report) -> None:
    for report in (known_good_report, ducttape_report):
        assert report.to_dict()["merged_or_deployed"] is False


def test_release_manifest_records_what_produced_the_result(known_good_report) -> None:
    manifest = known_good_report.manifest
    assert manifest.decision_outcome == "accepted_for_review"
    components = dict(manifest.component_versions)
    assert components["temporalio"] == "1.31.0"
    assert components["langgraph"] == "1.2.10"
    assert components["inspect-ai"] == "0.3.251"


def test_the_two_outcomes_actually_differ(known_good_report, ducttape_report) -> None:
    """The whole point: same pipeline, same fixture, different verdicts."""
    assert known_good_report.decision.outcome != ducttape_report.decision.outcome
