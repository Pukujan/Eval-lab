"""Canonical objective records for the TASK-0011 multidomain study."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from eval_lab.schema import (
    GoldLabel,
    GoldProvenance,
    JudgeRecord,
    JudgmentMode,
    RubricCriterion,
    Split,
)

_ANSWER_RE = re.compile(r"####\s*([^\s]+)")


def stable_rank(seed: int, family: str, source_problem_id: str) -> str:
    """Return a deterministic sort key for source-level sampling."""

    return hashlib.sha256(f"{seed}:{family}:{source_problem_id}".encode()).hexdigest()


def select_source_ids(
    source_problem_ids: Sequence[str], *, seed: int, family: str, limit: int
) -> list[str]:
    """Select unique source IDs without resampling or using labels."""

    if limit < 0:
        raise ValueError("limit must be non-negative")
    unique = sorted(set(source_problem_ids), key=lambda item: stable_rank(seed, family, item))
    return unique[:limit]


def _rubric() -> list[RubricCriterion]:
    return [
        RubricCriterion(
            criterion_id="objective-correctness",
            description="The candidate answer matches the trusted answer key or deterministic verifier.",
            weight=1.0,
            aggregation_rule="all",
        )
    ]


def _single_variant(
    *,
    dataset: str,
    source_problem_id: str,
    prompt: str,
    candidate: str,
    correct: bool,
    split: Split,
    evidence: Mapping[str, Any],
    variant: str,
) -> JudgeRecord:
    return JudgeRecord(
        record_id=f"{dataset}:{source_problem_id}:{variant}",
        source_problem_id=source_problem_id,
        mode=JudgmentMode.SINGLE,
        prompt=prompt,
        rubric=_rubric(),
        candidate_a=candidate,
        gold=GoldLabel(
            label="pass" if correct else "fail",
            provenance=GoldProvenance.ANSWER_KEY,
            evidence=dict(evidence),
            verifier_id=f"{dataset}-answer-key-v1",
        ),
        split=split,
        perturbation={"kind": "correct_or_deterministic_wrong_answer", "variant": variant},
    )


def canonicalize_answer_pair(
    *,
    dataset: str,
    source_problem_id: str,
    prompt: str,
    correct_candidate: str,
    wrong_candidate: str,
    split: Split,
    evidence: Mapping[str, Any],
) -> list[JudgeRecord]:
    """Create one correct and one deterministic incorrect single-answer record."""

    return [
        _single_variant(
            dataset=dataset,
            source_problem_id=source_problem_id,
            prompt=prompt,
            candidate=correct_candidate,
            correct=True,
            split=split,
            evidence=evidence,
            variant="correct",
        ),
        _single_variant(
            dataset=dataset,
            source_problem_id=source_problem_id,
            prompt=prompt,
            candidate=wrong_candidate,
            correct=False,
            split=split,
            evidence=evidence,
            variant="wrong",
        ),
    ]


def _choice_prompt(question: str, choices: Sequence[str]) -> str:
    labels = "\n".join(f"{chr(ord('A') + index)}) {choice}" for index, choice in enumerate(choices))
    return f"Question: {question}\nChoices:\n{labels}"


def canonicalize_choice_row(
    *,
    dataset: str,
    source_problem_id: str,
    question: str,
    choices: Sequence[str],
    answer_index: int,
    split: Split,
    evidence: Mapping[str, Any],
) -> list[JudgeRecord]:
    """Canonicalize an answer-key multiple-choice row as pass/fail variants."""

    if not question.strip() or len(choices) < 2:
        raise ValueError("choice rows require a question and at least two choices")
    if not 0 <= answer_index < len(choices):
        raise ValueError("answer_index is outside the choice list")
    wrong_index = (answer_index + 1) % len(choices)
    prompt = _choice_prompt(question.strip(), choices)
    return canonicalize_answer_pair(
        dataset=dataset,
        source_problem_id=source_problem_id,
        prompt=prompt,
        correct_candidate=f"Answer: {chr(ord('A') + answer_index)}) {choices[answer_index]}",
        wrong_candidate=f"Answer: {chr(ord('A') + wrong_index)}) {choices[wrong_index]}",
        split=split,
        evidence={**evidence, "answer_index": answer_index, "wrong_index": wrong_index},
    )


def gsm8k_final_answer(answer: str) -> str:
    """Extract and normalize the answer-key final number from GSM8K."""

    match = _ANSWER_RE.search(answer)
    if match is None:
        raise ValueError("GSM8K answer has no #### final answer")
    value = match.group(1).replace(",", "").replace("$", "")
    try:
        text = format(Decimal(value), "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    except InvalidOperation as exc:
        raise ValueError("GSM8K final answer is not numeric") from exc


def gsm8k_wrong_answer(correct_answer: str) -> str:
    """Create a deterministic numeric distractor without consulting labels beyond the answer key."""

    value = Decimal(correct_answer)
    text = format(value + Decimal(1), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def canonicalize_gsm8k_row(
    *,
    source_problem_id: str,
    question: str,
    answer: str,
    split: Split,
) -> list[JudgeRecord]:
    correct = gsm8k_final_answer(answer)
    return canonicalize_answer_pair(
        dataset="gsm8k",
        source_problem_id=source_problem_id,
        prompt=f"Solve the math word problem.\nQuestion: {question.strip()}",
        correct_candidate=f"Final answer: {correct}",
        wrong_candidate=f"Final answer: {gsm8k_wrong_answer(correct)}",
        split=split,
        evidence={"answer_key": correct, "source_dataset": "openai/gsm8k"},
    )


__all__ = [
    "canonicalize_answer_pair",
    "canonicalize_choice_row",
    "canonicalize_gsm8k_row",
    "gsm8k_final_answer",
    "gsm8k_wrong_answer",
    "select_source_ids",
    "stable_rank",
]
