"""Simple deterministic output verification for executable-style records."""

from __future__ import annotations

from typing import Any

from eval_lab.verifiers import VerifierResult, result

VERIFIER_ID = "code-output-v1"


def _normalize(value: Any) -> str:
    return "\n".join(line.rstrip() for line in str(value).strip().splitlines())


def verify_code_output(candidate: str, expected: Any) -> VerifierResult:
    """Compare normalized stdout-like text without executing candidate code."""

    candidate_output = _normalize(candidate)
    expected_output = _normalize(expected)
    return result(
        candidate_output == expected_output,
        evidence={
            "candidate_output": candidate_output,
            "expected_output": expected_output,
        },
        verifier_id=VERIFIER_ID,
    )


check_code_output = verify_code_output

__all__ = ["check_code_output", "verify_code_output"]
