"""Summarize pinned local decision-model predictions without mixing label spaces."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from eval_lab.metrics.classification import classification_metrics

EXP027 = "EXP-20260924-027-local-decision-bakeoff"
EXP028 = "EXP-20260924-028-legalbench-hearsay"
EXP015 = "EXP-20260921-015-grok-luna-qwen-bakeoff"
BENCHMARK = "exp027-frozen-pool"
LEGALBENCH = "exp028-legalbench-hearsay"
LABELS_BY_MODE = {"single": ["pass", "fail"], "pairwise": ["A", "B", "TIE"]}


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _wilson(successes: int, trials: int, z: float = 1.959963984540054) -> list[float] | None:
    if trials == 0:
        return None
    rate = successes / trials
    denominator = 1 + z**2 / trials
    center = (rate + z**2 / (2 * trials)) / denominator
    margin = z * math.sqrt(rate * (1 - rate) / trials + z**2 / (4 * trials**2)) / denominator
    return [max(0.0, center - margin), min(1.0, center + margin)]


def summarize_predictions(
    records: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    *,
    prediction_path: Path,
    mode_key: str | None = None,
    fixed_labels: list[str] | None = None,
) -> dict[str, Any]:
    expected = {record["record_id"]: record for record in records}
    by_id = {prediction["record_id"]: prediction for prediction in predictions}
    if len(by_id) != len(predictions):
        raise ValueError(f"duplicate prediction IDs in {prediction_path}")
    if set(by_id) != set(expected):
        missing = sorted(set(expected) - set(by_id))[:5]
        extra = sorted(set(by_id) - set(expected))[:5]
        raise ValueError(
            f"prediction IDs do not match benchmark pool; missing={missing}, extra={extra}"
        )

    aligned = [(record, by_id[record["record_id"]]) for record in records]
    counts = Counter(prediction["execution_status"] for _, prediction in aligned)
    resolved = [
        (record, prediction)
        for record, prediction in aligned
        if prediction.get("execution_status") == "ok" and prediction.get("label") is not None
    ]
    correct = sum(record["gold"]["label"] == prediction["label"] for record, prediction in resolved)
    modes = sorted({str(record[mode_key]) for record, _ in resolved}) if mode_key else ["all"]
    by_mode: dict[str, Any] = {}
    for mode in modes:
        group = [
            (record, prediction)
            for record, prediction in resolved
            if mode_key is None or str(record[mode_key]) == mode
        ]
        if not group:
            continue
        labels = fixed_labels or LABELS_BY_MODE.get(mode)
        if labels is None:
            raise ValueError(f"no fixed label order for mode {mode!r}")
        y_true = [str(record["gold"]["label"]) for record, _ in group]
        y_pred = [str(prediction["label"]) for _, prediction in group]
        probability_group = [
            (record, prediction)
            for record, prediction in group
            if prediction.get("probabilities") is not None
        ]
        probability_metrics = None
        if probability_group:
            probability_metrics = classification_metrics(
                [str(record["gold"]["label"]) for record, _ in probability_group],
                [str(prediction["label"]) for _, prediction in probability_group],
                [prediction["probabilities"] for _, prediction in probability_group],
                class_order=labels,
            )
        by_mode[mode] = {
            "record_count": len(group),
            "accuracy": sum(
                actual == predicted for actual, predicted in zip(y_true, y_pred, strict=True)
            )
            / len(group),
            "balanced_accuracy": (
                classification_metrics(y_true, y_pred, class_order=labels)["balanced_accuracy"]
            ),
            "macro_f1": classification_metrics(y_true, y_pred, class_order=labels)["macro_f1"],
            "probability_count": len(probability_group),
            "probability_metrics": probability_metrics,
        }

    latencies = [
        float(prediction["latency_ms"])
        for _, prediction in aligned
        if prediction.get("latency_ms") is not None
    ]
    return {
        "record_count": len(records),
        "resolved_count": len(resolved),
        "resolved_coverage": len(resolved) / len(records) if records else None,
        "unresolved_count": len(records) - len(resolved),
        "accuracy": correct / len(resolved) if resolved else None,
        "accuracy_95_wilson": _wilson(correct, len(resolved)),
        "status_counts": dict(sorted(counts.items())),
        "by_mode": by_mode,
        "probability_count": sum(item["probability_count"] for item in by_mode.values()),
        "latency_ms": {"p50": _percentile(latencies, 0.5), "p95": _percentile(latencies, 0.95)},
        "prediction_sha256": hashlib.sha256(prediction_path.read_bytes()).hexdigest(),
        "runner_revision": json.loads(
            (prediction_path.parent / "run-config.json").read_text(encoding="utf-8")
        )["runner_revision"],
    }


def _load_runs(
    *,
    experiment_root: Path,
    partition: str,
    records: list[dict[str, Any]],
    mode_key: str | None,
    fixed_labels: list[str] | None,
) -> dict[str, Any]:
    folder = experiment_root / f"{partition}-predictions"
    arms: dict[str, Any] = {}
    if not folder.exists():
        return arms
    for prediction_path in sorted(folder.glob("*/predictions.jsonl")):
        arm_id = prediction_path.parent.name
        predictions = _jsonl(prediction_path)
        arms[arm_id] = summarize_predictions(
            records,
            predictions,
            prediction_path=prediction_path,
            mode_key=mode_key,
            fixed_labels=fixed_labels,
        )
    return arms


def _markdown(experiment_id: str, partitions: dict[str, dict[str, Any]]) -> str:
    lines = [f"# {experiment_id} — local decision-model results", ""]
    for partition, arms in partitions.items():
        lines.extend(
            [
                f"## {partition.replace('_', ' ').title()}",
                "",
                "| Arm | Resolved | Coverage | Accuracy | 95% Wilson interval | Calibration by mode | p50 ms | p95 ms | Status counts |",
                "| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |",
            ]
        )
        for arm_id, result in sorted(arms.items()):
            interval = result["accuracy_95_wilson"]
            calibration = (
                "; ".join(
                    f"{mode}: {metrics.get('brier')}/{metrics.get('nll')}/{metrics.get('ece')}"
                    for mode, item in sorted(result["by_mode"].items())
                    if (metrics := item.get("probability_metrics")) is not None
                )
                or "unavailable"
            )
            lines.append(
                f"| `{arm_id}` | {result['resolved_count']}/{result['record_count']} | "
                f"{result['resolved_coverage']:.4f} | {result['accuracy']} | `{interval}` | `{calibration}` | "
                f"{result['latency_ms']['p50']} | {result['latency_ms']['p95']} | "
                f"`{result['status_counts']}` |"
            )
        if not arms:
            lines.append("No prediction runs are recorded yet.")
        else:
            lines.extend(
                [
                    "",
                    "### Class and calibration metrics by fixed label space",
                    "",
                    "| Arm | Mode | N | Accuracy | Balanced accuracy | Macro F1 | Brier | NLL | ECE |",
                    "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
                ]
            )
            for arm_id, result in sorted(arms.items()):
                for mode, values in sorted(result["by_mode"].items()):
                    metrics = values.get("probability_metrics") or {}
                    lines.append(
                        f"| `{arm_id}` | {mode} | {values['record_count']} | {values['accuracy']:.4f} | "
                        f"{values['balanced_accuracy']:.4f} | {values['macro_f1']:.4f} | "
                        f"{metrics.get('brier')} | {metrics.get('nll')} | {metrics.get('ece')} |"
                    )
        lines.append("")
    lines.extend(
        [
            "Calibration metrics are reported within each fixed label space in `results.json`; single-answer and pairwise records are not pooled for Brier, NLL, or ECE.",
            "Unresolved model failures remain statuses and are excluded from resolved accuracy. Public-selection results are descriptive and the blind holdout is the primary comparison.",
            "",
        ]
    )
    return "\n".join(lines)


def report(experiment_root: Path, legalbench_root: Path) -> dict[str, Any]:
    pool_rows = _jsonl(Path("experiments") / EXP015 / "records.jsonl")
    pool_fingerprint = json.loads(
        (experiment_root / "source-pool-fingerprint.json").read_text(encoding="utf-8")
    )
    partitions: dict[str, dict[str, Any]] = {}
    for partition in ("public", "blind"):
        pool_partition = "public_selection" if partition == "public" else "blind_holdout"
        records = [row["record"] for row in pool_rows if row["partition"] == pool_partition]
        partitions[partition] = _load_runs(
            experiment_root=experiment_root,
            partition=partition,
            records=records,
            mode_key="mode",
            fixed_labels=None,
        )
    results_027 = {
        "experiment_id": experiment_root.name,
        "dataset_fingerprint": pool_fingerprint["canonical_pool_fingerprint"],
        "primary_partition": "blind",
        "partitions": partitions,
        "calibration_policy": "native confidence only; metrics computed separately within each judgment mode",
    }
    (experiment_root / "results.json").write_text(
        json.dumps(results_027, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (experiment_root / "report.md").write_text(
        _markdown(experiment_root.name, partitions), encoding="utf-8"
    )

    legal_records = _jsonl(legalbench_root / "canonical-records.jsonl")
    legal_predictions: dict[str, Any] = {}
    folder = legalbench_root / "predictions"
    if folder.exists():
        for prediction_path in sorted(folder.glob("*/predictions.jsonl")):
            legal_predictions[prediction_path.parent.name] = summarize_predictions(
                legal_records,
                _jsonl(prediction_path),
                prediction_path=prediction_path,
                fixed_labels=["Yes", "No"],
            )
    source_manifest = json.loads(
        (legalbench_root / "source-manifest.json").read_text(encoding="utf-8")
    )
    results_028 = {
        "experiment_id": legalbench_root.name,
        "dataset_source": source_manifest,
        "split": "test",
        "gold_provenance": "benchmark answer key",
        "arms": legal_predictions,
        "interpretation_limit": "one fixed-label hearsay classification task; not general legal reasoning",
    }
    (legalbench_root / "results.json").write_text(
        json.dumps(results_028, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (legalbench_root / "report.md").write_text(
        _markdown(legalbench_root.name, {"test": legal_predictions}), encoding="utf-8"
    )
    return {"EXP-027": results_027, "EXP-028": results_028}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-root", type=Path, default=Path("experiments") / EXP027)
    parser.add_argument("--legalbench-root", type=Path, default=Path("experiments") / EXP028)
    args = parser.parse_args()
    result = report(args.experiment_root, args.legalbench_root)
    print(
        json.dumps(
            {
                key: {
                    "partitions": {
                        partition: {arm: summary["status_counts"] for arm, summary in arms.items()}
                        for partition, arms in value.get("partitions", {}).items()
                    }
                    if "partitions" in value
                    else {
                        arm: summary["status_counts"]
                        for arm, summary in value.get("arms", {}).items()
                    }
                }
                for key, value in result.items()
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
