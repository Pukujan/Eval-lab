"""Safe HumanEval execution-status models.

This module consumes already-produced, trusted execution metadata. It never
executes candidate code and cannot turn infrastructure or provider failures
into objective gold labels.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from eval_lab.verifiers import VerifierResult, result

HUMANEVAL_VERIFIER_ID = "humaneval-executable-tests-v1"


class HumanEvalStatus(str, Enum):
    PASS = "pass"
    TEST_FAILURE = "test_failure"
    SYNTAX_ERROR = "syntax_error"
    TIMEOUT = "timeout"
    CRASH = "crash"
    IMPORT_ERROR = "import_error"
    VERIFIER_ERROR = "verifier_error"
    SANDBOX_UNAVAILABLE = "sandbox_unavailable"
    MALFORMED_OUTPUT = "malformed_output"
    PROVIDER_FAILURE = "provider_failure"


_GOLD_ELIGIBLE = {
    HumanEvalStatus.PASS,
    HumanEvalStatus.TEST_FAILURE,
    HumanEvalStatus.SYNTAX_ERROR,
}


class HumanEvalExecutionResult(BaseModel):
    """A trusted/mock execution result, not an executor."""

    model_config = ConfigDict(extra="forbid")

    status: HumanEvalStatus
    stdout: str = ""
    stderr: str = ""
    duration_ms: float | None = Field(default=None, ge=0)
    test_count: int | None = Field(default=None, ge=0)
    evidence: dict[str, Any] = Field(default_factory=dict)

    @property
    def gold_eligible(self) -> bool:
        return self.status in _GOLD_ELIGIBLE

    @property
    def is_correct(self) -> bool:
        if not self.gold_eligible:
            raise ValueError(f"{self.status.value} cannot be converted to correctness gold")
        return self.status is HumanEvalStatus.PASS

    def to_verifier_result(self, *, verifier_id: str = HUMANEVAL_VERIFIER_ID) -> VerifierResult:
        """Convert only eligible pass/fail statuses into deterministic gold."""

        if not self.gold_eligible:
            raise ValueError(f"{self.status.value} is not eligible for deterministic gold")
        return result(
            self.is_correct,
            evidence={
                **self.evidence,
                "status": self.status.value,
                "stdout": self.stdout,
                "stderr": self.stderr,
                "duration_ms": self.duration_ms,
                "test_count": self.test_count,
            },
            verifier_id=verifier_id,
        )


def normalize_humaneval_status(value: HumanEvalStatus | str) -> HumanEvalStatus:
    """Normalize a status value without inferring one from free-form text."""

    if isinstance(value, HumanEvalStatus):
        return value
    try:
        return HumanEvalStatus(str(value).strip().lower())
    except ValueError as exc:
        raise ValueError(f"unknown HumanEval execution status: {value!r}") from exc


def build_humaneval_execution_result(
    status: HumanEvalStatus | str,
    *,
    stdout: str = "",
    stderr: str = "",
    duration_ms: float | None = None,
    test_count: int | None = None,
    evidence: dict[str, Any] | None = None,
) -> HumanEvalExecutionResult:
    """Build a typed result from a trusted runner or hand-written fixture."""

    return HumanEvalExecutionResult(
        status=normalize_humaneval_status(status),
        stdout=stdout,
        stderr=stderr,
        duration_ms=duration_ms,
        test_count=test_count,
        evidence=dict(evidence or {}),
    )


def verify_humaneval_execution(
    execution: HumanEvalExecutionResult,
    *,
    verifier_id: str = HUMANEVAL_VERIFIER_ID,
) -> VerifierResult:
    """Return gold only for pass/test-failure/syntax-error execution states."""

    return execution.to_verifier_result(verifier_id=verifier_id)


__all__ = [
    "HUMANEVAL_VERIFIER_ID",
    "HumanEvalExecutionResult",
    "HumanEvalStatus",
    "build_humaneval_execution_result",
    "normalize_humaneval_status",
    "verify_humaneval_execution",
]
