"""Run the frozen selective-escalation experiment and write auditable results."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from eval_lab.calibration import apply_temperature_scaling
from eval_lab.calibration.artifact import CalibrationArtifact
from eval_lab.escalation.providers import (
    OPENROUTER_PINNED_MODEL,
    OPENROUTER_ROLLING_MODEL,
    run_openrouter_jev,
    run_yolo_qwen,
)
from eval_lab.escalation.routing import (
    Route,
    evaluate_routing,
    matched_random_record_ids,
    route_prediction,
    select_threshold,
)
from eval_lab.schema import ExecutionStatus, JudgePrediction, JudgeRecord
from eval_lab.training import TextLogisticStudent

BENCHMARK = Path("benchmark/eval-lab-select-v0.1.0")
EXPERIMENT = Path("experiments/EXP-20260920-009-selective-escalation")
STUDENT_ARTIFACT = Path("experiments/EXP-20260920-008-small-judge-training/artifacts/student_D.json")
CALIBRATION_ARTIFACT = Path("experiments/EXP-20260920-008-small-judge-training/artifacts/calibration.json")
TARGETS = (0.01, 0.02, 0.05, 0.10)


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key in {"OPENROUTER_API_KEY", "YOLO_AUTO_API_KEY", "YOLO_API_KEY"} and value:
            os.environ.setdefault(key, value)


def _load_records(path: Path) -> tuple[list[JudgeRecord], dict[str, str], dict[str, str]]:
    records: list[JudgeRecord] = []
    domains: dict[str, str] = {}
    partitions: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        record = JudgeRecord.model_validate(row["record"])
        records.append(record)
        domains[record.record_id] = str(row["domain"])
        partitions[record.record_id] = str(row["partition"])
    if len({record.record_id for record in records}) != len(records):
        raise ValueError("benchmark record IDs are not unique")
    return records, domains, partitions


def _calibrated_predictions(
    predictions: list[JudgePrediction], artifact: CalibrationArtifact
) -> tuple[list[JudgePrediction], dict[str, float]]:
    output: list[JudgePrediction] = []
    confidences: dict[str, float] = {}
    for prediction in predictions:
        if prediction.probabilities is None:
            raise ValueError("student predictions must expose probabilities")
        probabilities = apply_temperature_scaling(prediction.probabilities, artifact)
        assert isinstance(probabilities, dict)
        label = max(probabilities, key=probabilities.get)
        calibrated = prediction.model_copy(
            update={
                "label": label,
                "probabilities": probabilities,
                "provider_metadata": {
                    **prediction.provider_metadata,
                    "calibrated": True,
                    "calibration": artifact.model_dump(mode="json"),
                },
            }
        )
        output.append(calibrated)
        confidences[prediction.record_id] = max(probabilities.values())
    return output, confidences


def _student_routes(
    records: list[JudgeRecord],
    predictions: list[JudgePrediction],
    *,
    threshold: float,
    calibrated_confidences: dict[str, float] | None,
    local_predictions: dict[str, JudgePrediction],
    escalated_predictions: dict[str, JudgePrediction],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record, prediction in zip(records, predictions, strict=True):
        route = route_prediction(
            prediction,
            threshold=threshold,
            calibrated_confidence=(calibrated_confidences or {}).get(record.record_id),
        )
        local = local_predictions[record.record_id]
        external = escalated_predictions.get(record.record_id)
        selected = local if route.route is Route.LOCAL else external
        rows.append(
            {
                **route.as_dict(),
                "final_label": selected.label if selected and selected.execution_status is ExecutionStatus.OK else None,
                "provider_status": selected.execution_status.value if selected else "not_called",
                "provider_model": selected.judge_id if selected else None,
                "provider_error": selected.error if selected else None,
            }
        )
    return rows


def _all_provider_rows(
    records: list[JudgeRecord], predictions: list[JudgePrediction], *, model_only: str
) -> dict[str, JudgePrediction]:
    if any(prediction.judge_id != model_only for prediction in predictions):
        raise ValueError("provider model identity changed within an arm")
    return {prediction.record_id: prediction for prediction in predictions}


def _summary(
    records: list[JudgeRecord], rows: list[dict[str, Any]], domains: dict[str, str]
) -> dict[str, Any]:
    return evaluate_routing(records, rows, domain_by_record_id=domains)


def run(
    *,
    benchmark: Path = BENCHMARK,
    output: Path = EXPERIMENT,
    run_providers: bool = True,
    env_file: Path | None = None,
) -> dict[str, Any]:
    if env_file:
        _load_dotenv(env_file)
    records, domains, partitions = _load_records(benchmark / "records.jsonl")
    threshold_records = [record for record in records if partitions[record.record_id] == "threshold_selection"]
    final_records = [record for record in records if partitions[record.record_id] == "final_evaluation"]
    student = TextLogisticStudent.from_artifact(json.loads(STUDENT_ARTIFACT.read_text(encoding="utf-8")))
    calibration = CalibrationArtifact.model_validate(json.loads(CALIBRATION_ARTIFACT.read_text(encoding="utf-8")))
    threshold_raw = student.predict(threshold_records)
    final_raw = student.predict(final_records)
    _, threshold_confidence = _calibrated_predictions(threshold_raw, calibration)
    final_calibrated, final_confidence = _calibrated_predictions(final_raw, calibration)
    threshold_raw_selection = {
        str(target): select_threshold(threshold_records, threshold_raw, target_error=target)
        for target in TARGETS
    }
    threshold_calibrated_selection = {
        str(target): select_threshold(
            threshold_records,
            threshold_raw,
            target_error=target,
            calibrated_confidences=threshold_confidence,
        )
        for target in TARGETS
    }
    pinned = run_openrouter_jev(final_records, model=OPENROUTER_PINNED_MODEL) if run_providers else []
    rolling = run_openrouter_jev(final_records, model=OPENROUTER_ROLLING_MODEL) if run_providers else []
    qwen = run_yolo_qwen(final_records) if run_providers else []
    pinned_by_id = _all_provider_rows(final_records, pinned, model_only=OPENROUTER_PINNED_MODEL) if pinned else {}
    _rolling_by_id = _all_provider_rows(final_records, rolling, model_only=OPENROUTER_ROLLING_MODEL) if rolling else {}
    qwen_by_id = _all_provider_rows(final_records, qwen, model_only="qwen3.8-flash") if qwen else {}
    output.mkdir(parents=True, exist_ok=True)
    (output / "provider-pinned.jsonl").write_text(
        "".join(prediction.model_dump_json() + "\n" for prediction in pinned), encoding="utf-8"
    )
    (output / "provider-rolling.jsonl").write_text(
        "".join(prediction.model_dump_json() + "\n" for prediction in rolling), encoding="utf-8"
    )
    (output / "provider-qwen.jsonl").write_text(
        "".join(prediction.model_dump_json() + "\n" for prediction in qwen), encoding="utf-8"
    )
    thresholds: dict[str, Any] = {
        "confidence_definition": "max calibrated class probability; raw arm uses max raw class probability",
        "target_error_rates": list(TARGETS),
        "calibrated": threshold_calibrated_selection,
        "raw": threshold_raw_selection,
        "selection_partition": "threshold_selection",
        "final_partition": "final_evaluation",
    }
    (output / "thresholds.json").write_text(json.dumps(thresholds, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    all_rows: list[dict[str, Any]] = []
    policy_results: dict[str, Any] = {}
    local_raw_by_id = {prediction.record_id: prediction for prediction in final_raw}
    local_calibrated_by_id = {prediction.record_id: prediction for prediction in final_calibrated}
    local_only_rows = [
        {
            "record_id": record.record_id,
            "route": Route.LOCAL.value,
            "final_label": local_raw_by_id[record.record_id].label,
            "provider_status": "not_called",
        }
        for record in final_records
    ]
    policy_results["local_only"] = _summary(final_records, local_only_rows, domains)
    all_rows.extend({"policy": "local_only", **row} for row in local_only_rows)
    for target in TARGETS:
        suffix = f"target_{target:.2f}"
        calibrated_threshold = threshold_calibrated_selection[str(target)]["selected"]["threshold"]
        raw_threshold = threshold_raw_selection[str(target)]["selected"]["threshold"]
        calibrated_jev = _student_routes(
            final_records,
            final_raw,
            threshold=calibrated_threshold,
            calibrated_confidences=final_confidence,
            local_predictions=local_calibrated_by_id,
            escalated_predictions=pinned_by_id,
        )
        raw_jev = _student_routes(
            final_records,
            final_raw,
            threshold=raw_threshold,
            calibrated_confidences=None,
            local_predictions=local_raw_by_id,
            escalated_predictions=pinned_by_id,
        )
        calibrated_qwen = _student_routes(
            final_records,
            final_raw,
            threshold=calibrated_threshold,
            calibrated_confidences=final_confidence,
            local_predictions=local_calibrated_by_id,
            escalated_predictions=qwen_by_id,
        )
        for name, rows in (
            (f"calibrated_local_to_jev_{suffix}", calibrated_jev),
            (f"raw_local_to_jev_{suffix}", raw_jev),
            (f"calibrated_local_to_qwen_flash_{suffix}", calibrated_qwen),
        ):
            policy_results[name] = _summary(final_records, rows, domains)
            all_rows.extend({"policy": name, **row} for row in rows)
        escalated_count = sum(row["route"] == Route.ESCALATE.value for row in calibrated_jev)
        random_ids = set(matched_random_record_ids([record.record_id for record in final_records], escalated_count, seed=20260920))
        random_rows = []
        for record in final_records:
            provider = pinned_by_id.get(record.record_id)
            use_provider = record.record_id in random_ids
            selected = provider if use_provider else local_raw_by_id[record.record_id]
            random_rows.append(
                {
                    "record_id": record.record_id,
                    "route": Route.ESCALATE.value if use_provider else Route.LOCAL.value,
                    "final_label": selected.label if selected.execution_status is ExecutionStatus.OK else None,
                    "provider_status": selected.execution_status.value,
                    "provider_model": selected.judge_id if use_provider else None,
                    "provider_error": selected.error,
                    "random_seed": 20260920,
                    "matched_escalation_count": escalated_count,
                }
            )
        name = f"random_matched_to_jev_{suffix}"
        policy_results[name] = _summary(final_records, random_rows, domains)
        all_rows.extend({"policy": name, **row} for row in random_rows)
    routing_path = output / "routing.jsonl"
    routing_path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in all_rows),
        encoding="utf-8",
    )
    differential = []
    for record in final_records:
        left = pinned_by_id.get(record.record_id)
        right = qwen_by_id.get(record.record_id)
        if left and right and left.execution_status is ExecutionStatus.OK and right.execution_status is ExecutionStatus.OK:
            differential.append(
                {
                    "record_id": record.record_id,
                    "jev_label": left.label,
                    "qwen_label": right.label,
                    "agree": left.label == right.label,
                }
            )
    payload = {
        "experiment_id": "EXP-20260920-009-selective-escalation",
        "status": "completed" if all(
            policy_results[name]["unresolved_count"] == 0
            for name in policy_results
            if name.startswith("local_only")
        ) else "completed_with_provider_statuses",
        "environment": {"platform": platform.platform(), "python": platform.python_version(), "git_commit": _git_head()},
        "benchmark_fingerprint": json.loads((benchmark / "fingerprint.json").read_text(encoding="utf-8"))["fingerprint"],
        "student": {"artifact": str(STUDENT_ARTIFACT), "selected_arm": "D", "student_id": student.artifact()["student_id"]},
        "calibration": calibration.model_dump(mode="json"),
        "counts": {"threshold_selection": len(threshold_records), "final_evaluation": len(final_records)},
        "provider_arms": {
            "openrouter_pinned": {"model": OPENROUTER_PINNED_MODEL, "status_counts": dict(Counter(item.execution_status.value for item in pinned))},
            "openrouter_rolling": {"model": OPENROUTER_ROLLING_MODEL, "status_counts": dict(Counter(item.execution_status.value for item in rolling))},
            "yolo_qwen_flash": {"model": "qwen3.8-flash", "status_counts": dict(Counter(item.execution_status.value for item in qwen))},
        },
        "policies": policy_results,
        "system_one_differential": {"comparable_count": len(differential), "agreement_count": sum(item["agree"] for item in differential), "rows": differential},
        "unresolved_policy_rule": "provider failures remain unresolved and never fall back to a local label",
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "report.md").write_text(
        "# EXP-20260920-009 — Selective escalation\n\n"
        f"Benchmark fingerprint: `{payload['benchmark_fingerprint']}`\n\n"
        f"Threshold records: {len(threshold_records)}; final records: {len(final_records)}.\n\n"
        "Provider statuses and unresolved calls are retained in `results.json` and the normalized provider JSONL files.\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=BENCHMARK)
    parser.add_argument("--output", type=Path, default=EXPERIMENT)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--skip-providers", action="store_true")
    args = parser.parse_args()
    payload = run(
        benchmark=args.benchmark,
        output=args.output,
        run_providers=not args.skip_providers,
        env_file=args.env_file,
    )
    print(json.dumps({"counts": payload["counts"], "provider_arms": payload["provider_arms"]}, sort_keys=True))


if __name__ == "__main__":
    main()
