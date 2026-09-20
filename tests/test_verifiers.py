import json

from eval_lab.schema import GoldProvenance
from eval_lab.verifiers import (
    verify_arithmetic,
    verify_code_output,
    verify_multiple_choice,
    verify_structured_output,
)


def test_arithmetic_verifier_is_deterministic() -> None:
    passed = verify_arithmetic("12", 12)
    failed = verify_arithmetic("13", 12)
    assert passed.is_correct is True
    assert failed.is_correct is False
    assert passed.to_gold_label().provenance is GoldProvenance.DETERMINISTIC_VERIFIER


def test_multiple_choice_verifier_accepts_explanation_suffix() -> None:
    assert verify_multiple_choice("B) Paris", "B").is_correct is True
    assert verify_multiple_choice("C", "B").is_correct is False


def test_structured_verifier_requires_exact_json_value() -> None:
    expected = {"status": "ready", "count": 3}
    assert verify_structured_output(json.dumps(expected), expected).is_correct is True
    assert verify_structured_output('{"status":"ready","count":4}', expected).is_correct is False
    assert verify_structured_output("not json", expected).is_correct is False


def test_code_output_verifier_normalizes_trailing_whitespace() -> None:
    assert verify_code_output("1\n2\n3\n", "1\n2\n3").is_correct is True
    assert verify_code_output("1\n3\n2", "1\n2\n3").is_correct is False
