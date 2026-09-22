"""Run pre-frozen repeat, label-order, and rubric-paraphrase Jev checks."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

import httpx

from eval_lab.escalation.providers import (
    OPENROUTER_PINNED_MODEL,
    OPENROUTER_ROLLING_MODEL,
    run_openrouter_jev,
)
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


def _skipped(record: JudgeRecord, model: str) -> JudgePrediction:
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=model,
        protocol_version="eval-lab-system-one-v1",
        execution_status=ExecutionStatus.SKIPPED,
        latency_ms=0.0,
        provider_metadata={"provider": "openrouter", "model": model},
        error={"type": "not_attempted_after_provider_stop"},
    )


def _status_code(prediction: JudgePrediction) -> int | None:
    value = prediction.error.get("status_code") if prediction.error else None
    return int(value) if isinstance(value, int | float) else None


def _primary_labels(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    source = path / "predictions.jsonl" if path.is_dir() else path
    labels: dict[str, str] = {}
    for raw in source.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        payload = json.loads(raw)
        prediction = payload.get("prediction", payload)
        if prediction.get("execution_status") == ExecutionStatus.OK.value and prediction.get("label") is not None:
            labels[str(prediction["record_id"])] = str(prediction["label"])
    return labels


def _run(args: argparse.Namespace) -> dict[str, Any]:
    pool = Path(args.pool)
    rows = [
        json.loads(line)
        for line in (pool / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    records = {row["record"]["record_id"]: JudgeRecord.model_validate(row["record"]) for row in rows if row["partition"] == "blind_holdout"}
    schedule = json.loads((pool / "perturbations.json").read_text(encoding="utf-8"))
    selected_ids = set(schedule["repeat_record_ids"]) | set(schedule["option_order_record_ids"]) | set(schedule["rubric_paraphrase_record_ids"])
    if not selected_ids <= set(records):
        raise ValueError("perturbation schedule contains an unknown record ID")
    env = {**_load_dotenv(Path(args.env_file) if args.env_file else None), **os.environ}
    key = env.get("OPENROUTER_API_KEY")
    model = args.model
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    result_rows: list[dict[str, Any]] = []
    schedule_rows = [
        ("repeat", record_id, repeat_index, None, None)
        for record_id in schedule["repeat_record_ids"]
        for repeat_index in range(int(schedule["repeat_count"]))
    ]
    schedule_rows.extend(("option_order", record_id, None, {record_id: schedule["option_order"][record_id]}, None) for record_id in schedule["option_order_record_ids"])
    schedule_rows.extend(("rubric_paraphrase", record_id, None, None, {record_id: schedule["rubric_paraphrase"]}) for record_id in schedule["rubric_paraphrase_record_ids"])
    stop_reason: str | None = None
    consecutive_provider_errors = 0
    with httpx.Client(timeout=args.timeout) as client:
        for kind, record_id, repeat_index, label_orders, instruction_overrides in schedule_rows:
            record = records[record_id]
            prediction = (
                _skipped(record, model)
                if stop_reason is not None
                else run_openrouter_jev(
                    [record],
                    model=model,
                    api_key=key,
                    client=client,
                    timeout=args.timeout,
                    label_orders=label_orders,
                    instruction_overrides=instruction_overrides,
                )[0]
            )
            row: dict[str, Any] = {"kind": kind, "record_id": record_id, "prediction": prediction.model_dump(mode="json")}
            if repeat_index is not None:
                row["repeat_index"] = repeat_index
            result_rows.append(row)
            code = _status_code(prediction)
            if code in {401, 403, 429}:
                stop_reason = f"http_{code}"
            elif prediction.execution_status is ExecutionStatus.PROVIDER_ERROR:
                consecutive_provider_errors += 1
                if consecutive_provider_errors >= 2:
                    stop_reason = "two_consecutive_provider_errors"
            elif prediction.execution_status is not ExecutionStatus.SKIPPED:
                consecutive_provider_errors = 0
    (output / "predictions.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in result_rows), encoding="utf-8")
    status_counts = dict(Counter(row["prediction"]["execution_status"] for row in result_rows))
    repeats: dict[str, list[str]] = {}
    for row in result_rows:
        if row["kind"] == "repeat" and row["prediction"]["execution_status"] == ExecutionStatus.OK.value:
            repeats.setdefault(row["record_id"], []).append(str(row["prediction"]["label"]))
    repeatability = {
        record_id: {"labels": labels, "stable": len(set(labels)) == 1}
        for record_id, labels in repeats.items()
    }
    option_rows = [row for row in result_rows if row["kind"] == "option_order" and row["prediction"]["execution_status"] == ExecutionStatus.OK.value]
    paraphrase_rows = [row for row in result_rows if row["kind"] == "rubric_paraphrase" and row["prediction"]["execution_status"] == ExecutionStatus.OK.value]
    results = {
        "experiment_id": EXPERIMENT_ID,
        "model": model,
        "schedule_fingerprint": __import__("hashlib").sha256(json.dumps(schedule, sort_keys=True).encode()).hexdigest(),
        "status_counts": status_counts,
        "stop_reason": stop_reason,
        "repeatability": repeatability,
        "repeatability_rate": (sum(item["stable"] for item in repeatability.values()) / len(repeatability)) if repeatability else None,
        "option_order_resolved": len(option_rows),
        "rubric_paraphrase_resolved": len(paraphrase_rows),
        "primary_arm_separate": True,
    }
    primary_labels = _primary_labels(args.primary)
    option_comparable = [
        row for row in option_rows if row["record_id"] in primary_labels and row["prediction"].get("label") is not None
    ]
    paraphrase_comparable = [
        row for row in paraphrase_rows if row["record_id"] in primary_labels and row["prediction"].get("label") is not None
    ]
    results["option_order_agreement_rate"] = (
        sum(row["prediction"]["label"] == primary_labels[row["record_id"]] for row in option_comparable) / len(option_comparable)
        if option_comparable else None
    )
    results["rubric_paraphrase_agreement_rate"] = (
        sum(row["prediction"]["label"] == primary_labels[row["record_id"]] for row in paraphrase_comparable) / len(paraphrase_comparable)
        if paraphrase_comparable else None
    )
    (output / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "report.md").write_text(
        f"# {EXPERIMENT_ID} — perturbations\n\nModel: `{model}`.\n\n"
        f"Status counts: `{status_counts}`; stop reason: `{stop_reason}`.\n\n"
        f"Repeatability rate: `{results['repeatability_rate']}` over `{len(repeatability)}` records.\n\n"
        f"Option-order agreement with the primary arm: `{results['option_order_agreement_rate']}`; rubric-paraphrase agreement: `{results['rubric_paraphrase_agreement_rate']}`.\n\n"
        "Option-order and rubric-paraphrase calls are separate robustness artifacts and are not pooled into the primary arm.\n",
        encoding="utf-8",
    )
    return {"model": model, "status_counts": status_counts, "repeatability_rate": results["repeatability_rate"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, default=Path("experiments") / EXPERIMENT_ID)
    parser.add_argument("--model", choices=(OPENROUTER_PINNED_MODEL, OPENROUTER_ROLLING_MODEL), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--primary", type=Path)
    args = parser.parse_args()
    print(json.dumps(_run(args), sort_keys=True))


if __name__ == "__main__":
    main()
