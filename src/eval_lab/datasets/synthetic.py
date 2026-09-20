"""Deterministic, provider-free objective fixture generation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from eval_lab.schema import (
    GoldLabel,
    GoldProvenance,
    JudgeRecord,
    JudgmentMode,
    PairwiseLabel,
    RubricCriterion,
    SourceRecord,
    Split,
    swap_pairwise_record,
)
from eval_lab.verifiers.arithmetic import verify_arithmetic
from eval_lab.verifiers.code_output import verify_code_output
from eval_lab.verifiers.multiple_choice import verify_multiple_choice
from eval_lab.verifiers.structured import verify_structured_output

DEFAULT_SPLIT_SEED = 20260920
SPLIT_POLICY: tuple[tuple[Split, float], ...] = (
    (Split.TRAIN, 0.50),
    (Split.DEV, 0.20),
    (Split.CALIBRATION, 0.15),
    (Split.TEST, 0.15),
)


def assign_split(
    source_problem_id: str,
    *,
    seed: int = DEFAULT_SPLIT_SEED,
    policy: Sequence[tuple[Split, float]] = SPLIT_POLICY,
) -> Split:
    """Assign a source to one split using only its ID, seed, and declared policy."""

    if not source_problem_id:
        raise ValueError("source_problem_id must not be empty")
    if not policy:
        raise ValueError("split policy must not be empty")
    total = sum(weight for _, weight in policy)
    if abs(total - 1.0) > 1e-9 or any(weight <= 0 for _, weight in policy):
        raise ValueError("split policy weights must be positive and sum to 1")

    digest = hashlib.sha256(f"{seed}:{source_problem_id}".encode()).digest()
    sample = int.from_bytes(digest[:8], byteorder="big") / float(2**64)
    cumulative = 0.0
    for split, weight in policy:
        cumulative += weight
        if sample < cumulative:
            return Split(split)
    return Split(policy[-1][0])


split_for_source = assign_split
deterministic_split = assign_split


class SyntheticFixture(BaseModel):
    """Complete deterministic source and judge-record fixture bundle."""

    model_config = ConfigDict(extra="forbid")

    seed: int
    split_seed: int
    sources: list[SourceRecord] = Field(min_length=24)
    records: list[JudgeRecord] = Field(min_length=120)

    @model_validator(mode="after")
    def validate_fixture(self) -> SyntheticFixture:
        source_splits = {source.source_problem_id: source.split for source in self.sources}
        if len(source_splits) != len(self.sources):
            raise ValueError("source_problem_id values must be unique")
        record_ids = [record.record_id for record in self.records]
        if len(set(record_ids)) != len(record_ids):
            raise ValueError("record IDs must be unique")
        for record in self.records:
            if record.source_problem_id not in source_splits:
                raise ValueError("every record must reference a known source")
            if record.split is not source_splits[record.source_problem_id]:
                raise ValueError("all source variants must inherit the source split")
        return self

    @property
    def single_records(self) -> list[JudgeRecord]:
        return [record for record in self.records if record.mode is JudgmentMode.SINGLE]

    @property
    def pairwise_records(self) -> list[JudgeRecord]:
        return [record for record in self.records if record.mode is JudgmentMode.PAIRWISE]

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def _rubric() -> list[RubricCriterion]:
    return [
        RubricCriterion(
            criterion_id="objective-correctness",
            description="The candidate matches the deterministic answer key.",
            weight=1.0,
            aggregation_rule="all",
        )
    ]


def _source_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []

    arithmetic = [
        ("addition", "What is 7 + 5?", 12, "12", "13", "0"),
        ("subtraction", "What is 19 - 7?", 12, "12", "11", "0"),
        ("multiplication", "What is 6 * 8?", 48, "48", "42", "0"),
        ("division", "What is 81 / 9?", 9, "9", "8", "0"),
        ("mixed", "What is 4 * 5 + 3?", 23, "23", "24", "0"),
        ("decimal", "What is 2.5 + 1.25?", 3.75, "3.75", "3.65", "0"),
    ]
    for index, (name, prompt, expected, correct, subtle, obvious) in enumerate(arithmetic, 1):
        specs.append(
            {
                "domain": "arithmetic",
                "source_problem_id": f"synthetic-arithmetic-{index:02d}",
                "prompt": prompt,
                "reference_answer": expected,
                "source_metadata": {"operation": name, "verifier": "arithmetic-v1"},
                "correct": correct,
                "subtle": subtle,
                "obvious": obvious,
                "verify": verify_arithmetic,
            }
        )

    multiple_choice = [
        ("capital", "Which city is the capital of France?", "B", ["A) Rome", "B) Paris", "C) Madrid", "D) Berlin"]),
        ("planet", "Which planet is known for its rings?", "C", ["A) Mars", "B) Venus", "C) Saturn", "D) Mercury"]),
        ("square", "Which number is a perfect square?", "A", ["A) 49", "B) 50", "C) 51", "D) 52"]),
        ("unit", "How many bits are in one byte?", "D", ["A) 2", "B) 4", "C) 6", "D) 8"]),
        ("water", "At standard pressure, water freezes at what temperature in Celsius?", "A", ["A) 0", "B) 10", "C) 32", "D) 100"]),
        ("logic", "Which value is greater than 0.5?", "B", ["A) 0.05", "B) 0.75", "C) 0.5", "D) 0.25"]),
    ]
    for index, (name, prompt, answer, options) in enumerate(multiple_choice, 1):
        wrong = next(letter for letter in "ABCD" if letter != answer)
        far_wrong = "Z"
        specs.append(
            {
                "domain": "multiple_choice",
                "source_problem_id": f"synthetic-multiple-choice-{index:02d}",
                "prompt": prompt,
                "reference_answer": {"answer": answer, "options": options},
                "source_metadata": {"topic": name, "verifier": "multiple-choice-v1"},
                "correct": answer,
                "subtle": wrong,
                "obvious": far_wrong,
                "verify": verify_multiple_choice,
            }
        )

    structured = [
        ("status", {"status": "ready", "count": 3}, '{"status":"ready","count":3}', '{"status":"ready","count":4}'),
        ("priority", {"priority": "high", "owner": "lab"}, '{"priority":"high","owner":"lab"}', '{"priority":"medium","owner":"lab"}'),
        ("coordinates", {"x": 2, "y": 5}, '{"x":2,"y":5}', '{"x":2,"y":6}'),
        ("flags", {"enabled": True, "mode": "safe"}, '{"enabled":true,"mode":"safe"}', '{"enabled":false,"mode":"safe"}'),
        ("items", {"items": ["a", "b"], "total": 2}, '{"items":["a","b"],"total":2}', '{"items":["a","b"],"total":3}'),
        ("version", {"version": 2, "stable": True}, '{"version":2,"stable":true}', '{"version":3,"stable":true}'),
    ]
    for index, (name, expected, correct, subtle) in enumerate(structured, 1):
        specs.append(
            {
                "domain": "structured",
                "source_problem_id": f"synthetic-structured-{index:02d}",
                "prompt": f"Return the requested {name} object as JSON.",
                "reference_answer": expected,
                "source_metadata": {"shape": name, "verifier": "structured-output-v1"},
                "correct": correct,
                "subtle": subtle,
                "obvious": "not json",
                "verify": verify_structured_output,
            }
        )

    code_output = [
        ("sum", "print the sum of 2 and 3", "5", "6"),
        ("length", "print the length of the string 'abc'", "3", "2"),
        ("uppercase", "print 'lab' in uppercase", "LAB", "Lab"),
        ("join", "print the words alpha and beta joined by a hyphen", "alpha-beta", "alpha beta"),
        ("sort", "print the sorted values from 3, 1, 2", "1\n2\n3", "1\n3\n2"),
        ("boolean", "print the result of 4 > 1", "True", "False"),
    ]
    for index, (name, prompt, correct, subtle) in enumerate(code_output, 1):
        specs.append(
            {
                "domain": "code_output",
                "source_problem_id": f"synthetic-code-output-{index:02d}",
                "prompt": prompt,
                "reference_answer": correct,
                "source_metadata": {"task": name, "verifier": "code-output-v1"},
                "correct": correct,
                "subtle": subtle,
                "obvious": "runtime error",
                "verify": verify_code_output,
            }
        )
    return specs


def _gold_for_single(spec: Mapping[str, Any], candidate: str) -> GoldLabel:
    verifier = spec["verify"]
    result = verifier(candidate, spec["reference_answer"])
    return result.to_gold_label()


def _pairwise_gold(spec: Mapping[str, Any], preferred: str, rejected: str) -> GoldLabel:
    preferred_result = spec["verify"](preferred, spec["reference_answer"])
    rejected_result = spec["verify"](rejected, spec["reference_answer"])
    return GoldLabel(
        label=PairwiseLabel.A.value if preferred == "A" else PairwiseLabel.B.value,
        provenance=GoldProvenance.DETERMINISTIC_VERIFIER,
        evidence={
            "preferred_is_correct": preferred_result.is_correct,
            "rejected_is_correct": rejected_result.is_correct,
            "preferred_evidence": preferred_result.evidence,
            "rejected_evidence": rejected_result.evidence,
        },
        verifier_id=preferred_result.verifier_id,
    )


def generate_synthetic_fixtures(
    *,
    seed: int = DEFAULT_SPLIT_SEED,
    split_seed: int = DEFAULT_SPLIT_SEED,
) -> SyntheticFixture:
    """Generate the complete deterministic four-domain fixture suite."""

    sources: list[SourceRecord] = []
    records: list[JudgeRecord] = []
    for spec in _source_specs():
        source = SourceRecord(
            source_id=spec["source_problem_id"],
            domain=spec["domain"],
            source_dataset="synthetic-objective-v1",
            source_problem_id=spec["source_problem_id"],
            split=assign_split(spec["source_problem_id"], seed=split_seed),
            prompt=spec["prompt"],
            reference_answer=spec["reference_answer"],
            source_metadata=spec["source_metadata"],
        )
        sources.append(source)
        shared = {
            "source_problem_id": source.source_problem_id,
            "prompt": source.prompt,
            "rubric": _rubric(),
            "split": source.split,
        }
        candidates = (spec["correct"], spec["subtle"], spec["obvious"])
        for suffix, candidate in zip(("correct", "subtle", "obvious"), candidates, strict=True):
            records.append(
                JudgeRecord(
                    record_id=f"single-{source.source_problem_id}-{suffix}",
                    mode=JudgmentMode.SINGLE,
                    candidate_a=candidate,
                    gold=_gold_for_single(spec, candidate),
                    **shared,
                )
            )

        for suffix, candidate_a, candidate_b, label in (
            ("correct-first", spec["correct"], spec["subtle"], PairwiseLabel.A),
            ("incorrect-first", spec["subtle"], spec["correct"], PairwiseLabel.B),
        ):
            verifier = spec["verify"]
            result_a = verifier(candidate_a, spec["reference_answer"])
            result_b = verifier(candidate_b, spec["reference_answer"])
            records.append(
                JudgeRecord(
                    record_id=f"pair-{source.source_problem_id}-{suffix}",
                    mode=JudgmentMode.PAIRWISE,
                    candidate_a=candidate_a,
                    candidate_b=candidate_b,
                    gold=GoldLabel(
                        label=label.value,
                        provenance=GoldProvenance.DETERMINISTIC_VERIFIER,
                        evidence={
                            "candidate_a": result_a.evidence,
                            "candidate_b": result_b.evidence,
                        },
                        verifier_id=result_a.verifier_id,
                    ),
                    perturbation={"kind": "candidate_order", "correct_position": label.value},
                    **shared,
                )
            )
    return SyntheticFixture(seed=seed, split_seed=split_seed, sources=sources, records=records)


build_synthetic_fixture = generate_synthetic_fixtures
generate_synthetic_fixture = generate_synthetic_fixtures


def serialize_fixture(fixture: SyntheticFixture) -> str:
    """Serialize a fixture with stable key ordering for reproducibility checks."""

    return json.dumps(fixture.model_dump(mode="json"), sort_keys=True, indent=2) + "\n"


__all__ = [
    "DEFAULT_SPLIT_SEED",
    "SPLIT_POLICY",
    "SyntheticFixture",
    "assign_split",
    "build_synthetic_fixture",
    "deterministic_split",
    "generate_synthetic_fixture",
    "generate_synthetic_fixtures",
    "serialize_fixture",
    "split_for_source",
    "swap_pairwise_record",
]
