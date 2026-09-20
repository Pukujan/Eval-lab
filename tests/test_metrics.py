import math

import pytest

from eval_lab.metrics import (
    accuracy,
    balanced_accuracy,
    expected_calibration_error,
    latency_summary,
    macro_f1,
    multiclass_brier,
    negative_log_likelihood,
    risk_coverage_curve,
    swap_consistency,
)


def test_known_classification_metrics() -> None:
    actual = ["A", "A", "B", "B", "C"]
    predicted = ["A", "B", "B", "C", "C"]

    assert accuracy(actual, predicted) == 0.6
    assert balanced_accuracy(actual, predicted, class_order=["A", "B", "C"]) == 2 / 3
    assert macro_f1(actual, predicted, class_order=["A", "B", "C"]) == pytest.approx(11 / 18)


def test_known_probability_metrics_and_unavailable_rows() -> None:
    actual = ["A", "B"]
    probabilities = [{"A": 0.8, "B": 0.2}, {"A": 0.3, "B": 0.7}]

    assert multiclass_brier(actual, probabilities, class_order=["A", "B"]) == 0.13
    assert negative_log_likelihood(actual, probabilities, class_order=["A", "B"]) == pytest.approx(
        -0.5 * (math.log(0.8) + math.log(0.7))
    )
    assert expected_calibration_error(actual, probabilities, class_order=["A", "B"], n_bins=10) == 0.25
    assert multiclass_brier(actual, [None, None], class_order=["A", "B"]) is None


def test_risk_coverage_and_swap_consistency_are_deterministic() -> None:
    curve = risk_coverage_curve([True, False, True], [0.9, 0.8, 0.7])

    assert [point.coverage for point in curve] == [0.0, 1 / 3, 2 / 3, 1.0]
    assert [point.risk for point in curve] == pytest.approx([0.0, 0.0, 0.5, 1 / 3])
    assert swap_consistency(["A", "B", "TIE"], ["B", "A", "TIE"]) == 1.0


def test_latency_summary_uses_stable_percentiles() -> None:
    summary = latency_summary([10, 20, 30, 40, 50])

    assert summary["mean_ms"] == 30.0
    assert summary["median_ms"] == 30.0
    assert summary["p95_ms"] == 48.0
