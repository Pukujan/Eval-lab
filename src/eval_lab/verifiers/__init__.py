"""Deterministic verifier primitives for objective fixture gold labels."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from eval_lab.schema import GoldLabel, GoldProvenance


class VerifierResult(BaseModel):
    """Stable result returned by every deterministic verifier."""

    model_config = ConfigDict(extra="forbid")

    is_correct: bool
    label: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    verifier_id: str = Field(min_length=1)

    @property
    def correct(self) -> bool:
        return self.is_correct

    def to_gold_label(self) -> GoldLabel:
        return GoldLabel(
            label=self.label,
            provenance=GoldProvenance.DETERMINISTIC_VERIFIER,
            evidence=self.evidence,
            verifier_id=self.verifier_id,
        )


def result(
    is_correct: bool,
    *,
    evidence: dict[str, Any],
    verifier_id: str,
) -> VerifierResult:
    return VerifierResult(
        is_correct=is_correct,
        label="pass" if is_correct else "fail",
        evidence=evidence,
        verifier_id=verifier_id,
    )


from eval_lab.verifiers.arithmetic import verify_arithmetic
from eval_lab.verifiers.code_output import verify_code_output
from eval_lab.verifiers.multiple_choice import verify_multiple_choice
from eval_lab.verifiers.structured import verify_structured_output

__all__ = [
    "VerifierResult",
    "result",
    "verify_arithmetic",
    "verify_code_output",
    "verify_multiple_choice",
    "verify_structured_output",
]
