"""Pure HumanEval canonicalization utilities.

This module validates supplied HumanEval-shaped rows and creates stable judge
records. It never downloads data and never executes candidate code.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from eval_lab.schema import GoldLabel, JudgeRecord, JudgmentMode, RubricCriterion, Split

HUMANEVAL_DATASET_ID = "openai/human-eval"
HUMANEVAL_CANONICALIZATION_VERSION = "humaneval-canonical-v1"
HUMANEVAL_VERIFIER_ID = "humaneval-executable-tests-v1"


def canonical_json(value: Any) -> bytes:
    """Return byte-stable JSON for fingerprints and record identities."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _required_text(row: Mapping[str, Any], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"HumanEval row requires non-empty string field {field!r}")
    return value


def validate_humaneval_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    """Validate and normalize supplied rows without retrieving or executing them."""

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise TypeError("HumanEval rows must be mappings")
        task_id = _required_text(row, "task_id").strip()
        if task_id in seen:
            raise ValueError(f"duplicate HumanEval task_id: {task_id}")
        seen.add(task_id)
        normalized.append(
            {
                "task_id": task_id,
                "prompt": _required_text(row, "prompt"),
                "entry_point": _required_text(row, "entry_point").strip(),
                "canonical_solution": _required_text(row, "canonical_solution"),
                "test": _required_text(row, "test"),
            }
        )
    if not normalized:
        raise ValueError("HumanEval rows must not be empty")
    return sorted(normalized, key=lambda item: item["task_id"])


def fingerprint_humaneval_rows(rows: Iterable[Mapping[str, Any]]) -> str:
    """Fingerprint normalized source rows in task-ID order."""

    return hashlib.sha256(canonical_json(validate_humaneval_rows(rows))).hexdigest()


def _rank(seed: int, task_id: str) -> str:
    return hashlib.sha256(f"{seed}:human_eval:{task_id}".encode()).hexdigest()


def assign_humaneval_splits(
    task_ids: Sequence[str],
    *,
    seed: int = 20260921,
    dev_fraction: float = 0.2,
    calibration_fraction: float = 0.2,
) -> dict[str, Split]:
    """Assign whole source families to deterministic dev/calibration/test splits."""

    if not task_ids or len(set(task_ids)) != len(task_ids):
        raise ValueError("task_ids must be a non-empty unique sequence")
    if not 0 <= dev_fraction < 1 or not 0 <= calibration_fraction < 1:
        raise ValueError("split fractions must be in [0, 1)")
    if dev_fraction + calibration_fraction >= 1:
        raise ValueError("dev and calibration fractions must leave a test split")

    ordered = sorted((str(task_id) for task_id in task_ids), key=lambda item: _rank(seed, item))
    dev_count = int(len(ordered) * dev_fraction)
    calibration_count = int(len(ordered) * calibration_fraction)
    assignments: dict[str, Split] = {}
    for index, task_id in enumerate(ordered):
        if index < dev_count:
            assignments[task_id] = Split.DEV
        elif index < dev_count + calibration_count:
            assignments[task_id] = Split.CALIBRATION
        else:
            assignments[task_id] = Split.TEST
    return assignments


class HumanEvalCandidate(BaseModel):
    """One candidate completion with stable identity and no hidden test material."""

    model_config = ConfigDict(extra="forbid")

    dataset_id: str = HUMANEVAL_DATASET_ID
    dataset_revision: str = Field(min_length=1)
    canonicalization_version: str = HUMANEVAL_CANONICALIZATION_VERSION
    task_id: str = Field(min_length=1)
    source_family_id: str = Field(min_length=1)
    entry_point: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    candidate_code: str
    candidate_sha256: str = Field(min_length=64, max_length=64)
    candidate_origin: str = Field(min_length=1)
    candidate_slot: int = Field(ge=0)
    split: Split
    record_id: str = Field(min_length=1)

    @field_validator("candidate_sha256")
    @classmethod
    def validate_candidate_hash(cls, value: str) -> str:
        if any(character not in "0123456789abcdef" for character in value.lower()):
            raise ValueError("candidate_sha256 must be lowercase hexadecimal")
        return value.lower()

    def to_judge_record(self, gold: GoldLabel) -> JudgeRecord:
        """Create the judge-facing record after a separate verifier supplies gold."""

        judge_prompt = f"{self.prompt}\n\nCandidate completion:\n{self.candidate_code}"
        return JudgeRecord(
            record_id=self.record_id,
            source_problem_id=self.task_id,
            mode=JudgmentMode.SINGLE,
            prompt=judge_prompt,
            rubric=[
                RubricCriterion(
                    criterion_id="executable-correctness",
                    description="The candidate passes the pinned executable tests.",
                    weight=1.0,
                    aggregation_rule="all",
                )
            ],
            candidate_a=self.candidate_code,
            gold=gold,
            split=self.split,
        )


def canonicalize_humaneval_row(
    row: Mapping[str, Any],
    candidate_code: str,
    *,
    dataset_revision: str,
    split: Split,
    candidate_origin: str = "fixture",
    candidate_slot: int = 0,
) -> HumanEvalCandidate:
    """Create one stable candidate record from a supplied row and code string."""

    normalized = validate_humaneval_rows([row])[0]
    if not isinstance(candidate_code, str):
        raise TypeError("candidate_code must be a string")
    if not candidate_origin.strip():
        raise ValueError("candidate_origin must not be empty")
    candidate_hash = hashlib.sha256(candidate_code.encode("utf-8")).hexdigest()
    identity = {
        "dataset_id": HUMANEVAL_DATASET_ID,
        "dataset_revision": dataset_revision,
        "task_id": normalized["task_id"],
        "candidate_sha256": candidate_hash,
        "candidate_origin": candidate_origin,
        "candidate_slot": candidate_slot,
    }
    record_id = hashlib.sha256(canonical_json(identity)).hexdigest()
    return HumanEvalCandidate(
        dataset_revision=dataset_revision,
        task_id=normalized["task_id"],
        source_family_id=normalized["task_id"],
        entry_point=normalized["entry_point"],
        prompt=normalized["prompt"],
        candidate_code=candidate_code,
        candidate_sha256=candidate_hash,
        candidate_origin=candidate_origin,
        candidate_slot=candidate_slot,
        split=split,
        record_id=record_id,
    )


def assert_family_split_isolation(records: Iterable[HumanEvalCandidate]) -> None:
    """Reject candidate variants of one source family assigned to multiple splits."""

    assignments: dict[str, Split] = {}
    for record in records:
        previous = assignments.setdefault(record.source_family_id, record.split)
        if previous is not record.split:
            raise ValueError(
                f"source family {record.source_family_id!r} crosses split boundaries"
            )


__all__ = [
    "HUMANEVAL_CANONICALIZATION_VERSION",
    "HUMANEVAL_DATASET_ID",
    "HUMANEVAL_VERIFIER_ID",
    "HumanEvalCandidate",
    "assert_family_split_isolation",
    "assign_humaneval_splits",
    "canonical_json",
    "canonicalize_humaneval_row",
    "fingerprint_humaneval_rows",
    "validate_humaneval_rows",
]
