"""Run one independently frozen OpenRouter Jev arm with explicit stop semantics."""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from eval_lab.escalation.providers import (
    OPENROUTER_PINNED_MODEL,
    OPENROUTER_ROLLING_MODEL,
    run_openrouter_jev,
)
from eval_lab.metrics.latency import latency_summary
from eval_lab.metrics.summary import evaluate_prediction_set
from eval_lab.schema import ExecutionStatus, JudgePrediction, JudgeRecord

EXPERIMENT_ID = "EXP-20260921-014-independent-jev-benchmark"


def _load_dotenv(path: Path | None) -> dict[str, str]:
    values: dict[str, str] = {}
    if path is None or not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _load_pool(pool: Path, partition: str, limit: int) -> tuple[list[dict[str, Any]], list[JudgeRecord]]:
    rows = [
        json.loads(line)
        for line in (pool / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected = [row for row in rows if row["partition"] == partition]
    if limit:
        selected = selected[:limit]
    records = [JudgeRecord.model_validate(row["record"]) for row in selected]
    if not records or len({record.record_id for record in records}) != len(records):
        raise ValueError("selected independent partition is empty or contains duplicate IDs")
    return selected, records


def _skipped(record: JudgeRecord, model: str, reason: str) -> JudgePrediction:
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=model,
        protocol_version="eval-lab-system-one-v1",
        execution_status=ExecutionStatus.SKIPPED,
        latency_ms=0.0,
        provider_metadata={"provider": "openrouter", "model": model},
        error={"type": reason},
    )


def _status_code(prediction: JudgePrediction) -> int | None:
    value = prediction.error.get("status_code") if prediction.error else None
    return int(value) if isinstance(value, int | float) else None


def _wilson(successes: int, trials: int) -> dict[str, float] | None:
    if trials == 0:
        return None
    z = 1.959963984540054
    estimate = successes / trials
    denominator = 1 + z * z / trials
    center = (estimate + z * z / (2 * trials)) / denominator
    margin = z * (estimate * (1 - estimate) / trials + z * z / (4 * trials * trials)) ** 0.5 / denominator
    return {"lower": max(0.0, center - margin), "upper": min(1.0, center + margin)}


def _prediction_row(row: dict[str, Any], prediction: JudgePrediction) -> dict[str, Any]:
    return {
        "dataset": row["dataset"],
        "partition": row["partition"],
        "source_problem_id": row["source_problem_id"],
        "record_id": prediction.record_id,
        "gold_label": row["record"]["gold"]["label"],
        "prediction": prediction.model_dump(mode="json"),
    }


def _run(args: argparse.Namespace) -> dict[str, Any]:
    model = args.model
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    pool = Path(args.pool)
    rows, records = _load_pool(pool, args.partition, args.limit)
    environment = {**_load_dotenv(Path(args.env_file) if args.env_file else None), **os.environ}
    api_key = environment.get("OPENROUTER_API_KEY")
    predictions: list[JudgePrediction] = []
    stop_reason: str | None = None
    consecutive_provider_errors = 0
    started = time.perf_counter()
    with httpx.Client(timeout=args.timeout) as client:
        for record in records:
            if stop_reason is not None:
                predictions.append(_skipped(record, model, "not_attempted_after_provider_stop"))
                continue
            prediction = run_openrouter_jev(
                [record], model=model, api_key=api_key, client=client, timeout=args.timeout
            )[0]
            predictions.append(prediction)
            code = _status_code(prediction)
            if code in {401, 403, 429}:
                stop_reason = f"http_{code}"
            elif prediction.execution_status is ExecutionStatus.PROVIDER_ERROR:
                consecutive_provider_errors += 1
                if consecutive_provider_errors >= 2:
                    stop_reason = "two_consecutive_provider_errors"
            else:
                consecutive_provider_errors = 0

    output_rows = [_prediction_row(row, prediction) for row, prediction in zip(rows, predictions, strict=True)]
    (output / "predictions.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in output_rows), encoding="utf-8"
    )
    domain_map = {row["record_id"]: row["dataset"] for row in output_rows}
    metrics = evaluate_prediction_set(records, predictions, domain_by_record_id=domain_map)
    resolved = [prediction for prediction in predictions if prediction.execution_status is ExecutionStatus.OK]
    correct = sum(prediction.label == record.gold.label for record, prediction in zip(records, predictions, strict=True) if prediction.execution_status is ExecutionStatus.OK)
    usage = [prediction.provider_metadata.get("usage") for prediction in predictions if isinstance(prediction.provider_metadata.get("usage"), dict)]
    costs = [item.get("cost") for item in usage if isinstance(item.get("cost"), (int, float))]
    results = {
        "experiment_id": EXPERIMENT_ID,
        "partition": args.partition,
        "provider": "openrouter",
        "model": model,
        "pool_fingerprint": json.loads((pool / "freeze.json").read_text(encoding="utf-8"))["records_fingerprint"],
        "blind_record_ids_fingerprint": json.loads((pool / "freeze.json").read_text(encoding="utf-8"))["blind_record_ids_fingerprint"],
        "record_count": len(records),
        "resolved_count": len(resolved),
        "correct_count": correct,
        "accuracy_95_ci": _wilson(correct, len(resolved)),
        "status_counts": dict(sorted(Counter(prediction.execution_status.value for prediction in predictions).items())),
        "stop_reason": stop_reason,
        "elapsed_seconds": time.perf_counter() - started,
        "metrics": metrics,
        "latency": latency_summary([prediction.latency_ms for prediction in predictions if prediction.latency_ms is not None]),
        "actual_cost": sum(float(value) for value in costs) if costs else None,
        "usage_metadata_available": bool(usage),
        "gold_not_used_for_provider_request": True,
        "created_at_utc": datetime.now(UTC).isoformat(),
    }
    (output / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = [
        f"# {EXPERIMENT_ID} — {model}",
        "",
        f"Partition: `{args.partition}`; records: `{len(records)}`; resolved: `{len(resolved)}`; correct: `{correct}`.",
        f"Accuracy among resolved predictions: `{correct / len(resolved) if resolved else None}`; 95% Wilson interval: `{results['accuracy_95_ci']}`.",
        f"Status counts: `{results['status_counts']}`; stop reason: `{stop_reason}`.",
        "",
        "Provider failures and unattempted records remain explicit execution states. No retry, fallback label, or JevBench item was used.",
    ]
    (output / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return {"model": model, "record_count": len(records), "status_counts": results["status_counts"], "stop_reason": stop_reason}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, default=Path("experiments") / EXPERIMENT_ID)
    parser.add_argument("--partition", choices=("public_selection", "blind_holdout"), default="blind_holdout")
    parser.add_argument("--model", choices=(OPENROUTER_PINNED_MODEL, OPENROUTER_ROLLING_MODEL), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    if args.limit < 0:
        raise ValueError("limit must be non-negative")
    print(json.dumps(_run(args), sort_keys=True))


if __name__ == "__main__":
    main()
