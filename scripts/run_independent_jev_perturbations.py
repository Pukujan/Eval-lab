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
from eval_lab.schema import ExecutionStatus, JudgeRecord

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
    with httpx.Client(timeout=args.timeout) as client:
        for record_id in schedule["repeat_record_ids"]:
            record = records[record_id]
            for repeat_index in range(int(schedule["repeat_count"])):
                prediction = run_openrouter_jev([record], model=model, api_key=key, client=client, timeout=args.timeout)[0]
                result_rows.append({"kind": "repeat", "record_id": record_id, "repeat_index": repeat_index, "prediction": prediction.model_dump(mode="json")})
        option_ids = schedule["option_order_record_ids"]
        option_predictions = run_openrouter_jev(
            [records[record_id] for record_id in option_ids],
            model=model,
            api_key=key,
            client=client,
            timeout=args.timeout,
            label_orders={record_id: value for record_id, value in schedule["option_order"].items()},
        )
        result_rows.extend({"kind": "option_order", "record_id": prediction.record_id, "prediction": prediction.model_dump(mode="json")} for prediction in option_predictions)
        paraphrase = schedule["rubric_paraphrase"]
        paraphrase_ids = schedule["rubric_paraphrase_record_ids"]
        paraphrase_predictions = run_openrouter_jev(
            [records[record_id] for record_id in paraphrase_ids],
            model=model,
            api_key=key,
            client=client,
            timeout=args.timeout,
            instruction_overrides={record_id: paraphrase for record_id in paraphrase_ids},
        )
        result_rows.extend({"kind": "rubric_paraphrase", "record_id": prediction.record_id, "prediction": prediction.model_dump(mode="json")} for prediction in paraphrase_predictions)
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
        "repeatability": repeatability,
        "repeatability_rate": (sum(item["stable"] for item in repeatability.values()) / len(repeatability)) if repeatability else None,
        "option_order_resolved": len(option_rows),
        "rubric_paraphrase_resolved": len(paraphrase_rows),
        "primary_arm_separate": True,
    }
    (output / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "report.md").write_text(
        f"# {EXPERIMENT_ID} — perturbations\n\nModel: `{model}`.\n\n"
        f"Status counts: `{status_counts}`.\n\n"
        f"Repeatability rate: `{results['repeatability_rate']}` over `{len(repeatability)}` records.\n\n"
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
    args = parser.parse_args()
    print(json.dumps(_run(args), sort_keys=True))


if __name__ == "__main__":
    main()
