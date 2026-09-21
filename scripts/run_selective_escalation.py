"""Run the frozen selective-escalation experiment and write auditable results."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
from collections import Counter
from collections.abc import Mapping
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
    matched_random_record_ids,
    route_prediction,
    select_threshold,
)
from eval_lab.metrics.latency import latency_summary
from eval_lab.metrics.policy import summarize_policy_metrics
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
        if key in {"OPENROUTER_API_KEY", "YOLO_AUTO_API_KEY", "YOLO_API_KEY", "QWEN_API_KEY", "QWEN_API_URL"} and value:
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


def _load_predictions(path: Path) -> list[JudgePrediction]:
    if not path.exists():
        return []
    return [JudgePrediction.model_validate(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _route_outcome(
    *,
    local: JudgePrediction | None,
    external: JudgePrediction | None,
    escalate: bool,
) -> dict[str, Any]:
    if not escalate:
        if local is None:
            raise ValueError("local prediction is required for a local route")
        ok = local.execution_status is ExecutionStatus.OK
        return {
            "final_label": local.label if ok else None,
            "provider_status": "not_called",
            "provider_model": None,
            "provider_error": None,
        }
    if external is None:
        return {
            "final_label": None,
            "provider_status": "not_called",
            "provider_model": None,
            "provider_error": {"type": "provider_not_available"},
        }
    ok = external.execution_status is ExecutionStatus.OK
    return {
        "final_label": external.label if ok else None,
        "provider_status": external.execution_status.value,
        "provider_model": external.judge_id,
        "provider_error": external.error,
    }


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
        rows.append(
            {
                **route.as_dict(),
                **_route_outcome(
                    local=local_predictions[record.record_id],
                    external=escalated_predictions.get(record.record_id),
                    escalate=route.route is Route.ESCALATE,
                ),
            }
        )
    return rows


def _provider_only_rows(
    records: list[JudgeRecord],
    predictions_by_id: dict[str, JudgePrediction],
    *,
    model: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        outcome = _route_outcome(
            local=None,
            external=predictions_by_id.get(record.record_id),
            escalate=True,
        )
        if outcome["provider_model"] is None:
            outcome["provider_model"] = model
        rows.append({"record_id": record.record_id, "route": Route.ESCALATE.value, **outcome})
    return rows


def _all_provider_rows(
    records: list[JudgeRecord], predictions: list[JudgePrediction], *, model_only: str
) -> dict[str, JudgePrediction]:
    if any(prediction.judge_id != model_only for prediction in predictions):
        raise ValueError("provider model identity changed within an arm")
    return {prediction.record_id: prediction for prediction in predictions}


def _selected_predictions(
    rows: list[dict[str, Any]],
    local_by_id: Mapping[str, JudgePrediction],
    provider_by_id: Mapping[str, JudgePrediction],
) -> dict[str, JudgePrediction]:
    selected: dict[str, JudgePrediction] = {}
    for row in rows:
        record_id = str(row["record_id"])
        prediction = (
            local_by_id.get(record_id)
            if row.get("route") == Route.LOCAL.value
            else provider_by_id.get(record_id)
        )
        if prediction is not None:
            selected[record_id] = prediction
    return selected


def _ranking(
    records: list[JudgeRecord],
    predictions: Mapping[str, JudgePrediction],
    confidences: Mapping[str, float],
) -> tuple[list[bool], list[float]]:
    correct: list[bool] = []
    values: list[float] = []
    for record in records:
        prediction = predictions[record.record_id]
        correct.append(prediction.label == record.gold.label)
        values.append(float(confidences[record.record_id]))
    return correct, values


def _raw_confidences(predictions: list[JudgePrediction]) -> dict[str, float]:
    return {prediction.record_id: max(prediction.probabilities.values()) for prediction in predictions}


def _summary(
    records: list[JudgeRecord],
    rows: list[dict[str, Any]],
    domains: dict[str, str],
    *,
    selected_predictions: Mapping[str, JudgePrediction] | None = None,
    ranking_correct: list[bool] | None = None,
    ranking_confidence: list[float] | None = None,
    target_error: float | None = None,
    threshold: float | None = None,
) -> dict[str, Any]:
    return summarize_policy_metrics(
        records,
        rows,
        domain_by_record_id=domains,
        selected_predictions=selected_predictions,
        ranking_correct=ranking_correct,
        ranking_confidence=ranking_confidence,
        target_error=target_error,
        threshold=threshold,
    )


def _mark_collapsed(policy_results: dict[str, Any]) -> None:
    families: dict[str, list[str]] = {}
    for name in policy_results:
        for target in TARGETS:
            suffix = f"_target_{target:.2f}"
            if name.endswith(suffix):
                families.setdefault(name[: -len(suffix)], []).append(name)
                break
    for names in families.values():
        signatures = []
        for name in names:
            point = policy_results[name].get("selected_operating_point") or {}
            signatures.append((point.get("threshold"), policy_results[name].get("local_coverage")))
        collapsed = len(names) > 1 and len(set(signatures)) == 1
        collapsed_targets = [name.rsplit("_target_", 1)[-1] for name in names]
        for name in names:
            point = policy_results[name].get("selected_operating_point")
            if not isinstance(point, dict):
                continue
            point["collapsed"] = collapsed
            if collapsed:
                point["collapsed_targets"] = collapsed_targets


def _write_predictions(
    path: Path,
    predictions: list[JudgePrediction],
    source: Path | None,
) -> list[JudgePrediction]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if source is not None:
        if source.resolve() != path.resolve():
            path.write_bytes(source.read_bytes().replace(b"\r\n", b"\n"))
        return _load_predictions(path)
    path.write_bytes("".join(item.model_dump_json() + "\n" for item in predictions).encode("utf-8"))
    return predictions


def _provider_usage(predictions: list[JudgePrediction]) -> dict[str, Any]:
    latencies = [prediction.latency_ms for prediction in predictions if prediction.latency_ms is not None]
    statuses = Counter(prediction.execution_status.value for prediction in predictions)
    input_tokens = 0.0
    output_tokens = 0.0
    cost = 0.0
    usage_calls = 0
    for prediction in predictions:
        usage = prediction.provider_metadata.get("usage")
        if not isinstance(usage, dict):
            continue
        usage_calls += 1
        input_tokens += float(usage.get("input_tokens", 0.0) or 0.0)
        output_tokens += float(usage.get("output_tokens", 0.0) or 0.0)
        cost += float(usage.get("cost", 0.0) or 0.0)
    latency = dict(latency_summary(latencies))
    return {
        "calls": len(predictions),
        "status_counts": dict(statuses),
        "latency_ms": latency,
        "usage_available_calls": usage_calls,
        "input_tokens": input_tokens if usage_calls else None,
        "output_tokens": output_tokens if usage_calls else None,
        "cost": cost if usage_calls else None,
    }


def run(
    *,
    benchmark: Path = BENCHMARK,
    output: Path = EXPERIMENT,
    run_providers: bool = True,
    env_file: Path | None = None,
    provider_limit: int | None = None,
    provider_timeout: float = 20.0,
    include_rolling: bool = True,
    include_qwen: bool = True,
    include_pinned: bool = True,
    pinned_predictions_path: Path | None = None,
    rolling_predictions_path: Path | None = None,
    qwen_predictions_path: Path | None = None,
    experiment_id: str = "EXP-20260920-009-selective-escalation",
) -> dict[str, Any]:
    if env_file:
        _load_dotenv(env_file)
    records, domains, partitions = _load_records(benchmark / "records.jsonl")
    threshold_records = [record for record in records if partitions[record.record_id] == "threshold_selection"]
    final_records = [record for record in records if partitions[record.record_id] == "final_evaluation"]
    provider_records = final_records if provider_limit is None else final_records[:provider_limit]
    if not provider_records:
        raise ValueError("provider evaluation pool must not be empty")
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
    if pinned_predictions_path:
        pinned_source = pinned_predictions_path
        pinned_generated: list[JudgePrediction] = []
    elif run_providers and include_pinned:
        pinned_source = None
        pinned_generated = run_openrouter_jev(
            provider_records, model=OPENROUTER_PINNED_MODEL, timeout=provider_timeout
        )
    elif run_providers:
        pinned_source = output / "provider-pinned.jsonl"
        pinned_generated = []
    else:
        pinned_source = None
        pinned_generated = []
    if rolling_predictions_path:
        rolling_source = rolling_predictions_path
        rolling_generated: list[JudgePrediction] = []
    elif run_providers and include_rolling:
        rolling_source = None
        rolling_generated = run_openrouter_jev(
            provider_records, model=OPENROUTER_ROLLING_MODEL, timeout=provider_timeout
        )
    else:
        rolling_source = None
        rolling_generated = []
    if qwen_predictions_path:
        qwen_source = qwen_predictions_path
        qwen_generated: list[JudgePrediction] = []
    elif run_providers and include_qwen:
        qwen_source = None
        qwen_generated = run_yolo_qwen(
            provider_records,
            base_url=os.getenv("YOLO_AUTO_BASE_URL") or os.getenv("QWEN_API_URL", "https://api.yolo-auto.com/v1"),
            timeout=provider_timeout,
        )
    else:
        qwen_source = None
        qwen_generated = []
    output.mkdir(parents=True, exist_ok=True)
    pinned = _write_predictions(output / "provider-pinned.jsonl", pinned_generated, pinned_source)
    rolling = _write_predictions(output / "provider-rolling.jsonl", rolling_generated, rolling_source)
    qwen = _write_predictions(output / "provider-qwen.jsonl", qwen_generated, qwen_source)
    pinned_by_id = _all_provider_rows(provider_records, pinned, model_only=OPENROUTER_PINNED_MODEL) if pinned else {}
    _rolling_by_id = (
        _all_provider_rows(provider_records, rolling, model_only=OPENROUTER_ROLLING_MODEL) if rolling else {}
    )
    qwen_by_id = _all_provider_rows(provider_records, qwen, model_only="qwen3.8-flash") if qwen else {}
    thresholds: dict[str, Any] = {
        "confidence_definition": "max calibrated class probability; raw arm uses max raw class probability",
        "target_error_rates": list(TARGETS),
        "calibrated": threshold_calibrated_selection,
        "raw": threshold_raw_selection,
        "selection_partition": "threshold_selection",
        "final_partition": "final_evaluation",
    }
    (output / "thresholds.json").write_bytes(
        (json.dumps(thresholds, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    all_rows: list[dict[str, Any]] = []
    policy_results: dict[str, Any] = {}
    local_raw_by_id = {prediction.record_id: prediction for prediction in final_raw}
    local_calibrated_by_id = {prediction.record_id: prediction for prediction in final_calibrated}
    raw_confidence = _raw_confidences(final_raw)
    calibrated_ranking = _ranking(final_records, local_calibrated_by_id, final_confidence)
    raw_ranking = _ranking(final_records, local_raw_by_id, raw_confidence)
    local_only_rows = [
        {
            "record_id": record.record_id,
            "route": Route.LOCAL.value,
            **_route_outcome(
                local=local_raw_by_id[record.record_id],
                external=None,
                escalate=False,
            ),
        }
        for record in final_records
    ]
    policy_results["local_only"] = _summary(
        final_records,
        local_only_rows,
        domains,
        selected_predictions=local_raw_by_id,
        ranking_correct=raw_ranking[0],
        ranking_confidence=raw_ranking[1],
    )
    all_rows.extend({"policy": "local_only", **row} for row in local_only_rows)
    pinned_only_rows = _provider_only_rows(final_records, pinned_by_id, model=OPENROUTER_PINNED_MODEL)
    qwen_only_rows = _provider_only_rows(final_records, qwen_by_id, model="qwen3.8-flash")
    policy_results["pinned_jev_only"] = _summary(
        final_records,
        pinned_only_rows,
        domains,
        selected_predictions=pinned_by_id,
    )
    policy_results["qwen_flash_only"] = _summary(
        final_records,
        qwen_only_rows,
        domains,
        selected_predictions=qwen_by_id,
    )
    all_rows.extend({"policy": "pinned_jev_only", **row} for row in pinned_only_rows)
    all_rows.extend({"policy": "qwen_flash_only", **row} for row in qwen_only_rows)
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
        policy_specs = (
            (
                f"calibrated_local_to_jev_{suffix}",
                calibrated_jev,
                local_calibrated_by_id,
                pinned_by_id,
                calibrated_ranking,
                calibrated_threshold,
            ),
            (
                f"raw_local_to_jev_{suffix}",
                raw_jev,
                local_raw_by_id,
                pinned_by_id,
                raw_ranking,
                raw_threshold,
            ),
            (
                f"calibrated_local_to_qwen_flash_{suffix}",
                calibrated_qwen,
                local_calibrated_by_id,
                qwen_by_id,
                calibrated_ranking,
                calibrated_threshold,
            ),
        )
        for name, rows, local_map, provider_map, ranking, threshold in policy_specs:
            policy_results[name] = _summary(
                final_records,
                rows,
                domains,
                selected_predictions=_selected_predictions(rows, local_map, provider_map),
                ranking_correct=ranking[0],
                ranking_confidence=ranking[1],
                target_error=target,
                threshold=threshold,
            )
            all_rows.extend({"policy": name, **row} for row in rows)
        escalated_count = sum(row["route"] == Route.ESCALATE.value for row in calibrated_jev)
        random_ids = set(
            matched_random_record_ids([record.record_id for record in final_records], escalated_count, seed=20260920)
        )
        random_rows = []
        for record in final_records:
            use_provider = record.record_id in random_ids
            random_rows.append(
                {
                    "record_id": record.record_id,
                    "route": Route.ESCALATE.value if use_provider else Route.LOCAL.value,
                    **_route_outcome(
                        local=local_raw_by_id[record.record_id],
                        external=pinned_by_id.get(record.record_id),
                        escalate=use_provider,
                    ),
                    "random_seed": 20260920,
                    "matched_escalation_count": escalated_count,
                }
            )
        name = f"random_matched_to_jev_{suffix}"
        policy_results[name] = _summary(
            final_records,
            random_rows,
            domains,
            selected_predictions=_selected_predictions(random_rows, local_raw_by_id, pinned_by_id),
            ranking_correct=raw_ranking[0],
            ranking_confidence=raw_ranking[1],
            target_error=target,
            threshold=None,
        )
        all_rows.extend({"policy": name, **row} for row in random_rows)
    _mark_collapsed(policy_results)
    routing_path = output / "routing.jsonl"
    routing_path.write_bytes(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in all_rows).encode("utf-8")
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
        "experiment_id": experiment_id,
        "status": "completed_with_provider_statuses"
        if any(
            arm["status_counts"].get("ok", 0) != len(provider_records)
            for arm in (
                {
                    "status_counts": dict(Counter(item.execution_status.value for item in pinned)),
                },
                {
                    "status_counts": dict(Counter(item.execution_status.value for item in rolling)),
                },
                {
                    "status_counts": dict(Counter(item.execution_status.value for item in qwen)),
                },
            )
        )
        else "completed",
        "environment": {"platform": platform.platform(), "python": platform.python_version(), "git_commit": _git_head()},
        "benchmark_fingerprint": json.loads((benchmark / "fingerprint.json").read_text(encoding="utf-8"))["fingerprint"],
        "student": {"artifact": str(STUDENT_ARTIFACT), "selected_arm": "D", "student_id": student.artifact()["student_id"]},
        "calibration": calibration.model_dump(mode="json"),
        "counts": {
            "threshold_selection": len(threshold_records),
            "final_evaluation": len(final_records),
            "provider_evaluation": len(provider_records),
            "provider_selection": "deterministic prefix of frozen final-evaluation record order",
        },
        "provider_arms": {
            "openrouter_pinned": {"model": OPENROUTER_PINNED_MODEL, "status_counts": dict(Counter(item.execution_status.value for item in pinned))},
            "openrouter_rolling": {"model": OPENROUTER_ROLLING_MODEL, "status_counts": dict(Counter(item.execution_status.value for item in rolling))},
            "yolo_qwen_flash": {"model": "qwen3.8-flash", "status_counts": dict(Counter(item.execution_status.value for item in qwen))},
        },
        "provider_usage": {
            OPENROUTER_PINNED_MODEL: _provider_usage(pinned),
            OPENROUTER_ROLLING_MODEL: _provider_usage(rolling),
            "qwen3.8-flash": _provider_usage(qwen),
        },
        "policies": policy_results,
        "system_one_differential": {"comparable_count": len(differential), "agreement_count": sum(item["agree"] for item in differential), "rows": differential},
        "unresolved_policy_rule": "provider failures remain unresolved and never fall back to a local label",
    }
    (output / "results.json").write_bytes(
        (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    (output / "report.md").write_bytes(
        (
            f"# {experiment_id} — Selective escalation\n\n"
            f"Benchmark fingerprint: `{payload['benchmark_fingerprint']}`\n\n"
            f"Threshold-selection records: {len(threshold_records)}; "
            f"final-evaluation records: {len(final_records)}; "
            f"provider prefix: {len(provider_records)}.\n\n"
            "Provider call counts, statuses, latency summaries, token usage, and reported costs "
            "are recorded in `results.json` under `provider_usage`; normalized per-record evidence "
            "remains in the provider JSONL files.\n\n"
            "Provider failures remain unresolved and never fall back to a local label. "
            "Pinned Jev and rolling Jev are separate arms.\n"
        ).encode()
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=BENCHMARK)
    parser.add_argument("--output", type=Path, default=EXPERIMENT)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--skip-providers", action="store_true")
    parser.add_argument("--provider-limit", type=int, default=None)
    parser.add_argument("--provider-timeout", type=float, default=20.0)
    parser.add_argument("--skip-rolling", action="store_true")
    parser.add_argument("--skip-qwen", action="store_true")
    parser.add_argument("--skip-pinned", action="store_true")
    parser.add_argument("--pinned-predictions", type=Path)
    parser.add_argument("--rolling-predictions", type=Path)
    parser.add_argument("--qwen-predictions", type=Path)
    parser.add_argument("--experiment-id", default="EXP-20260920-009-selective-escalation")
    args = parser.parse_args()
    payload = run(
        benchmark=args.benchmark,
        output=args.output,
        run_providers=not args.skip_providers,
        env_file=args.env_file,
        provider_limit=args.provider_limit,
        provider_timeout=args.provider_timeout,
        include_rolling=not args.skip_rolling,
        include_qwen=not args.skip_qwen,
        include_pinned=not args.skip_pinned,
        pinned_predictions_path=args.pinned_predictions,
        rolling_predictions_path=args.rolling_predictions,
        qwen_predictions_path=args.qwen_predictions,
        experiment_id=args.experiment_id,
    )
    print(json.dumps({"counts": payload["counts"], "provider_arms": payload["provider_arms"]}, sort_keys=True))


if __name__ == "__main__":
    main()
