"""Recompute the frozen multidomain Qwen report from immutable predictions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eval_lab.schema import JudgePrediction

try:
    from scripts.run_multidomain_qwen import _load_pool, _metrics
except ModuleNotFoundError:
    from run_multidomain_qwen import _load_pool, _metrics


def _load_predictions(path: Path) -> dict[str, dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in (path / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    predictions = {row["record_id"]: row for row in rows}
    if len(predictions) != len(rows):
        raise ValueError(f"duplicate prediction IDs in {path}")
    return predictions


def _fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)

    pool = Path(args.pool)
    pool_rows, records = _load_pool(pool, args.partition)
    source = Path(args.input)
    source_predictions = _load_predictions(source)
    expected_ids = {record.record_id for record in records}
    if set(source_predictions) != expected_ids:
        raise ValueError("input predictions do not exactly match the frozen partition")
    predictions = [
        JudgePrediction.model_validate(source_predictions[record.record_id]["prediction"])
        for record in records
    ]
    scoring_rows = [
        {**row, "gold_label": record.gold.label}
        for row, record in zip(pool_rows, records, strict=True)
    ]
    metrics = _metrics(scoring_rows, predictions)
    results = {
        "experiment_id": "EXP-20260921-013-qwen-multidomain-holdout",
        "partition": args.partition,
        "model": "qwen3.8-flash",
        "provider": "yolo-auto",
        "source_predictions": str(source),
        "record_count": len(records),
        "metrics": metrics,
        "probabilities_available": any(prediction.probabilities is not None for prediction in predictions),
        "gold_not_used_for_provider_request": True,
    }
    (output / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        f"# EXP-20260921-013 — {args.partition} report",
        "",
        f"Source predictions: `{source}`",
        "",
        "Provider: `yolo-auto`; model: `qwen3.8-flash`.",
        "Gold labels were used only after provider execution for scoring. Provider failures remain unresolved.",
        "",
        "| Dataset | Records | Resolved | Accuracy | 95% CI | Balanced accuracy | Macro-F1 | Unresolved | p95 ms | Statuses |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for dataset, values in metrics["by_dataset"].items():
        interval = values["accuracy_95_ci"]
        ci = "NA" if interval is None else f"[{interval['lower']:.4f}, {interval['upper']:.4f}]"
        lines.append(
            f"| `{dataset}` | {values['records']} | {values['resolved']} | {_fmt(values['accuracy'])} | {ci} | "
            f"{_fmt(values['balanced_accuracy'])} | {_fmt(values['macro_f1'])} | "
            f"{values['unresolved_rate']:.4f} | {_fmt(values['latency']['p95_ms'])} | `{values['status_counts']}` |"
        )
    lines.extend(
        [
            "",
            f"Overall resolved accuracy: `{_fmt(metrics['accuracy'])}`; unresolved rate: `{metrics['unresolved_rate']:.4f}`.",
            f"Overall accuracy 95% interval: `{metrics['accuracy_95_ci']}`.",
            "Qwen probabilities/logprobs were unavailable, so calibration metrics are not claimed.",
        ]
    )
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"partition": args.partition, "records": len(records), "metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, default=Path("experiments/EXP-20260921-013-qwen-multidomain-holdout"))
    parser.add_argument("--partition", choices=("public_selection", "blind_holdout"), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args), sort_keys=True))


if __name__ == "__main__":
    main()
