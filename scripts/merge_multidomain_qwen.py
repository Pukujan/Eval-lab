"""Merge immutable base/retry Qwen outputs for one frozen partition."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval_lab.schema import JudgePrediction

try:
    from scripts.run_multidomain_qwen import _load_pool, _metrics
except ModuleNotFoundError:
    from run_multidomain_qwen import _load_pool, _metrics


def _load_predictions(path: Path) -> dict[str, dict[str, Any]]:
    rows = [json.loads(line) for line in (path / "predictions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    result = {row["record_id"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"duplicate prediction IDs in {path}")
    return result


def merge(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    pool = Path(args.pool)
    pool_rows, records = _load_pool(pool, args.partition)
    base = _load_predictions(Path(args.base))
    retry = _load_predictions(Path(args.retry))
    merged: list[dict[str, Any]] = []
    predictions: list[JudgePrediction] = []
    for row, record in zip(pool_rows, records, strict=True):
        source = retry.get(record.record_id, base.get(record.record_id))
        if source is None:
            raise ValueError(f"missing prediction for {record.record_id}")
        prediction = JudgePrediction.model_validate(source["prediction"])
        predictions.append(prediction)
        merged.append(
            {
                "dataset": row["dataset"],
                "partition": row["partition"],
                "source_problem_id": row["source_problem_id"],
                "record_id": record.record_id,
                "gold_label": record.gold.label,
                "prediction": prediction.model_dump(mode="json"),
            }
        )
    (output / "predictions.jsonl").write_bytes(
        b"".join((json.dumps(row, sort_keys=True) + "\n").encode("utf-8") for row in merged)
    )
    results = {
        "experiment_id": "EXP-20260921-013-qwen-multidomain-holdout",
        "partition": args.partition,
        "model": "qwen3.8-flash",
        "provider": "yolo-auto",
        "base_output": str(args.base),
        "retry_output": str(args.retry),
        "record_count": len(records),
        "status_counts": dict(Counter(prediction.execution_status.value for prediction in predictions)),
        "metrics": _metrics(merged, predictions),
        "probabilities_available": any(prediction.probabilities is not None for prediction in predictions),
        "created_at_utc": datetime.now(UTC).isoformat(),
    }
    (output / "results.json").write_bytes((json.dumps(results, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    (output / "report.md").write_text(
        f"# EXP-20260921-013-qwen-multidomain-holdout — {args.partition}\n\n"
        f"Merged {len(records)} records from immutable base `{args.base}` and retry `{args.retry}` outputs.\n\n"
        f"Status counts: `{results['status_counts']}`. Provider errors remain unresolved.\n",
        encoding="utf-8",
    )
    return {"partition": args.partition, "records": len(records), "status_counts": results["status_counts"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, default=Path("experiments/EXP-20260921-013-qwen-multidomain-holdout"))
    parser.add_argument("--partition", choices=("public_selection", "blind_holdout"), required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--retry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(merge(args), sort_keys=True))


if __name__ == "__main__":
    main()
