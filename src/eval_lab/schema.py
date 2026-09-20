"""Provider-neutral canonical records used by every Eval Lab judge."""

from __future__ import annotations

import math
from collections.abc import Mapping
from enum import Enum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Split(str, Enum):
    """Supported data splits."""

    TRAIN = "train"
    DEV = "dev"
    CALIBRATION = "calibration"
    TEST = "test"


class GoldProvenance(str, Enum):
    """Origin of an objective or explicitly weak gold label."""

    DETERMINISTIC_VERIFIER = "deterministic_verifier"
    ANSWER_KEY = "answer_key"
    EXECUTABLE_TEST = "executable_test"
    HUMAN_ADJUDICATION = "human_adjudication"
    WEAK_MODEL_SUPERVISION = "weak_model_supervision"


class JudgmentMode(str, Enum):
    """Whether a judge evaluates one candidate or compares two."""

    SINGLE = "single"
    PAIRWISE = "pairwise"


class PairwiseLabel(str, Enum):
    """Gold label for a pairwise candidate comparison."""

    A = "A"
    B = "B"
    TIE = "TIE"


class ExecutionStatus(str, Enum):
    """Execution outcome for a provider prediction."""

    OK = "ok"
    RATE_LIMITED = "rate_limited"
    PROVIDER_ERROR = "provider_error"
    PARSE_ERROR = "parse_error"
    SKIPPED = "skipped"


class CanonicalModel(BaseModel):
    """Shared strict configuration for canonical records."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def _copy_alias(data: Any, target: str, *aliases: str) -> Any:
    if not isinstance(data, Mapping):
        return data
    copied = dict(data)
    if target not in copied:
        for alias in aliases:
            if alias in copied:
                copied[target] = copied[alias]
                break
    for alias in aliases:
        copied.pop(alias, None)
    return copied


class RubricCriterion(CanonicalModel):
    """One stable, human-readable criterion applied to a candidate."""

    criterion_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    weight: float | None = Field(default=None, gt=0)
    aggregation_rule: str | None = None

    @model_validator(mode="before")
    @classmethod
    def accept_stable_id_aliases(cls, data: Any) -> Any:
        return _copy_alias(data, "criterion_id", "id", "stable_id")


class SourceRecord(CanonicalModel):
    """A source problem and its answer-key/reference material."""

    source_id: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    source_dataset: str = Field(min_length=1)
    source_problem_id: str = Field(min_length=1)
    split: Split
    prompt: str = Field(min_length=1)
    reference_answer: Any
    source_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_stable_id_aliases(cls, data: Any) -> Any:
        return _copy_alias(data, "source_id", "id", "stable_id")

    @property
    def stable_id(self) -> str:
        return self.source_id


class GoldLabel(CanonicalModel):
    """A label plus the evidence and provenance that justify it."""

    label: str = Field(min_length=1)
    provenance: GoldProvenance
    evidence: Any
    verifier_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode="before")
    @classmethod
    def accept_verifier_aliases(cls, data: Any) -> Any:
        return _copy_alias(data, "verifier_id", "verifier_version")


class JudgeRecord(CanonicalModel):
    """Canonical input and objective label for one judge decision."""

    record_id: str = Field(min_length=1)
    source_problem_id: str = Field(min_length=1)
    mode: JudgmentMode
    prompt: str = Field(min_length=1)
    rubric: list[RubricCriterion] = Field(min_length=1)
    candidate_a: str = Field(min_length=1)
    candidate_b: str | None = None
    gold: GoldLabel
    split: Split
    perturbation: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_stable_id_aliases(cls, data: Any) -> Any:
        return _copy_alias(data, "record_id", "id", "stable_id")

    @model_validator(mode="after")
    def validate_mode_shape(self) -> Self:
        if self.mode is JudgmentMode.PAIRWISE and not self.candidate_b:
            raise ValueError("pairwise records require candidate_b")
        if self.mode is JudgmentMode.SINGLE and self.candidate_b is not None:
            raise ValueError("single records must not include candidate_b")
        if self.mode is JudgmentMode.PAIRWISE:
            pairwise_labels = {item.value for item in PairwiseLabel}
            if self.gold.label not in pairwise_labels:
                raise ValueError("pairwise gold label must be A, B, or TIE")
        return self

    @property
    def stable_id(self) -> str:
        return self.record_id


def _validate_probabilities(value: Any) -> dict[str, float] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping) or not value:
        raise ValueError("probabilities must be a non-empty mapping")

    probabilities: dict[str, float] = {}
    for label, probability in value.items():
        if isinstance(probability, bool):
            raise TypeError("probabilities must be numeric")
        try:
            numeric = float(probability)
        except (TypeError, ValueError) as exc:
            raise ValueError("probabilities must be numeric") from exc
        if not math.isfinite(numeric) or numeric < 0 or numeric > 1:
            raise ValueError("probabilities must be finite values in [0, 1]")
        probabilities[str(label)] = numeric

    if not math.isclose(sum(probabilities.values()), 1.0, rel_tol=0, abs_tol=1e-6):
        raise ValueError("probabilities must sum to 1 within tolerance")
    return probabilities


class JudgePrediction(CanonicalModel):
    """A judge output with explicit execution state and optional probabilities."""

    record_id: str = Field(min_length=1)
    judge_id: str = Field(min_length=1)
    protocol_version: str = Field(min_length=1)
    label: str | None = None
    probabilities: dict[str, float] | None = None
    raw_scores: dict[str, float] | None = None
    execution_status: ExecutionStatus = ExecutionStatus.OK
    latency_ms: float | None = Field(default=None, ge=0)
    token_usage: dict[str, int | float] | None = None
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def accept_prediction_aliases(cls, data: Any) -> Any:
        data = _copy_alias(data, "record_id", "id", "stable_id")
        data = _copy_alias(data, "protocol_version", "prompt_version")
        data = _copy_alias(data, "probabilities", "probability_map")
        return data

    @field_validator("probabilities", mode="before")
    @classmethod
    def validate_probabilities(cls, value: Any) -> dict[str, float] | None:
        return _validate_probabilities(value)

    @model_validator(mode="after")
    def validate_execution(self) -> Self:
        if self.execution_status is ExecutionStatus.OK and self.label is None:
            raise ValueError("successful predictions require a label")
        return self


def swap_pairwise_record(record: JudgeRecord) -> JudgeRecord:
    """Return an A/B-swapped pairwise record with an inverted non-tie gold label."""

    if record.mode is not JudgmentMode.PAIRWISE:
        raise ValueError("only pairwise records can be swapped")
    inverted = {
        PairwiseLabel.A.value: PairwiseLabel.B.value,
        PairwiseLabel.B.value: PairwiseLabel.A.value,
        PairwiseLabel.TIE.value: PairwiseLabel.TIE.value,
    }[record.gold.label]
    payload = record.model_dump(mode="python")
    payload["candidate_a"], payload["candidate_b"] = record.candidate_b, record.candidate_a
    payload["gold"] = {**record.gold.model_dump(mode="python"), "label": inverted}
    payload["perturbation"] = {
        **record.perturbation,
        "kind": "ab_swap",
        "source_record_id": record.record_id,
    }
    return JudgeRecord.model_validate(payload)


__all__ = [
    "ExecutionStatus",
    "GoldLabel",
    "GoldProvenance",
    "JudgePrediction",
    "JudgeRecord",
    "JudgmentMode",
    "PairwiseLabel",
    "RubricCriterion",
    "SourceRecord",
    "Split",
    "swap_pairwise_record",
]
