"""Deterministic temperature and binary Platt calibration."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any, cast

from eval_lab.calibration.artifact import CalibrationArtifact
from eval_lab.schema import ExecutionStatus, JudgePrediction, JudgeRecord, Split

ProbabilityRow = Mapping[str, float]


def _as_probability_rows(
    inputs: Sequence[JudgeRecord] | Sequence[ProbabilityRow],
    second: Sequence[JudgePrediction] | Sequence[str] | None,
    *,
    fit_split: Split,
    class_order: Sequence[str] | None,
) -> tuple[list[str], list[dict[str, float]], list[str]]:
    if fit_split is not Split.CALIBRATION:
        raise ValueError("calibration must be fit with fit_split=calibration")
    if not inputs:
        raise ValueError("calibration inputs must not be empty")

    first = inputs[0]
    if isinstance(first, JudgeRecord):
        if second is None or not all(isinstance(item, JudgePrediction) for item in second):
            raise TypeError(
                "canonical calibration requires JudgeRecord and JudgePrediction sequences"
            )
        records = list(cast(Sequence[JudgeRecord], inputs))
        predictions = list(cast(Sequence[JudgePrediction], second))
        if len(records) != len(predictions):
            raise ValueError("records and predictions must have equal lengths")
        by_id = {record.record_id: record for record in records}
        if len(by_id) != len(records):
            raise ValueError("calibration records must have unique record IDs")
        labels: list[str] = []
        rows: list[dict[str, float]] = []
        for prediction in predictions:
            record = by_id.get(prediction.record_id)
            if record is None:
                raise ValueError("prediction record IDs must match calibration records")
            if record.split is Split.TEST:
                raise ValueError("calibration fitting rejects test split labels")
            if record.split is not Split.CALIBRATION:
                raise ValueError("calibration fitting requires split=calibration records")
            if prediction.execution_status is not ExecutionStatus.OK or prediction.label is None:
                raise ValueError("calibration fitting requires successful labeled predictions")
            if prediction.probabilities is None:
                raise ValueError("temperature calibration requires probabilities")
            labels.append(record.gold.label)
            rows.append(dict(prediction.probabilities))
        inferred = list(class_order or rows[0].keys())
        return _validate_rows(labels, rows, inferred)

    if second is None:
        raise TypeError("probability calibration requires labels")
    labels = [str(label) for label in second]
    rows = [dict(row) for row in inputs]
    inferred = list(class_order or rows[0].keys())
    return _validate_rows(labels, rows, inferred)


def _validate_rows(
    labels: Sequence[str], rows: Sequence[dict[str, float]], class_order: Sequence[str]
) -> tuple[list[str], list[dict[str, float]], list[str]]:
    classes = list(class_order)
    if not classes or len(classes) != len(set(classes)):
        raise ValueError("class_order must contain unique labels")
    if len(labels) != len(rows) or not rows:
        raise ValueError("calibration labels and probabilities must be non-empty and equally sized")
    for label in labels:
        if label not in classes:
            raise ValueError("calibration label is outside class_order")
    normalized: list[dict[str, float]] = []
    for row in rows:
        values = [float(row.get(label, 0.0)) for label in classes]
        if any(not math.isfinite(value) or value < 0 or value > 1 for value in values):
            raise ValueError("probabilities must be finite values in [0, 1]")
        if not math.isclose(sum(values), 1.0, rel_tol=0.0, abs_tol=1e-6):
            raise ValueError("probabilities must sum to one")
        normalized.append(dict(zip(classes, values, strict=True)))
    return list(labels), normalized, classes


def _temperature_nll(
    labels: Sequence[str],
    rows: Sequence[ProbabilityRow],
    classes: Sequence[str],
    temperature: float,
) -> float:
    total = 0.0
    for label, row in zip(labels, rows, strict=True):
        logits = [math.log(max(float(row[item]), 1e-15)) / temperature for item in classes]
        maximum = max(logits)
        log_normalizer = maximum + math.log(sum(math.exp(value - maximum) for value in logits))
        total += -(logits[classes.index(label)] - log_normalizer)
    return total / len(labels)


def _fit_positive_temperature(
    labels: Sequence[str], rows: Sequence[ProbabilityRow], classes: Sequence[str]
) -> float:
    """Minimize NLL in log-temperature space with a deterministic golden search."""

    lower, upper = -6.0, 6.0
    golden = (math.sqrt(5.0) - 1.0) / 2.0
    left = upper - golden * (upper - lower)
    right = lower + golden * (upper - lower)
    for _ in range(80):
        if _temperature_nll(labels, rows, classes, math.exp(left)) <= _temperature_nll(
            labels, rows, classes, math.exp(right)
        ):
            upper, right = right, left
            left = upper - golden * (upper - lower)
        else:
            lower, left = left, right
            right = lower + golden * (upper - lower)
    candidate = math.exp((lower + upper) / 2)
    baseline = _temperature_nll(labels, rows, classes, 1.0)
    return candidate if _temperature_nll(labels, rows, classes, candidate) <= baseline else 1.0


def fit_temperature_scaling(
    inputs: Sequence[JudgeRecord] | Sequence[ProbabilityRow],
    second: Sequence[JudgePrediction] | Sequence[str] | None = None,
    *,
    fit_split: Split = Split.CALIBRATION,
    class_order: Sequence[str] | None = None,
    code_version: str = "eval-lab-0.1.0",
) -> CalibrationArtifact:
    """Fit scalar multiclass temperature using calibration labels only."""

    labels, rows, classes = _as_probability_rows(
        inputs, second, fit_split=fit_split, class_order=class_order
    )
    temperature = _fit_positive_temperature(labels, rows, classes)
    return CalibrationArtifact(
        method="temperature",
        parameters={"temperature": temperature},
        fit_split=Split.CALIBRATION,
        class_order=classes,
        input_semantics="class probabilities; p_calibrated = softmax(log(p) / temperature)",
        code_version=code_version,
    )


def _apply_rows(
    probabilities: Sequence[ProbabilityRow], artifact: CalibrationArtifact
) -> list[dict[str, float]]:
    if artifact.method != "temperature":
        raise ValueError("artifact method is not temperature")
    temperature = float(artifact.parameters.get("temperature", 0.0))
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    output: list[dict[str, float]] = []
    for row in probabilities:
        artifact.validate_classes(row)
        logits = [
            math.log(max(float(row[label]), 1e-15)) / temperature for label in artifact.class_order
        ]
        maximum = max(logits)
        values = [math.exp(value - maximum) for value in logits]
        normalizer = sum(values)
        output.append(
            dict(zip(artifact.class_order, (value / normalizer for value in values), strict=True))
        )
    return output


def apply_temperature_scaling(
    probabilities: ProbabilityRow | Sequence[ProbabilityRow], artifact: CalibrationArtifact
) -> dict[str, float] | list[dict[str, float]]:
    """Apply a fitted temperature artifact without reading labels."""

    if isinstance(probabilities, Mapping):
        return _apply_rows([probabilities], artifact)[0]
    return _apply_rows(probabilities, artifact)


def _binary_rows(
    inputs: Sequence[JudgeRecord] | Sequence[float],
    second: Sequence[JudgePrediction] | Sequence[str] | None,
    *,
    fit_split: Split,
    class_order: Sequence[str] | None,
) -> tuple[list[float], list[int], list[str]]:
    if fit_split is not Split.CALIBRATION:
        raise ValueError("calibration must be fit with fit_split=calibration")
    classes = list(class_order or ("negative", "positive"))
    if len(classes) != 2 or len(set(classes)) != 2:
        raise ValueError("binary calibration requires exactly two class labels")
    if not inputs or second is None or len(inputs) != len(second):
        raise ValueError("binary calibration inputs must be non-empty and equally sized")
    scores: list[float] = []
    labels: list[int] = []
    if isinstance(inputs[0], JudgeRecord):
        records = list(cast(Sequence[JudgeRecord], inputs))
        predictions = list(cast(Sequence[JudgePrediction], second))
        by_id = {record.record_id: record for record in records}
        for prediction in predictions:
            if not isinstance(prediction, JudgePrediction):
                raise TypeError("canonical binary calibration requires JudgePrediction values")
            record = by_id.get(prediction.record_id)
            if record is None or record.split is Split.TEST:
                raise ValueError("calibration fitting rejects test split labels")
            if record.split is not Split.CALIBRATION:
                raise ValueError("calibration fitting requires split=calibration records")
            if (
                prediction.execution_status is not ExecutionStatus.OK
                or prediction.probabilities is None
            ):
                raise ValueError("binary calibration requires successful probabilities")
            probability = float(prediction.probabilities.get(classes[1], 0.0))
            scores.append(math.log(max(probability, 1e-15) / max(1.0 - probability, 1e-15)))
            labels.append(int(record.gold.label == classes[1]))
    else:
        scores_input = cast(Sequence[float], inputs)
        labels_input = cast(Sequence[str], second)
        for score, label in zip(scores_input, labels_input, strict=True):
            scores.append(float(score))
            labels.append(int(str(label) == classes[1]))
    if not all(math.isfinite(score) for score in scores):
        raise ValueError("binary scores must be finite")
    return scores, labels, classes


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def fit_platt_scaling(
    inputs: Sequence[JudgeRecord] | Sequence[float],
    second: Sequence[JudgePrediction] | Sequence[str] | None = None,
    *,
    fit_split: Split = Split.CALIBRATION,
    class_order: Sequence[str] | None = None,
    code_version: str = "eval-lab-0.1.0",
) -> CalibrationArtifact:
    """Fit binary logistic (Platt) scaling on calibration scores."""

    scores, labels, classes = _binary_rows(
        inputs, second, fit_split=fit_split, class_order=class_order
    )
    slope, intercept = 1.0, 0.0
    for _ in range(100):
        probabilities = [_sigmoid(slope * score + intercept) for score in scores]
        gradient_slope = sum(
            (probability - label) * score
            for probability, label, score in zip(probabilities, labels, scores, strict=True)
        )
        gradient_intercept = sum(
            probability - label for probability, label in zip(probabilities, labels, strict=True)
        )
        h11 = (
            sum(
                probability * (1.0 - probability) * score * score
                for probability, score in zip(probabilities, scores, strict=True)
            )
            + 1e-8
        )
        h12 = sum(
            probability * (1.0 - probability) * score
            for probability, score in zip(probabilities, scores, strict=True)
        )
        h22 = sum(probability * (1.0 - probability) for probability in probabilities) + 1e-8
        determinant = h11 * h22 - h12 * h12
        if determinant <= 0:
            break
        delta_slope = (h22 * gradient_slope - h12 * gradient_intercept) / determinant
        delta_intercept = (-h12 * gradient_slope + h11 * gradient_intercept) / determinant
        slope -= delta_slope
        intercept -= delta_intercept
        if max(abs(delta_slope), abs(delta_intercept)) < 1e-9:
            break
    return CalibrationArtifact(
        method="platt",
        parameters={"slope": slope, "intercept": intercept},
        fit_split=Split.CALIBRATION,
        class_order=classes,
        input_semantics="binary log-odds score; sigmoid(slope * score + intercept)",
        code_version=code_version,
    )


def apply_platt_scaling(
    scores: float | Sequence[float], artifact: CalibrationArtifact
) -> dict[str, float] | list[dict[str, float]]:
    """Apply binary Platt scaling and return bounded class probabilities."""

    if artifact.method != "platt" or len(artifact.class_order) != 2:
        raise ValueError("artifact is not a binary Platt calibrator")
    slope = float(artifact.parameters.get("slope", 0.0))
    intercept = float(artifact.parameters.get("intercept", 0.0))
    values = (
        [float(scores)] if isinstance(scores, (int, float)) else [float(score) for score in scores]
    )
    result = []
    for score in values:
        positive = _sigmoid(slope * score + intercept)
        result.append({artifact.class_order[0]: 1.0 - positive, artifact.class_order[1]: positive})
    return result[0] if isinstance(scores, (int, float)) else result


def apply_calibration(values: Any, artifact: CalibrationArtifact) -> Any:
    """Dispatch application by artifact method."""

    if artifact.method == "temperature":
        return apply_temperature_scaling(values, artifact)
    if artifact.method == "platt":
        return apply_platt_scaling(values, artifact)
    raise ValueError(f"unsupported calibration method: {artifact.method}")


__all__ = [
    "apply_calibration",
    "apply_platt_scaling",
    "apply_temperature_scaling",
    "fit_platt_scaling",
    "fit_temperature_scaling",
]
