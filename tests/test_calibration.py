import pytest

from eval_lab.calibration import (
    apply_platt_scaling,
    apply_temperature_scaling,
    fit_platt_scaling,
    fit_temperature_scaling,
)
from eval_lab.metrics import negative_log_likelihood
from eval_lab.schema import (
    GoldLabel,
    GoldProvenance,
    JudgePrediction,
    JudgeRecord,
    JudgmentMode,
    RubricCriterion,
    Split,
)


def test_temperature_is_positive_round_trips_and_improves_controlled_nll() -> None:
    labels = ["yes", "yes", "no", "no"]
    probabilities = [
        {"yes": 0.55, "no": 0.45},
        {"yes": 0.60, "no": 0.40},
        {"yes": 0.45, "no": 0.55},
        {"yes": 0.40, "no": 0.60},
    ]
    artifact = fit_temperature_scaling(probabilities, labels, class_order=["yes", "no"])
    restored = type(artifact).model_validate_json(artifact.model_dump_json())
    calibrated = apply_temperature_scaling(probabilities, restored)

    assert artifact.parameters["temperature"] > 0
    assert restored == artifact
    assert all(sum(row.values()) == pytest.approx(1.0) for row in calibrated)
    assert negative_log_likelihood(labels, calibrated, class_order=["yes", "no"]) <= negative_log_likelihood(
        labels, probabilities, class_order=["yes", "no"]
    ) + 1e-9


def test_temperature_fit_rejects_non_calibration_split() -> None:
    with pytest.raises(ValueError, match="fit_split=calibration"):
        fit_temperature_scaling(
            [{"yes": 0.8, "no": 0.2}],
            ["yes"],
            fit_split=Split.TEST,
            class_order=["yes", "no"],
        )


def test_temperature_fit_rejects_test_record_labels() -> None:
    record = JudgeRecord(
        record_id="test-record",
        source_problem_id="test-source",
        mode=JudgmentMode.SINGLE,
        prompt="Evaluate.",
        rubric=[RubricCriterion(criterion_id="c", description="Correct")],
        candidate_a="candidate",
        gold=GoldLabel(label="yes", provenance=GoldProvenance.ANSWER_KEY, evidence={}),
        split=Split.TEST,
    )
    prediction = JudgePrediction(
        record_id=record.record_id,
        judge_id="fixture",
        protocol_version="test-v1",
        label="yes",
        probabilities={"yes": 0.8, "no": 0.2},
    )

    with pytest.raises(ValueError, match="test split labels"):
        fit_temperature_scaling([record], [prediction], class_order=["yes", "no"])


def test_platt_scaling_is_bounded() -> None:
    artifact = fit_platt_scaling([-2.0, -1.0, 1.0, 2.0], ["no", "no", "yes", "yes"], class_order=["no", "yes"])
    probabilities = apply_platt_scaling([-100.0, 0.0, 100.0], artifact)

    assert all(0.0 <= row["yes"] <= 1.0 for row in probabilities)
    assert all(sum(row.values()) == pytest.approx(1.0) for row in probabilities)
