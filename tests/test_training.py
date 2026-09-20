from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_lab.datasets.synthetic import generate_synthetic_fixtures
from eval_lab.schema import Split
from eval_lab.training import TextLogisticStudent, build_training_rows

ROOT = Path(__file__).resolve().parents[1]
HARD_NEGATIVE_PATH = ROOT / "experiments/EXP-20260920-007-teacher-hard-negatives/verified_hard_negatives.jsonl"
PARAPHRASE_PATH = ROOT / "experiments/EXP-20260920-007-teacher-hard-negatives/rubric_paraphrases.jsonl"


def _fixture_inputs() -> tuple[object, list[dict[str, object]], dict[str, str]]:
    fixture = generate_synthetic_fixtures()
    hard_negatives = [
        json.loads(line)
        for line in HARD_NEGATIVE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    paraphrases = {
        str(row["domain"]): str(row["paraphrase"])
        for row in (
            json.loads(line)
            for line in PARAPHRASE_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    return fixture, hard_negatives, paraphrases


def test_training_arms_preserve_source_splits_and_expected_augmentation() -> None:
    fixture, hard_negatives, paraphrases = _fixture_inputs()
    rows = {
        arm: build_training_rows(
            fixture.records,
            arm=arm,
            hard_negatives=hard_negatives,
            rubric_paraphrases=paraphrases,
        )
        for arm in "ABCD"
    }

    assert len(rows["A"]) == 33
    assert len(rows["B"]) == 66
    assert len(rows["C"]) == 36
    assert len(rows["D"]) == 72
    for arm_rows in rows.values():
        assert all(row.source_split == Split.TRAIN.value for row in arm_rows)
        assert all(row.provenance == "deterministic_verifier" for row in arm_rows)
        assert not any(row.source_split == Split.TEST.value for row in arm_rows)
    assert all(row.source_kind == "objective" for row in rows["A"])
    assert any(row.source_kind == "verified_hard_negative" for row in rows["C"])
    assert any("criterion-paraphrase" in row.augmentation for row in rows["B"])


def test_student_is_deterministic_and_emits_normalized_probabilities() -> None:
    fixture, hard_negatives, paraphrases = _fixture_inputs()
    rows = build_training_rows(
        fixture.records,
        arm="D",
        hard_negatives=hard_negatives,
        rubric_paraphrases=paraphrases,
    )
    records = [
        record
        for record in fixture.records
        if record.mode.value == "single" and record.split is Split.DEV
    ][:5]
    first = TextLogisticStudent().fit(rows)
    second = TextLogisticStudent().fit(rows)
    first_predictions = first.predict(records)
    second_predictions = second.predict(records)

    assert first.artifact() == second.artifact()
    assert [item.label for item in first_predictions] == [item.label for item in second_predictions]
    for prediction in first_predictions:
        assert prediction.probabilities is not None
        assert sum(prediction.probabilities.values()) == pytest.approx(1.0)
        assert prediction.execution_status.value == "ok"


def test_student_rejects_pairwise_records() -> None:
    fixture, hard_negatives, paraphrases = _fixture_inputs()
    rows = build_training_rows(
        fixture.records,
        arm="A",
        hard_negatives=hard_negatives,
        rubric_paraphrases=paraphrases,
    )
    student = TextLogisticStudent().fit(rows)
    pairwise = next(record for record in fixture.records if record.mode.value == "pairwise")
    with pytest.raises(ValueError, match="single-answer"):
        student.predict([pairwise])


def test_test_hard_negative_is_excluded_from_training() -> None:
    fixture, hard_negatives, paraphrases = _fixture_inputs()
    test_item = dict(hard_negatives[0])
    test_item["split"] = "test"
    rows = build_training_rows(
        fixture.records,
        arm="C",
        hard_negatives=[test_item],
        rubric_paraphrases=paraphrases,
    )
    assert not any(row.record_id == test_item["record_id"] for row in rows)
