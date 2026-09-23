"""Exact arithmetic answer verification."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from eval_lab.verifiers import VerifierResult, result

VERIFIER_ID = "arithmetic-v1"


def _number(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise InvalidOperation
    return Decimal(str(value).strip().replace(",", ""))


def verify_arithmetic(candidate: str, expected: Any) -> VerifierResult:
    """Verify a numeric candidate against an answer-key value."""

    expected_number: Decimal | str
    try:
        candidate_number = _number(candidate)
        expected_number = _number(expected)
        is_correct = candidate_number == expected_number
        parse_error = None
    except (InvalidOperation, TypeError, ValueError):
        candidate_number = None
        expected_number = str(expected)
        is_correct = False
        parse_error = "candidate is not a valid decimal number"

    evidence = {
        "candidate": str(candidate),
        "expected": str(expected),
        "candidate_value": str(candidate_number) if candidate_number is not None else None,
        "expected_value": str(expected_number),
    }
    if parse_error:
        evidence["error"] = parse_error
    return result(is_correct, evidence=evidence, verifier_id=VERIFIER_ID)


check_arithmetic = verify_arithmetic

__all__ = ["check_arithmetic", "verify_arithmetic"]
