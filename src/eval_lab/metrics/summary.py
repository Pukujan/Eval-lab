"""Aggregate metrics over canonical records and predictions."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from eval_lab.metrics.classification import classification_metrics
from eval_lab.metrics.latency import latency_summary
from eval_lab.metrics.risk import confidence_from_probabilities, risk_coverage_curve
from eval_lab.schema import ExecutionStatus, JudgePrediction, JudgeRecord


def _metric_rows(
    records: Sequence[JudgeRecord], predictions: Sequence[JudgePrediction]
) -> tuple[list[JudgeRecord], list[JudgePrediction]]:
    if len(records) != len(predictions):
        raise ValueError("records and predictions must have equal lengths")
    by_id = {record.record_id: record for record in records}
    if len(by_id) != len(records) or any(
        prediction.record_id not in by_id for prediction in predictions
    ):
        raise ValueError("prediction record IDs must match unique record IDs")
    successful = [
        (by_id[prediction.record_id], prediction)
        for prediction in predictions
        if prediction.execution_status is ExecutionStatus.OK and prediction.label is not None
    ]
    return [record for record, _ in successful], [prediction for _, prediction in successful]


def _one_domain(
    records: Sequence[JudgeRecord], predictions: Sequence[JudgePrediction]
) -> dict[str, object]:
    if not records:
        return {"count": 0, "metrics": None, "probability_metrics_available": False}
    labels = [record.gold.label for record in records]
    guesses: list[str] = []
    for prediction in predictions:
        if prediction.label is None:
            raise ValueError("resolved predictions must have labels")
        guesses.append(prediction.label)
    probabilities = [prediction.probabilities for prediction in predictions]
    classes = list(dict.fromkeys(labels + guesses))
    for row in probabilities:
        if row is not None:
            classes.extend(label for label in row if label not in classes)
    metrics = classification_metrics(labels, guesses, probabilities, class_order=classes)
    return {
        "count": len(records),
        "metrics": metrics,
        "probability_metrics_available": all(row is not None for row in probabilities),
    }


def evaluate_prediction_set(
    records: Sequence[JudgeRecord],
    predictions: Sequence[JudgePrediction],
    *,
    target_errors: Sequence[float] = (0.01, 0.02, 0.05),
    domain_by_record_id: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Evaluate successful predictions while retaining all execution statuses."""

    successful_records, successful_predictions = _metric_rows(records, predictions)
    status_counts = Counter(prediction.execution_status.value for prediction in predictions)
    aggregate = _one_domain(successful_records, successful_predictions)
    by_domain: dict[str, dict[str, object]] = {}
    domains = {
        domain_by_record_id.get(record.record_id, "unknown") if domain_by_record_id else "unknown"
        for record in successful_records
    }
    for domain in sorted(domains):
        pairs = [
            (record, prediction)
            for record, prediction in zip(successful_records, successful_predictions, strict=True)
            if (
                domain_by_record_id.get(record.record_id, "unknown")
                if domain_by_record_id
                else "unknown"
            )
            == domain
        ]
        by_domain[domain] = _one_domain([item[0] for item in pairs], [item[1] for item in pairs])

    risk: dict[str, object] = {"curve": [], "coverage_at_target_error": {}}
    confidence: list[float] = []
    correct: list[bool] = []
    for record, prediction in zip(successful_records, successful_predictions, strict=True):
        if prediction.probabilities is not None:
            confidence.append(confidence_from_probabilities(prediction.probabilities))
            correct.append(prediction.label == record.gold.label)
    if confidence:
        curve = risk_coverage_curve(correct, confidence)
        risk["curve"] = [point.as_dict() for point in curve]
        risk["coverage_at_target_error"] = {
            str(target): max(point.coverage for point in curve if point.risk <= target)
            for target in target_errors
        }

    latencies = [
        prediction.latency_ms for prediction in predictions if prediction.latency_ms is not None
    ]
    return {
        "total_count": len(predictions),
        "successful_count": len(successful_predictions),
        "status_counts": dict(sorted(status_counts.items())),
        "failure_count": len(predictions) - len(successful_predictions),
        "aggregate": aggregate,
        "by_domain": by_domain,
        "risk_coverage": risk,
        "latency": latency_summary(latencies),
    }
