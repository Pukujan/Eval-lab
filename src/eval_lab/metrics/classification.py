"""Known-value classification and probability metrics."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any


def _require_equal_lengths(*values: Sequence[Any]) -> None:
    if not values:
        return
    length = len(values[0])
    if length == 0 or any(len(value) != length for value in values):
        raise ValueError("metric inputs must be non-empty and have equal lengths")


def _classes(
    y_true: Sequence[str], y_pred: Sequence[str], class_order: Sequence[str] | None
) -> list[str]:
    if class_order is not None:
        classes = list(class_order)
        if not classes or len(set(classes)) != len(classes):
            raise ValueError("class_order must contain unique labels")
        return classes
    return list(dict.fromkeys([*y_true, *y_pred]))


def _probability_rows(
    probabilities: Sequence[Mapping[str, float] | None],
    classes: Sequence[str],
) -> list[list[float]] | None:
    if any(row is None for row in probabilities):
        return None
    rows: list[list[float]] = []
    for row in probabilities:
        assert row is not None
        values = [float(row.get(label, 0.0)) for label in classes]
        if any(not math.isfinite(value) or value < 0 or value > 1 for value in values):
            raise ValueError("probabilities must be finite values in [0, 1]")
        if not math.isclose(sum(values), 1.0, abs_tol=1e-6):
            raise ValueError("probabilities must sum to one")
        rows.append(values)
    return rows


def _probability_classes(
    y_true: Sequence[str],
    probabilities: Sequence[Mapping[str, float] | None],
    class_order: Sequence[str] | None,
) -> list[str]:
    if class_order is not None:
        return _classes(y_true, [], class_order)
    for row in probabilities:
        if row is not None:
            return _classes(y_true, [], list(row))
    return _classes(y_true, [], [])


def accuracy(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    _require_equal_lengths(y_true, y_pred)
    return sum(actual == predicted for actual, predicted in zip(y_true, y_pred, strict=True)) / len(
        y_true
    )


def balanced_accuracy(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    *,
    class_order: Sequence[str] | None = None,
) -> float:
    _require_equal_lengths(y_true, y_pred)
    classes = _classes(y_true, y_pred, class_order)
    recalls = []
    for label in classes:
        actual = [index for index, value in enumerate(y_true) if value == label]
        if actual:
            recalls.append(sum(y_pred[index] == label for index in actual) / len(actual))
    return sum(recalls) / len(recalls) if recalls else 0.0


def macro_f1(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    *,
    class_order: Sequence[str] | None = None,
) -> float:
    _require_equal_lengths(y_true, y_pred)
    classes = _classes(y_true, y_pred, class_order)
    scores = []
    for label in classes:
        true_positive = sum(
            actual == label and predicted == label
            for actual, predicted in zip(y_true, y_pred, strict=True)
        )
        false_positive = sum(
            actual != label and predicted == label
            for actual, predicted in zip(y_true, y_pred, strict=True)
        )
        false_negative = sum(
            actual == label and predicted != label
            for actual, predicted in zip(y_true, y_pred, strict=True)
        )
        denominator = 2 * true_positive + false_positive + false_negative
        scores.append(2 * true_positive / denominator if denominator else 0.0)
    return sum(scores) / len(scores) if scores else 0.0


def multiclass_brier(
    y_true: Sequence[str],
    probabilities: Sequence[Mapping[str, float] | None],
    *,
    class_order: Sequence[str] | None = None,
) -> float | None:
    _require_equal_lengths(y_true, probabilities)
    classes = _probability_classes(y_true, probabilities, class_order)
    rows = _probability_rows(probabilities, classes)
    if rows is None:
        return None
    return sum(
        sum(
            (probability - float(label == actual)) ** 2
            for probability, label in zip(row, classes, strict=True)
        )
        for actual, row in zip(y_true, rows, strict=True)
    ) / len(rows)


def negative_log_likelihood(
    y_true: Sequence[str],
    probabilities: Sequence[Mapping[str, float] | None],
    *,
    class_order: Sequence[str] | None = None,
) -> float | None:
    _require_equal_lengths(y_true, probabilities)
    classes = _probability_classes(y_true, probabilities, class_order)
    rows = _probability_rows(probabilities, classes)
    if rows is None:
        return None
    index = {label: position for position, label in enumerate(classes)}
    if any(label not in index for label in y_true):
        raise ValueError("y_true contains a label outside class_order")
    epsilon = 1e-15
    return sum(
        -math.log(max(epsilon, row[index[actual]]))
        for actual, row in zip(y_true, rows, strict=True)
    ) / len(rows)


def expected_calibration_error(
    y_true: Sequence[str],
    probabilities: Sequence[Mapping[str, float] | None],
    *,
    class_order: Sequence[str] | None = None,
    n_bins: int = 10,
) -> float | None:
    _require_equal_lengths(y_true, probabilities)
    if n_bins <= 0:
        raise ValueError("n_bins must be positive")
    classes = _probability_classes(y_true, probabilities, class_order)
    rows = _probability_rows(probabilities, classes)
    if rows is None:
        return None
    errors = 0.0
    for bin_index in range(n_bins):
        lower = bin_index / n_bins
        upper = (bin_index + 1) / n_bins
        members = []
        for actual, row in zip(y_true, rows, strict=True):
            confidence = max(row)
            in_bin = lower <= confidence < upper or (
                bin_index == n_bins - 1 and confidence == upper
            )
            if in_bin:
                prediction = classes[row.index(confidence)]
                members.append((actual, prediction, confidence))
        if members:
            mean_confidence = sum(item[2] for item in members) / len(members)
            mean_accuracy = sum(item[0] == item[1] for item in members) / len(members)
            errors += len(members) / len(rows) * abs(mean_accuracy - mean_confidence)
    return errors


def classification_metrics(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    probabilities: Sequence[Mapping[str, float] | None] | None = None,
    *,
    class_order: Sequence[str] | None = None,
    n_bins: int = 10,
) -> dict[str, float | None]:
    _require_equal_lengths(y_true, y_pred)
    classes = _classes(y_true, y_pred, class_order)
    metrics: dict[str, float | None] = {
        "accuracy": accuracy(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy(y_true, y_pred, class_order=classes),
        "macro_f1": macro_f1(y_true, y_pred, class_order=classes),
        "brier": None,
        "nll": None,
        "ece": None,
    }
    if probabilities is not None:
        metrics["brier"] = multiclass_brier(y_true, probabilities, class_order=classes)
        metrics["nll"] = negative_log_likelihood(y_true, probabilities, class_order=classes)
        metrics["ece"] = expected_calibration_error(
            y_true,
            probabilities,
            class_order=classes,
            n_bins=n_bins,
        )
    return metrics
