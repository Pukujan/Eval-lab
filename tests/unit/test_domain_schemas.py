"""Domain-schema unit tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domain.schemas import (
    ALL_SCHEMAS,
    Assumption,
    Evidence,
    EvidencePolarity,
    GateResult,
    InvariantKind,
    ProblemSpecification,
    ReliabilityDecision,
    RootCauseHypothesis,
    SystemInvariant,
)


def test_every_required_schema_is_defined() -> None:
    names = {schema.__name__ for schema in ALL_SCHEMAS}
    assert names == {
        "ProblemSpecification",
        "SystemInvariant",
        "RootCauseHypothesis",
        "Assumption",
        "Evidence",
        "FalsificationProbe",
        "ProbeResult",
        "RepairCandidate",
        "PatchArtifact",
        "VerificationResult",
        "ReliabilityDecision",
        "EvaluationRun",
        "AnonymousModelIdentity",
        "PrivilegedModelIdentity",
        "ReleaseManifest",
    }


@pytest.mark.parametrize("schema", ALL_SCHEMAS, ids=lambda s: s.__name__)
def test_every_schema_is_versioned_frozen_and_strict(schema) -> None:
    assert "schema_version" in schema.model_fields, f"{schema.__name__} is not versioned"
    assert schema.model_config.get("frozen") is True
    assert schema.model_config.get("extra") == "forbid"


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Assumption(assumption_id="A-1", statement="x", unexpected="boom")


def test_evidence_requires_a_real_sha256() -> None:
    with pytest.raises(ValidationError):
        Evidence(
            evidence_id="E-1",
            source="probe",
            polarity=EvidencePolarity.SUPPORTING,
            summary="s",
            payload_sha256="not-a-digest",
        )


def test_hypothesis_requires_assumptions_and_predictions() -> None:
    with pytest.raises(ValidationError):
        RootCauseHypothesis(
            hypothesis_id="H-1",
            causal_mechanism="m",
            mechanism_class="c",
            assumptions=(),
            predicted_observations=("p",),
            falsification_condition="f",
            proposed_probe_id="P-1",
        )


def test_specification_requires_exactly_one_primary_invariant() -> None:
    two_primaries = (
        SystemInvariant(
            invariant_id="INV-1", statement="a", kind=InvariantKind.PRIMARY, check_reference="r"
        ),
        SystemInvariant(
            invariant_id="INV-2", statement="b", kind=InvariantKind.PRIMARY, check_reference="r"
        ),
    )
    with pytest.raises(ValidationError):
        ProblemSpecification(
            specification_id="s",
            title="t",
            reported_symptom="sym",
            repository_path="/tmp",
            expected_behaviour="e",
            invariants=two_primaries,
        )


def test_decision_must_cite_gate_evidence() -> None:
    with pytest.raises(ValidationError):
        ReliabilityDecision(
            run_id="r", outcome="accepted_for_review", gate_results=(), rationale="because"
        )


def test_decision_outcome_is_restricted_to_terminal_states() -> None:
    for forbidden in ("approved", "correct", "safe", "production_ready"):
        with pytest.raises(ValidationError):
            ReliabilityDecision(
                run_id="r",
                outcome=forbidden,
                gate_results=(GateResult(gate_name="g", passed=True, detail="d"),),
                rationale="x",
            )


def test_content_hash_is_stable_and_sensitive() -> None:
    first = Assumption(assumption_id="A-1", statement="same")
    second = Assumption(assumption_id="A-1", statement="same")
    different = Assumption(assumption_id="A-1", statement="different")
    assert first.content_hash() == second.content_hash()
    assert first.content_hash() != different.content_hash()


def test_models_are_immutable() -> None:
    assumption = Assumption(assumption_id="A-1", statement="x")
    with pytest.raises(ValidationError):
        assumption.statement = "y"
