import math

import pytest
from pydantic import ValidationError

from eval_lab.schema import (
    ExecutionStatus,
    GoldLabel,
    GoldProvenance,
    JudgePrediction,
    JudgeRecord,
    JudgmentMode,
    PairwiseLabel,
    RubricCriterion,
    SourceRecord,
    Split,
)


def _rubric() -> list[RubricCriterion]:
    return [RubricCriterion(criterion_id="correct", description="Matches the key.")]


def _gold(label: str = "pass") -> GoldLabel:
    return GoldLabel(
        label=label,
        provenance=GoldProvenance.DETERMINISTIC_VERIFIER,
        evidence={"source": "test"},
        verifier_id="test-v1",
    )


def test_schema_accepts_valid_single_record() -> None:
    record = JudgeRecord(
        record_id="single-1",
        source_problem_id="problem-1",
        mode=JudgmentMode.SINGLE,
        prompt="What is 2 + 2?",
        rubric=_rubric(),
        candidate_a="4",
        gold=_gold(),
        split=Split.TEST,
    )
    assert record.candidate_b is None
    assert record.stable_id == "single-1"


def test_schema_accepts_valid_pairwise_record() -> None:
    record = JudgeRecord(
        id="pair-1",
        source_problem_id="problem-1",
        mode="pairwise",
        prompt="Which answer is correct?",
        rubric=_rubric(),
        candidate_a="4",
        candidate_b="5",
        gold=_gold(PairwiseLabel.A.value),
        split="test",
    )
    assert record.record_id == "pair-1"
    assert record.gold.label == "A"


def test_pairwise_record_rejects_missing_candidate_b() -> None:
    with pytest.raises(ValidationError, match="candidate_b"):
        JudgeRecord(
            record_id="pair-invalid",
            source_problem_id="problem-1",
            mode=JudgmentMode.PAIRWISE,
            prompt="Compare.",
            rubric=_rubric(),
            candidate_a="A",
            gold=_gold(PairwiseLabel.A.value),
            split=Split.TEST,
        )


@pytest.mark.parametrize(
    "probabilities",
    [
        {"A": -0.1, "B": 1.1},
        {"A": 0.4, "B": 0.4},
        {"A": math.nan, "B": 0.0},
        {"A": 1.1, "B": -0.1},
    ],
)
def test_invalid_probability_vectors_are_rejected(probabilities: dict[str, float]) -> None:
    with pytest.raises(ValidationError, match="probabilities"):
        JudgePrediction(
            record_id="record-1",
            judge_id="judge-1",
            protocol_version="test-v1",
            label="A",
            probabilities=probabilities,
            execution_status=ExecutionStatus.OK,
        )


def test_gold_provenance_serialization_round_trip() -> None:
    source = SourceRecord(
        stable_id="source-1",
        domain="arithmetic",
        source_dataset="test",
        source_problem_id="problem-1",
        split=Split.CALIBRATION,
        prompt="What is 2 + 2?",
        reference_answer=4,
    )
    restored = SourceRecord.model_validate_json(source.model_dump_json())
    assert restored == source
    assert restored.split is Split.CALIBRATION

    gold = _gold(PairwiseLabel.TIE.value)
    assert GoldLabel.model_validate_json(gold.model_dump_json()) == gold
