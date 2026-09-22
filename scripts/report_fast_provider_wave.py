"""Build an offline comparison from separate normalized provider runs."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from eval_lab.reporting import build_report
from eval_lab.schema import ExecutionStatus, JudgePrediction, JudgeRecord


def _load_records(pool: Path, partition: str) -> tuple[list[JudgeRecord], dict[str, str]]:
    rows = [
        json.loads(line)
        for line in (pool / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected = [row for row in rows if partition == "all" or row["partition"] == partition]
    records = [JudgeRecord.model_validate(row["record"]) for row in selected]
    if not records or len({record.record_id for record in records}) != len(records):
        raise ValueError("selected pool is empty or contains duplicate IDs")
    domains = {record.record_id: str(row.get("dataset", "unknown")) for row, record in zip(selected, records, strict=True)}
    return records, domains


def _load_predictions(run: Path, records: list[JudgeRecord]) -> list[JudgePrediction]:
    candidates = sorted((run / "predictions").glob("*.jsonl"))
    if not candidates and (run / "predictions.jsonl").is_file():
        candidates = [run / "predictions.jsonl"]
    if len(candidates) != 1:
        raise ValueError(f"expected exactly one prediction file in {run}, found {len(candidates)}")
    predictions: list[JudgePrediction] = []
    for line in candidates[0].read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        payload = row.get("prediction") if isinstance(row, dict) and "prediction" in row else row
        predictions.append(JudgePrediction.model_validate(payload))
    expected = [record.record_id for record in records]
    actual = [prediction.record_id for prediction in predictions]
    if len(actual) != len(set(actual)) or set(actual) != set(expected):
        raise ValueError(f"prediction IDs in {run} do not match the selected pool")
    by_id = {prediction.record_id: prediction for prediction in predictions}
    return [by_id[record_id] for record_id in expected]


def _arm_summary(
    records: list[JudgeRecord], predictions: list[JudgePrediction], domains: dict[str, str]
) -> dict[str, Any]:
    resolved = [
        (record, prediction)
        for record, prediction in zip(records, predictions, strict=True)
        if prediction.execution_status is ExecutionStatus.OK and prediction.label is not None
    ]
    surfaced = sorted(
        {
            model_id
            for prediction in predictions
            for model_id in prediction.provider_metadata.get("surfaced_model_ids", [])
            if isinstance(model_id, str)
        }
    )
    for prediction in predictions:
        resolved_model = prediction.provider_metadata.get("resolved_model")
        if isinstance(resolved_model, str) and resolved_model:
            surfaced.append(resolved_model)
    surfaced = sorted(set(surfaced))
    return {
        "provider": predictions[0].provider_metadata.get("provider") if predictions else None,
        "requested_model": (
            predictions[0].provider_metadata.get("requested_model")
            or predictions[0].provider_metadata.get("model")
            if predictions
            else None
        ),
        "surfaced_model_ids": surfaced,
        "record_count": len(records),
        "resolved_count": len(resolved),
        "correct_count": sum(record.gold.label == prediction.label for record, prediction in resolved),
        "resolved_coverage": len(resolved) / len(records) if records else 0.0,
        "accuracy": (
            sum(record.gold.label == prediction.label for record, prediction in resolved) / len(resolved)
            if resolved
            else None
        ),
        "status_counts": dict(sorted(Counter(prediction.execution_status.value for prediction in predictions).items())),
        "native_probability_count": sum(prediction.probabilities is not None for prediction in predictions),
        "metrics": build_report(records, predictions, domain_by_record_id=domains),
    }


def _agreement(records: list[JudgeRecord], predictions: dict[str, list[JudgePrediction]]) -> dict[str, Any]:
    indexed = {arm: {prediction.record_id: prediction for prediction in values} for arm, values in predictions.items()}
    arms = sorted(predictions)
    output: dict[str, Any] = {}
    for index, left in enumerate(arms):
        for right in arms[index + 1 :]:
            comparable = 0
            agreement = 0
            for record in records:
                first = indexed[left][record.record_id]
                second = indexed[right][record.record_id]
                if (
                    first.execution_status is ExecutionStatus.OK
                    and second.execution_status is ExecutionStatus.OK
                    and first.label is not None
                    and second.label is not None
                ):
                    comparable += 1
                    agreement += int(first.label == second.label)
            output[f"{left}__vs__{right}"] = {
                "comparable_count": comparable,
                "agreement_count": agreement,
                "agreement_rate": agreement / comparable if comparable else None,
            }
    return output


def _checksums(root: Path) -> None:
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "checksums.sha256":
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
    (root / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--partition", choices=("public_selection", "blind_holdout", "all"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arm", action="append", required=True, help="arm_id=run_directory")
    args = parser.parse_args()
    output = args.output
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    records, domains = _load_records(args.pool, args.partition)
    runs: dict[str, Path] = {}
    for item in args.arm:
        arm, separator, run = item.partition("=")
        if not separator or not arm or not run or arm in runs:
            raise ValueError(f"invalid or duplicate --arm value: {item}")
        runs[arm] = Path(run)
    predictions = {arm: _load_predictions(run, records) for arm, run in runs.items()}
    summaries = {arm: _arm_summary(records, values, domains) for arm, values in predictions.items()}
    results = {
        "partition": args.partition,
        "record_count": len(records),
        "arms": summaries,
        "differential": {"pairs": _agreement(records, predictions)},
        "source_pool": str(Path(args.pool)),
        "gold_used_offline_only": True,
    }
    (output / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        f"# Fast provider wave — {args.partition}",
        "",
        "| Arm | Requested | Surfaced | Resolved | Coverage | Accuracy | Statuses |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for arm, summary in summaries.items():
        lines.append(
            f"| `{arm}` | `{summary['requested_model']}` | `{', '.join(summary['surfaced_model_ids']) or '(none)'}` | "
            f"{summary['resolved_count']}/{summary['record_count']} | {summary['resolved_coverage']:.4f} | "
            f"{summary['accuracy']} | `{summary['status_counts']}` |"
        )
    lines.extend(
        [
            "",
            "Provider failures and malformed outputs remain unresolved and are excluded from accuracy.",
            f"Same-record agreement: `{json.dumps(results['differential']['pairs'], sort_keys=True)}`.",
        ]
    )
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _checksums(output)
    print(json.dumps(results, sort_keys=True))


if __name__ == "__main__":
    main()
