"""Deterministic JSON-object verification."""

from __future__ import annotations

import json
from typing import Any

from eval_lab.verifiers import VerifierResult, result

VERIFIER_ID = "structured-output-v1"


def verify_structured_output(candidate: str, expected: Any) -> VerifierResult:
    """Parse a JSON object and compare it to the expected object exactly."""

    try:
        parsed = json.loads(candidate)
        parse_error = None
    except (json.JSONDecodeError, TypeError) as exc:
        parsed = None
        parse_error = str(exc)

    is_correct = parse_error is None and parsed == expected
    evidence: dict[str, Any] = {
        "candidate": str(candidate),
        "parsed": parsed,
        "expected": expected,
    }
    if parse_error:
        evidence["error"] = parse_error
    return result(is_correct, evidence=evidence, verifier_id=VERIFIER_ID)


check_structured_output = verify_structured_output

__all__ = ["check_structured_output", "verify_structured_output"]
