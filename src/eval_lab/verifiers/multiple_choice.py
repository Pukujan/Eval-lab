"""Answer-key verification for short multiple-choice responses."""

from __future__ import annotations

import re
from typing import Any

from eval_lab.verifiers import VerifierResult, result

VERIFIER_ID = "multiple-choice-v1"
_ANSWER_RE = re.compile(r"^([A-Za-z])(?:[.)\s]|$)")


def _choice(value: Any) -> str:
    match = _ANSWER_RE.match(str(value).strip())
    return (match.group(1) if match else str(value).strip()).upper()


def verify_multiple_choice(candidate: str, expected: Any) -> VerifierResult:
    """Verify the selected option letter, allowing a short explanatory suffix."""

    expected_value = expected.get("answer") if isinstance(expected, dict) else expected
    candidate_choice = _choice(candidate)
    expected_choice = _choice(expected_value)
    return result(
        candidate_choice == expected_choice,
        evidence={
            "candidate": str(candidate),
            "candidate_choice": candidate_choice,
            "expected_choice": expected_choice,
        },
        verifier_id=VERIFIER_ID,
    )


check_multiple_choice = verify_multiple_choice

__all__ = ["check_multiple_choice", "verify_multiple_choice"]
