"""Report per-family accuracy, calibration, and selective-prediction metrics.

Joins the blind predictions produced by ``scripts/run_gleif_classifier_jev.py``
to the frozen GLEIF gold labels and writes ``results.json`` and ``report.md`` for
EXP-032. Every family is reported beside a majority-class baseline, because the
entity-category family is heavily imbalanced and raw accuracy alone is
misleading. Nothing here calls a model.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from eval_lab.metrics.classification import (
    balanced_accuracy,
    classification_metrics,
    macro_f1,
)
from eval_lab.metrics.latency import latency_summary
from eval_lab.metrics.risk import confidence_from_probabilities, risk_coverage_curve
from eval_lab.schema import ExecutionStatus, JudgePrediction

try:
    from scripts.analyze_judge_comparison import wilson
except ImportError:  # executed as a file from the repository root
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.analyze_judge_comparison import wilson

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ID = "EXP-20261005-032-gleif-classifier"
EXPERIMENT_DIR = ROOT / "experiments" / EXPERIMENT_ID
PARTITION = "blind_holdout"
TARGET_ERRORS = (0.01, 0.02, 0.05)


def _load_rows(family: str) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in (EXPERIMENT_DIR / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [row for row in rows if row["family"] == family and row["partition"] == PARTITION]


def _load_predictions(path: Path) -> dict[str, JudgePrediction]:
    predictions: dict[str, JudgePrediction] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            prediction = JudgePrediction.model_validate_json(line)
            if prediction.record_id in predictions:
                raise ValueError(f"duplicate prediction record ID: {prediction.record_id}")
            predictions[prediction.record_id] = prediction
    return predictions


def _reliability_bins(
    correct: list[bool], confidence: list[float], *, n_bins: int = 10
) -> list[dict[str, Any]]:
    """Equal-width confidence bins with empirical accuracy, for a reliability chart."""

    bins: list[dict[str, Any]] = []
    for index in range(n_bins):
        lower = index / n_bins
        upper = (index + 1) / n_bins
        members = [
            (is_correct, score)
            for is_correct, score in zip(correct, confidence, strict=True)
            if lower <= score < upper or (index == n_bins - 1 and score == upper)
        ]
        bins.append(
            {
                "binLower": lower,
                "binUpper": upper,
                "count": len(members),
                "meanConfidence": (
                    sum(score for _, score in members) / len(members) if members else None
                ),
                "accuracy": (
                    sum(int(is_correct) for is_correct, _ in members) / len(members)
                    if members
                    else None
                ),
            }
        )
    return bins


def _histogram(values: list[float], *, n_bins: int = 10) -> list[dict[str, Any]]:
    counts = [0] * n_bins
    for value in values:
        index = min(int(value * n_bins), n_bins - 1)
        counts[index] += 1
    return [
        {
            "binLower": index / n_bins,
            "binUpper": (index + 1) / n_bins,
            "count": counts[index],
        }
        for index in range(n_bins)
    ]


def _per_class(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for label in labels:
        support = sum(actual == label for actual in y_true)
        predicted = sum(guess == label for guess in y_pred)
        true_positive = sum(
            actual == label and guess == label for actual, guess in zip(y_true, y_pred, strict=True)
        )
        precision = true_positive / predicted if predicted else None
        recall = true_positive / support if support else None
        report[label] = {
            "support": support,
            "predicted": predicted,
            "truePositive": true_positive,
            "precision": precision,
            "recall": recall,
            "f1": (
                2 * precision * recall / (precision + recall)
                if precision and recall
                else (0.0 if precision is not None or recall is not None else None)
            ),
        }
    return report


def _family_report(
    family: str,
    labels: list[str],
    rows: list[dict[str, Any]],
    predictions: dict[str, JudgePrediction],
) -> dict[str, Any]:
    total = len(rows)
    statuses: Counter[str] = Counter()
    y_true: list[str] = []
    y_pred: list[str] = []
    probabilities: list[dict[str, float] | None] = []
    confidence: list[float] = []
    correct: list[bool] = []
    latencies: list[float] = []
    costs: list[float] = []
    resolved = 0
    for row in rows:
        record_id = row["record"]["record_id"]
        prediction = predictions.get(record_id)
        if prediction is None:
            raise ValueError(f"{family}: no prediction for {record_id}")
        statuses[prediction.execution_status.value] += 1
        if prediction.latency_ms is not None:
            latencies.append(prediction.latency_ms)
        usage = prediction.provider_metadata.get("usage")
        if isinstance(usage, dict) and isinstance(usage.get("cost"), (int, float)):
            costs.append(float(usage["cost"]))
        if prediction.execution_status is not ExecutionStatus.OK or prediction.label is None:
            continue
        resolved += 1
        gold = row["record"]["gold"]["label"]
        y_true.append(gold)
        y_pred.append(prediction.label)
        probabilities.append(prediction.probabilities)
        correct.append(prediction.label == gold)
        if prediction.probabilities is not None:
            confidence.append(confidence_from_probabilities(prediction.probabilities))

    metrics = (
        classification_metrics(y_true, y_pred, probabilities, class_order=labels)
        if y_true
        else {
            "accuracy": None,
            "balanced_accuracy": None,
            "macro_f1": None,
            "brier": None,
            "nll": None,
            "ece": None,
        }
    )
    supported = sorted({label for label in y_true})
    metrics["macro_f1_observed_classes"] = (
        macro_f1(y_true, y_pred, class_order=supported) if y_true else None
    )
    metrics["balanced_accuracy_observed_classes"] = (
        balanced_accuracy(y_true, y_pred, class_order=supported) if y_true else None
    )
    majority_label = Counter(y_true).most_common(1)[0][0] if y_true else None
    majority_pred = [majority_label] * len(y_true)
    baseline = {
        "label": majority_label,
        "accuracy": (sum(a == b for a, b in zip(y_true, majority_pred, strict=True)) / len(y_true))
        if y_true
        else None,
        "balanced_accuracy": balanced_accuracy(y_true, majority_pred, class_order=labels)
        if y_true
        else None,
        "macro_f1": macro_f1(y_true, majority_pred, class_order=labels) if y_true else None,
        "gold_counts": dict(sorted(Counter(y_true).items())),
    }
    curve = risk_coverage_curve(correct, confidence) if confidence else []
    risk = {
        "curve": [point.as_dict() for point in curve],
        "coverage_at_target_error": {
            str(target): max(
                (point.coverage for point in curve if point.risk <= target), default=None
            )
            for target in TARGET_ERRORS
        },
    }
    correct_count = sum(correct)
    return {
        "family": family,
        "legal_labels": labels,
        "record_count": total,
        "resolved_count": resolved,
        "correct_count": correct_count,
        "coverage": resolved / total if total else None,
        "valid_label_rate": (sum(label in set(labels) for label in y_pred) / len(y_pred))
        if y_pred
        else None,
        "accuracy_95_ci": wilson(correct_count, resolved) if resolved else None,
        "status_counts": dict(sorted(statuses.items())),
        "metrics": metrics,
        "majority_baseline": baseline,
        "per_class": _per_class(y_true, y_pred, labels),
        "predicted_counts": dict(sorted(Counter(y_pred).items())),
        "risk_coverage": risk,
        "reliability": _reliability_bins(correct, confidence) if confidence else [],
        "confidence_histogram": _histogram(confidence) if confidence else [],
        "latency": latency_summary(latencies),
        "actual_cost": sum(costs) if costs else None,
        "cost_per_1000": (sum(costs) / total * 1000.0) if costs and total else None,
        "usage_metadata_available": bool(costs),
    }


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--predictions-dir", type=Path, default=EXPERIMENT_DIR / "runs")
    parser.add_argument("--output", type=Path, default=EXPERIMENT_DIR)
    args = parser.parse_args()

    typed_spec = json.loads(
        (EXPERIMENT_DIR / "typed-question-spec.json").read_text(encoding="utf-8")
    )
    families = sorted(typed_spec["families"])
    reports: dict[str, Any] = {}
    for family in families:
        labels = typed_spec["families"][family]["legal_labels"]
        rows = _load_rows(family)
        predictions = _load_predictions(args.predictions_dir / family / "predictions.jsonl")
        reports[family] = _family_report(family, labels, rows, predictions)

    aggregate_records = sum(report["record_count"] for report in reports.values())
    aggregate_resolved = sum(report["resolved_count"] for report in reports.values())
    aggregate_correct = sum(report["correct_count"] for report in reports.values())
    aggregate_statuses: Counter[str] = Counter()
    for report in reports.values():
        aggregate_statuses.update(report["status_counts"])
    results = {
        "experiment_id": EXPERIMENT_ID,
        "partition": PARTITION,
        "provider": "openrouter",
        "model": "typesafe/jev-1.13",
        # Flat summary fields so the run-telemetry ledger reads this file directly.
        "record_count": aggregate_records,
        "resolved_count": aggregate_resolved,
        "correct_count": aggregate_correct,
        "accuracy": aggregate_correct / aggregate_resolved if aggregate_resolved else None,
        "accuracy_95_ci": wilson(aggregate_correct, aggregate_resolved)
        if aggregate_resolved
        else None,
        "status_counts": dict(sorted(aggregate_statuses.items())),
        "families": reports,
        "aggregate": {
            "record_count": aggregate_records,
            "resolved_count": aggregate_resolved,
            "correct_count": aggregate_correct,
            "coverage": aggregate_resolved / aggregate_records if aggregate_records else None,
            "micro_accuracy": aggregate_correct / aggregate_resolved
            if aggregate_resolved
            else None,
            "macro_accuracy_over_families": (
                sum(report["metrics"]["accuracy"] for report in reports.values()) / len(reports)
                if reports
                and all(report["metrics"]["accuracy"] is not None for report in reports.values())
                else None
            ),
        },
        "gold_provenance": "deterministic_verifier (frozen GLEIF source field value)",
        "gold_not_used_for_provider_request": True,
    }
    (args.output / "results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = [
        f"# {EXPERIMENT_ID} — Jev 1.13 as a closed-set GLEIF classifier",
        "",
        (
            f"Partition `{PARTITION}`; model `typesafe/jev-1.13`; gold is the frozen GLEIF "
            "source field value (`deterministic_verifier`). Each family is reported beside a "
            "majority-class baseline because raw accuracy is misleading under class imbalance."
        ),
        "",
        (
            f"Blind items: **{aggregate_records}** ({aggregate_resolved} resolved, "
            f"micro-accuracy {_fmt(results['aggregate']['micro_accuracy'])})."
        ),
        "",
    ]
    for family, report in reports.items():
        metrics = report["metrics"]
        baseline = report["majority_baseline"]
        risk = report["risk_coverage"]["coverage_at_target_error"]
        lines += [
            f"## {family}",
            "",
            (
                f"- items `{report['record_count']}`; resolved `{report['resolved_count']}`; "
                f"coverage `{_fmt(report['coverage'])}`; valid-label rate "
                f"`{_fmt(report['valid_label_rate'])}`"
            ),
            (
                f"- accuracy `{_fmt(metrics['accuracy'])}` "
                f"(95% Wilson `{report['accuracy_95_ci']}`) vs majority baseline "
                f"`{_fmt(baseline['accuracy'])}` (always `{baseline['label']}`)"
            ),
            (
                f"- balanced accuracy `{_fmt(metrics['balanced_accuracy'])}` vs baseline "
                f"`{_fmt(baseline['balanced_accuracy'])}`"
            ),
            (
                f"- macro-F1 `{_fmt(metrics['macro_f1'])}` vs baseline "
                f"`{_fmt(baseline['macro_f1'])}`; over classes with gold support "
                f"`{_fmt(metrics['macro_f1_observed_classes'])}`"
            ),
            (
                f"- Brier `{_fmt(metrics['brier'])}`; NLL `{_fmt(metrics['nll'])}`; "
                f"ECE `{_fmt(metrics['ece'])}`"
            ),
            (
                f"- risk/coverage: coverage at 1% risk `{_fmt(risk['0.01'])}`, at 5% risk "
                f"`{_fmt(risk['0.05'])}`"
            ),
            (
                f"- status counts `{report['status_counts']}`; p95 latency "
                f"`{_fmt(report['latency'].get('p95_ms'), 1)}` ms; cost per 1000 "
                f"`{_fmt(report['cost_per_1000'])}`"
            ),
            f"- gold distribution `{baseline['gold_counts']}`",
            "",
        ]
    (args.output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(results["aggregate"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
