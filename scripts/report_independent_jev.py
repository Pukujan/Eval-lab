"""Score independent Jev arms and frozen comparison arms on the blind partition."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from eval_lab.metrics.summary import evaluate_prediction_set
from eval_lab.schema import (
    ExecutionStatus,
    JudgePrediction,
    JudgeRecord,
    JudgmentMode,
    PairwiseLabel,
)
from eval_lab.training import TextLogisticStudent

EXPERIMENT_ID = "EXP-20260921-014-independent-jev-benchmark"
QWEN_SOURCE = Path("experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-blind-merged-20260921/predictions.jsonl")
STUDENT_SOURCE = Path("experiments/EXP-20260920-008-small-judge-training/artifacts/student_D.json")


def _load_pool(pool: Path, partition: str) -> tuple[list[dict[str, Any]], list[JudgeRecord]]:
    rows = [
        json.loads(line)
        for line in (pool / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected = [row for row in rows if row["partition"] == partition]
    records = [JudgeRecord.model_validate(row["record"]) for row in selected]
    if len({record.record_id for record in records}) != len(records):
        raise ValueError("pool contains duplicate IDs")
    return selected, records


def _load_prediction_rows(path: Path) -> dict[str, JudgePrediction]:
    predictions: dict[str, JudgePrediction] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        payload = row.get("prediction", row)
        prediction = JudgePrediction.model_validate(payload)
        if prediction.record_id in predictions:
            raise ValueError(f"duplicate prediction ID: {prediction.record_id}")
        predictions[prediction.record_id] = prediction
    return predictions


def _align(records: list[JudgeRecord], predictions: dict[str, JudgePrediction], arm: str) -> list[JudgePrediction]:
    expected = {record.record_id for record in records}
    if set(predictions) != expected:
        raise ValueError(f"{arm} predictions do not exactly match the independent blind IDs")
    return [predictions[record.record_id] for record in records]


def _wilson(successes: int, trials: int) -> dict[str, float] | None:
    if not trials:
        return None
    z = 1.959963984540054
    estimate = successes / trials
    denominator = 1 + z * z / trials
    center = (estimate + z * z / (2 * trials)) / denominator
    margin = z * (estimate * (1 - estimate) / trials + z * z / (4 * trials * trials)) ** 0.5 / denominator
    return {"lower": max(0.0, center - margin), "upper": min(1.0, center + margin)}


def _majority_predictions(records: list[JudgeRecord], public_records: list[JudgeRecord]) -> list[JudgePrediction]:
    by_mode: dict[JudgmentMode, str] = {}
    for mode in (JudgmentMode.SINGLE, JudgmentMode.PAIRWISE):
        labels = [record.gold.label for record in public_records if record.mode is mode]
        if not labels:
            labels = [record.gold.label for record in records if record.mode is mode]
        counts = Counter(labels)
        legal = ["pass", "fail"] if mode is JudgmentMode.SINGLE else [item.value for item in PairwiseLabel]
        by_mode[mode] = max(legal, key=lambda label: (counts[label], -legal.index(label)))
    return [
        JudgePrediction(
            record_id=record.record_id,
            judge_id="frozen-majority-label",
            protocol_version="independent-jev-v1",
            label=by_mode[record.mode],
            execution_status=ExecutionStatus.OK,
            provider_metadata={"provider": "local", "selection_partition": "public_selection"},
        )
        for record in records
    ]


def _differential(left: list[JudgePrediction], right: list[JudgePrediction], records: list[JudgeRecord]) -> dict[str, Any]:
    comparable = [
        (record, a, b)
        for record, a, b in zip(records, left, right, strict=True)
        if a.execution_status is ExecutionStatus.OK and b.execution_status is ExecutionStatus.OK and a.label is not None and b.label is not None
    ]
    by_dataset: dict[str, dict[str, int]] = defaultdict(lambda: {"comparable": 0, "agreement": 0})
    for record, a, b in comparable:
        dataset = str(record.source_problem_id.split(":", 1)[0])
        by_dataset[dataset]["comparable"] += 1
        by_dataset[dataset]["agreement"] += int(a.label == b.label)
    return {
        "comparable_count": len(comparable),
        "agreement_count": sum(a.label == b.label for _record, a, b in comparable),
        "agreement_rate": (sum(a.label == b.label for _record, a, b in comparable) / len(comparable)) if comparable else None,
        "by_source_family": dict(sorted(by_dataset.items())),
    }


def _arm_summary(records: list[JudgeRecord], predictions: list[JudgePrediction], dataset_by_id: dict[str, str]) -> dict[str, Any]:
    metrics = evaluate_prediction_set(records, predictions, domain_by_record_id=dataset_by_id)
    resolved = [
        (record, prediction)
        for record, prediction in zip(records, predictions, strict=True)
        if prediction.execution_status is ExecutionStatus.OK and prediction.label is not None
    ]
    correct = sum(record.gold.label == prediction.label for record, prediction in resolved)
    metrics["accuracy_95_ci"] = _wilson(correct, len(resolved))
    metrics["unresolved_rate"] = (len(records) - len(resolved)) / len(records)
    return metrics


def _write_comparison(path: Path, predictions: list[JudgePrediction]) -> None:
    path.write_text("".join(prediction.model_dump_json() + "\n" for prediction in predictions), encoding="utf-8")


def _run(args: argparse.Namespace) -> dict[str, Any]:
    pool = Path(args.pool)
    rows, records = _load_pool(pool, "blind_holdout")
    dataset_by_id = {row["record"]["record_id"]: row["dataset"] for row in rows}
    _public_rows, public_records = _load_pool(pool, "public_selection")
    pinned = _align(records, _load_prediction_rows(Path(args.pinned)), "pinned Jev")
    rolling = _align(records, _load_prediction_rows(Path(args.rolling)), "rolling Jev")
    qwen = _align(records, _load_prediction_rows(Path(args.qwen)), "Qwen")
    student = TextLogisticStudent.from_artifact(json.loads(Path(args.student).read_text(encoding="utf-8")))
    local_single = {prediction.record_id: prediction for prediction in student.predict([record for record in records if record.mode is JudgmentMode.SINGLE])}
    local = [
        local_single[record.record_id]
        if record.mode is JudgmentMode.SINGLE
        else JudgePrediction(
            record_id=record.record_id,
            judge_id="tfidf-logistic-v1",
            protocol_version="task-0009-single-correctness-v1",
            execution_status=ExecutionStatus.SKIPPED,
            latency_ms=0.0,
            provider_metadata={"provider": "local", "scope": "single-answer correctness"},
            error={"type": "pairwise_out_of_scope"},
        )
        for record in records
    ]
    majority = _majority_predictions(records, public_records)
    arms = {
        "jev_pinned": pinned,
        "jev_rolling_canary": rolling,
        "qwen_comparison": qwen,
        "local_task0009_arm_D": local,
        "majority_baseline": majority,
    }
    for name, predictions in arms.items():
        _write_comparison(pool / f"predictions-{name}.jsonl", predictions)
    summaries = {name: _arm_summary(records, predictions, dataset_by_id) for name, predictions in arms.items()}
    differentials = {
        "pinned_vs_qwen": _differential(pinned, qwen, records),
        "pinned_vs_local": _differential(pinned, local, records),
        "pinned_vs_rolling": _differential(pinned, rolling, records),
    }
    results = {
        "experiment_id": EXPERIMENT_ID,
        "partition": "blind_holdout",
        "pool_fingerprint": json.loads((pool / "freeze.json").read_text(encoding="utf-8"))["records_fingerprint"],
        "record_count": len(records),
        "arms": summaries,
        "differentials": differentials,
        "primary_score": "metric vector; no JevBench composite",
        "gold_not_used_for_provider_requests": True,
        "jevbench_excluded": True,
    }
    output = pool / "results.json"
    output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        f"# {EXPERIMENT_ID} — independent blind evaluation",
        "",
        f"Pool: `{len(records)}` blind records; fingerprint `{results['pool_fingerprint']}`.",
        "",
        "| Arm | Resolved | Accuracy | 95% Wilson interval | Unresolved | Brier | NLL | ECE | p95 ms |",
        "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, summary in summaries.items():
        aggregate = summary["aggregate"]
        metrics = aggregate["metrics"] if aggregate else {}
        resolved = summary["successful_count"]
        accuracy = metrics.get("accuracy") if metrics else None
        ci = summary["accuracy_95_ci"]
        lines.append(
            f"| `{name}` | {resolved} | {accuracy} | `{ci}` | {summary['unresolved_rate']:.4f} | "
            f"{metrics.get('brier')} | {metrics.get('nll')} | {metrics.get('ece')} | {summary['latency']['p95_ms']} |"
        )
    lines.extend(
        [
            "",
            "JevBench tasks, labels, and its composite score are excluded from the primary score.",
            "",
            f"Pinned Jev vs Qwen agreement on comparable records: `{differentials['pinned_vs_qwen']['agreement_rate']}`.",
            f"Pinned Jev vs local student agreement on comparable records: `{differentials['pinned_vs_local']['agreement_rate']}`.",
            "",
            "Provider failures remain unresolved; rolling Jev is a separate canary and is never pooled with pinned Jev.",
        ]
    )
    (pool / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"record_count": len(records), "arms": {name: summary["status_counts"] for name, summary in summaries.items()}, "differentials": differentials}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, default=Path("experiments") / EXPERIMENT_ID)
    parser.add_argument("--pinned", type=Path, required=True)
    parser.add_argument("--rolling", type=Path, required=True)
    parser.add_argument("--qwen", type=Path, default=QWEN_SOURCE)
    parser.add_argument("--student", type=Path, default=STUDENT_SOURCE)
    args = parser.parse_args()
    print(json.dumps(_run(args), sort_keys=True))


if __name__ == "__main__":
    main()
