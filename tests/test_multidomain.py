"""Offline tests for TASK-0011 source canonicalization and split discipline."""

from __future__ import annotations

from eval_lab.datasets.multidomain import (
    canonicalize_choice_row,
    canonicalize_gsm8k_row,
    gsm8k_final_answer,
    select_source_ids,
)
from eval_lab.schema import Split


def test_source_selection_is_deterministic_and_unique() -> None:
    values = ["a", "b", "c", "a"]
    assert select_source_ids(values, seed=7, family="test", limit=3) == select_source_ids(
        values, seed=7, family="test", limit=3
    )
    assert len(select_source_ids(values, seed=7, family="test", limit=10)) == 3


def test_choice_canonicalization_creates_objective_correct_and_wrong_variants() -> None:
    records = canonicalize_choice_row(
        dataset="mmlu",
        source_problem_id="subject:test:0001",
        question="Which letter comes first?",
        choices=["alpha", "beta", "gamma"],
        answer_index=1,
        split=Split.TEST,
        evidence={"subject": "test"},
    )
    assert [record.gold.label for record in records] == ["pass", "fail"]
    assert {record.source_problem_id for record in records} == {"subject:test:0001"}
    assert all(record.split is Split.TEST for record in records)
    assert records[0].candidate_a != records[1].candidate_a


def test_gsm8k_answer_normalization_and_wrong_answer_are_deterministic() -> None:
    records = canonicalize_gsm8k_row(
        source_problem_id="gsm8k-main:test-00001",
        question="What is 2 + 2?",
        answer="2 + 2 = 4\n#### 4",
        split=Split.CALIBRATION,
    )
    assert gsm8k_final_answer("work\n#### 1,200") == "1200"
    assert records[0].candidate_a == "Final answer: 4"
    assert records[1].candidate_a == "Final answer: 5"
    assert records[0].gold.label == "pass"
    assert records[1].gold.label == "fail"
