"""Metrics and reliability utilities for frozen canonical predictions."""

from eval_lab.metrics.classification import (
    accuracy,
    balanced_accuracy,
    classification_metrics,
    expected_calibration_error,
    macro_f1,
    multiclass_brier,
    negative_log_likelihood,
)
from eval_lab.metrics.latency import latency_summary
from eval_lab.metrics.risk import (
    RiskCoveragePoint,
    confidence_from_probabilities,
    coverage_at_target_error,
    risk_coverage_curve,
    swap_consistency,
)
from eval_lab.metrics.summary import evaluate_prediction_set

__all__ = [
    "RiskCoveragePoint",
    "accuracy",
    "balanced_accuracy",
    "classification_metrics",
    "confidence_from_probabilities",
    "coverage_at_target_error",
    "evaluate_prediction_set",
    "expected_calibration_error",
    "latency_summary",
    "macro_f1",
    "multiclass_brier",
    "negative_log_likelihood",
    "risk_coverage_curve",
    "swap_consistency",
]
