from eval_lab.datasets.synthetic import generate_synthetic_fixtures
from scripts.generate_hard_negatives import _failure_mode, _parse_payload, _verify_candidate


def test_teacher_payload_requires_structured_candidate_fields() -> None:
    assert _parse_payload('{"candidate":"11","failure_mode":"arithmetic_near_miss","rationale":"off by one"}') == {
        "candidate": "11",
        "failure_mode": "arithmetic_near_miss",
        "rationale": "off by one",
    }
    assert _parse_payload('{"candidate":"11"}') is None


def test_failure_mode_falls_back_to_domain_taxonomy() -> None:
    assert _failure_mode("structured", "unknown-label") == "structured_field_mutation"
    assert _failure_mode("arithmetic", "unsupported_claim") == "unsupported_claim"


def test_accepted_candidate_requires_independent_verifier_failure() -> None:
    fixture = generate_synthetic_fixtures()
    source = next(item for item in fixture.sources if item.source_problem_id == "synthetic-arithmetic-02")
    verification = _verify_candidate(source, "11")
    correct = _verify_candidate(source, "12")

    assert verification["is_correct"] is False
    assert correct["is_correct"] is True
    assert verification["verifier_id"] == "arithmetic-v1"
