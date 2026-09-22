"""Run Qwen3.8 Flash over one frozen TASK-0011 partition."""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from eval_lab.metrics.classification import classification_metrics
from eval_lab.metrics.latency import latency_summary
from eval_lab.schema import ExecutionStatus, JudgePrediction, JudgeRecord

try:
    from scripts.run_qwen_streaming_retry import _load_dotenv, _run_one
except ModuleNotFoundError:
    from run_qwen_streaming_retry import _load_dotenv, _run_one

MODEL = "qwen3.8-flash"
EXPERIMENT_ID = "EXP-20260921-013-qwen-multidomain-holdout"


def _binomial_interval(successes: int, trials: int) -> dict[str, float] | None:
    if trials <= 0:
        return None
    z = 1.959963984540054
    estimate = successes / trials
    denominator = 1 + z * z / trials
    center = (estimate + z * z / (2 * trials)) / denominator
    margin = z * ((estimate * (1 - estimate) / trials + z * z / (4 * trials * trials)) ** 0.5) / denominator
    return {"lower": max(0.0, center - margin), "upper": min(1.0, center + margin)}


def _load_pool(
    path: Path, partition: str, record_ids_file: Path | None = None
) -> tuple[list[dict[str, Any]], list[JudgeRecord]]:
    rows = [
        json.loads(line)
        for line in (path / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    requested = (
        {line.strip() for line in record_ids_file.read_text(encoding="utf-8").splitlines() if line.strip()}
        if record_ids_file is not None
        else None
    )
    selected = [
        row
        for row in rows
        if row["partition"] == partition
        and (requested is None or row["record"]["record_id"] in requested)
    ]
    if not selected:
        raise ValueError(f"no records found for partition {partition!r}")
    if requested is not None and {row["record"]["record_id"] for row in selected} != requested:
        raise ValueError("retry record IDs are not all present in the requested partition")
    records = [JudgeRecord.model_validate(row["record"]) for row in selected]
    if len({record.record_id for record in records}) != len(records):
        raise ValueError("partition contains duplicate record IDs")
    return selected, records


def _prediction_row(
    row: dict[str, Any], record: JudgeRecord, prediction: JudgePrediction
) -> dict[str, Any]:
    return {
        "dataset": row["dataset"],
        "partition": row["partition"],
        "source_problem_id": row["source_problem_id"],
        "record_id": record.record_id,
        "gold_label": record.gold.label,
        "prediction": prediction.model_dump(mode="json"),
    }


def _metrics(rows: list[dict[str, Any]], predictions: list[JudgePrediction]) -> dict[str, Any]:
    by_dataset: dict[str, list[tuple[str, str | None, ExecutionStatus, float | None]]] = defaultdict(list)
    for row, prediction in zip(rows, predictions, strict=True):
        by_dataset[row["dataset"]].append(
            (row["gold_label"], prediction.label, prediction.execution_status, prediction.latency_ms)
        )
    metrics: dict[str, Any] = {}
    for dataset, values in sorted(by_dataset.items()):
        resolved = [
            (gold, label)
            for gold, label, status, _latency in values
            if status is ExecutionStatus.OK and label is not None
        ]
        classification = (
            classification_metrics(
                [gold for gold, _label in resolved],
                [label for _gold, label in resolved],
            )
            if resolved
            else {
                "accuracy": None,
                "balanced_accuracy": None,
                "macro_f1": None,
                "brier": None,
                "nll": None,
                "ece": None,
            }
        )
        latencies = [latency for _gold, _label, _status, latency in values if latency is not None]
        metrics[dataset] = {
            "records": len(values),
            "resolved": len(resolved),
            "correct": sum(gold == label for gold, label in resolved),
            "unresolved_rate": (len(values) - len(resolved)) / len(values),
            "accuracy_95_ci": _binomial_interval(
                sum(gold == label for gold, label in resolved), len(resolved)
            ),
            **classification,
            "latency": latency_summary(latencies),
            "status_counts": dict(Counter(status.value for _, _, status, _latency in values)),
        }
    resolved = [
        (row["gold_label"], prediction.label)
        for row, prediction in zip(rows, predictions, strict=True)
        if prediction.execution_status is ExecutionStatus.OK and prediction.label is not None
    ]
    classification = (
        classification_metrics(
            [gold for gold, _label in resolved],
            [label for _gold, label in resolved],
        )
        if resolved
        else {
            "accuracy": None,
            "balanced_accuracy": None,
            "macro_f1": None,
            "brier": None,
            "nll": None,
            "ece": None,
        }
    )
    latencies = [prediction.latency_ms for prediction in predictions if prediction.latency_ms is not None]
    return {
        "records": len(rows),
        "resolved": len(resolved),
        "correct": sum(gold == label for gold, label in resolved),
        "unresolved_rate": (len(rows) - len(resolved)) / len(rows),
        "accuracy_95_ci": _binomial_interval(sum(gold == label for gold, label in resolved), len(resolved)),
        **classification,
        "latency": latency_summary(latencies),
        "status_counts": dict(Counter(prediction.execution_status.value for prediction in predictions)),
        "by_dataset": metrics,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    pool = Path(args.pool)
    rows, records = _load_pool(pool, args.partition, args.record_ids_file)
    environment = {**_load_dotenv(Path(args.env_file) if args.env_file else None), **os.environ}
    api_key = environment.get("YOLO_AUTO_API_KEY") or environment.get("YOLO_API_KEY") or environment.get("QWEN_API_KEY")
    if not api_key:
        raise RuntimeError("Qwen credential is unavailable")
    base_url = (environment.get("YOLO_AUTO_BASE_URL") or environment.get("QWEN_API_URL") or "https://api.yolo-auto.com/v1").rstrip("/")
    started = time.perf_counter()
    with httpx.Client() as client:
        def request(record: JudgeRecord) -> JudgePrediction:
            return _run_one(record, client=client, url=f"{base_url}/chat/completions", api_key=api_key, timeout=args.timeout)

        if args.workers == 1:
            predictions = [request(record) for record in records]
        else:
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                predictions = list(executor.map(request, records))
    if any(prediction.judge_id != MODEL for prediction in predictions):
        raise RuntimeError("provider returned an unexpected model identity")
    normalized = [_prediction_row(row, record, prediction) for row, record, prediction in zip(rows, records, predictions, strict=True)]
    (output / "predictions.jsonl").write_bytes(
        b"".join((json.dumps(item, sort_keys=True) + "\n").encode("utf-8") for item in normalized)
    )
    results = {
        "experiment_id": EXPERIMENT_ID,
        "partition": args.partition,
        "model": MODEL,
        "provider": "yolo-auto",
        "base_url": base_url,
        "pool_fingerprint": json.loads((pool / "source-manifest.json").read_text(encoding="utf-8"))["records_fingerprint"],
        "holdout_manifest_fingerprint": json.loads((pool / "holdout-manifest.json").read_text(encoding="utf-8"))["record_ids_fingerprint"],
        "record_count": len(records),
        "record_ids_file": str(args.record_ids_file) if args.record_ids_file else None,
        "workers": args.workers,
        "timeout_seconds": args.timeout,
        "streaming": True,
        "granularity": "one_record_per_request",
        "elapsed_seconds": time.perf_counter() - started,
        "metrics": _metrics(normalized, predictions),
        "latency_ms": latency_summary(
            [prediction.latency_ms for prediction in predictions if prediction.latency_ms is not None]
        ),
        "probabilities_available": any(prediction.probabilities is not None for prediction in predictions),
        "gold_not_used_for_provider_request": True,
        "created_at_utc": datetime.now(UTC).isoformat(),
    }
    (output / "results.json").write_bytes((json.dumps(results, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    (output / "report.md").write_text(
        f"# {EXPERIMENT_ID} — {args.partition}\n\n"
        f"Model: `{MODEL}` via YOLO-Auto; records: {len(records)}; "
        f"accuracy: {results['metrics']['accuracy']}; unresolved: "
        f"{len(records) - results['metrics']['resolved']}.\n\n"
        "Gold labels were used only after provider execution for objective scoring. "
        "Provider failures remain unresolved and no fallback label is fabricated.\n",
        encoding="utf-8",
    )
    return {"partition": args.partition, "records": len(records), "status_counts": results["metrics"]["status_counts"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, default=Path("experiments/EXP-20260921-013-qwen-multidomain-holdout"))
    parser.add_argument("--partition", choices=("public_selection", "blind_holdout"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--record-ids-file", type=Path)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    if args.workers < 1:
        raise ValueError("workers must be positive")
    print(json.dumps(run(args), sort_keys=True))


if __name__ == "__main__":
    main()
