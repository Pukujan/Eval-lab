"""Run the preregistered local Qwen 4B raw/calibrated calibration study."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
from collections import Counter
from pathlib import Path
from typing import Any

from eval_lab.calibration import apply_calibration, fit_temperature_scaling
from eval_lab.judges.qwen import ContextLimitError, QwenJudge, QwenRuntimeConfig
from eval_lab.metrics.latency import latency_summary
from eval_lab.reporting import build_report
from eval_lab.schema import ExecutionStatus, JudgePrediction, JudgeRecord, JudgmentMode, Split

EXPERIMENT_ID = "EXP-20260921-017-judge-calibration"
POOL = Path("experiments/EXP-20260921-015-grok-luna-qwen-bakeoff")
PROMPT_VERSION = "eval-lab-system-one-local-v1"


def _load_records(pool: Path, partition: str, limit: int) -> tuple[list[JudgeRecord], dict[str, str], dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in (pool / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected = [row for row in rows if partition == "all" or row["partition"] == partition]
    if limit:
        selected = selected[:limit]
    records = [JudgeRecord.model_validate(row["record"]) for row in selected]
    if len({record.record_id for record in records}) != len(records):
        raise ValueError("selected pool contains duplicate record IDs")
    domains = {
        record.record_id: str(row.get("dataset", "unknown"))
        for row, record in zip(selected, records, strict=True)
    }
    manifest = json.loads((pool / "pool-manifest.json").read_text(encoding="utf-8"))
    return records, domains, manifest


def _prediction_failure(
    record: JudgeRecord,
    *,
    model_id: str,
    config: QwenRuntimeConfig,
    started: float,
    kind: str,
    error_type: str,
) -> JudgePrediction:
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=model_id,
        protocol_version=config.prompt_version,
        execution_status=ExecutionStatus.PROVIDER_ERROR,
        latency_ms=(time.perf_counter() - started) * 1000.0,
        provider_metadata={
            "provider": "local",
            "runtime": "transformers",
            "model_id": model_id,
            "requested_revision": config.revision,
            "context_cap": config.context_cap,
            "prompt_version": config.prompt_version,
        },
        error={"kind": kind, "type": error_type},
    )


def _predict(
    judge: QwenJudge,
    record: JudgeRecord,
    *,
    model_id: str,
    config: QwenRuntimeConfig,
) -> JudgePrediction:
    started = time.perf_counter()
    try:
        return judge.predict_one(record)
    except ContextLimitError as exc:
        return _prediction_failure(
            record,
            model_id=model_id,
            config=config,
            started=started,
            kind="context_limit",
            error_type=type(exc).__name__,
        )
    except Exception as exc:  # noqa: BLE001  # preserve one local-runtime failure per record
        return _prediction_failure(
            record,
            model_id=model_id,
            config=config,
            started=started,
            kind="local_runtime_error",
            error_type=type(exc).__name__,
        )


def _write_jsonl(path: Path, predictions: list[JudgePrediction]) -> None:
    path.write_text("".join(prediction.model_dump_json() + "\n" for prediction in predictions), encoding="utf-8")


def _load_predictions(path: Path) -> list[JudgePrediction]:
    return [
        JudgePrediction.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_progress(path: Path, predictions: list[JudgePrediction], *, record_count: int, model_id: str) -> None:
    path.write_text(
        json.dumps(
            {
                "model_id": model_id,
                "record_count": record_count,
                "completed_count": len(predictions),
                "status_counts": dict(sorted(Counter(prediction.execution_status.value for prediction in predictions).items())),
                "last_record_id": predictions[-1].record_id if predictions else None,
                "updated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _mode_classes(mode: JudgmentMode) -> list[str]:
    return ["pass", "fail"] if mode is JudgmentMode.SINGLE else ["A", "B", "TIE"]


def _fit_calibrators(records: list[JudgeRecord], predictions: list[JudgePrediction]) -> dict[str, Any]:
    by_id = {prediction.record_id: prediction for prediction in predictions}
    artifacts: dict[str, Any] = {}
    for mode in (JudgmentMode.SINGLE, JudgmentMode.PAIRWISE):
        mode_records = [record for record in records if record.mode is mode and record.split is Split.CALIBRATION]
        mode_predictions = [by_id[record.record_id] for record in mode_records]
        usable = [
            (record, prediction)
            for record, prediction in zip(mode_records, mode_predictions, strict=True)
            if prediction.execution_status is ExecutionStatus.OK and prediction.probabilities is not None
        ]
        key = mode.value
        if not usable:
            artifacts[key] = {
                "status": "unavailable",
                "reason": "no successful predictions with probabilities",
                "fit_record_count": 0,
                "fit_record_ids": [],
            }
            continue
        fit_records = [item[0] for item in usable]
        fit_predictions = [item[1] for item in usable]
        artifact = fit_temperature_scaling(
            fit_records,
            fit_predictions,
            class_order=_mode_classes(mode),
            code_version="task-0017-temperature-v1",
        )
        artifacts[key] = {
            "status": "completed",
            "fit_record_count": len(fit_records),
            "fit_record_ids": [record.record_id for record in fit_records],
            "artifact": artifact.model_dump(mode="json"),
        }
    return artifacts


def _load_calibration_artifacts(path: Path) -> dict[str, Any]:
    payload = json.loads((path / "calibration" / "artifacts.json").read_text(encoding="utf-8"))
    return payload["modes"]


def _apply_calibrators(
    records: list[JudgeRecord],
    predictions: list[JudgePrediction],
    modes: dict[str, Any],
) -> list[JudgePrediction]:
    calibrated: list[JudgePrediction] = []
    for record, prediction in zip(records, predictions, strict=True):
        mode = record.mode.value
        item = modes.get(mode, {})
        artifact_payload = item.get("artifact") if isinstance(item, dict) else None
        if prediction.probabilities is None or not artifact_payload:
            calibrated.append(prediction)
            continue
        from eval_lab.calibration.artifact import CalibrationArtifact

        artifact = CalibrationArtifact.model_validate(artifact_payload)
        probabilities = apply_calibration(prediction.probabilities, artifact)
        assert isinstance(probabilities, dict)
        calibrated.append(
            prediction.model_copy(
                update={
                    "probabilities": probabilities,
                    "provider_metadata": {
                        **prediction.provider_metadata,
                        "calibration_method": artifact.method,
                        "calibration_temperature": artifact.parameters["temperature"],
                        "calibration_fit_split": artifact.fit_split.value,
                    },
                }
            )
        )
    return calibrated


def _checksums(root: Path) -> None:
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "checksums.sha256":
            continue
        entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
    (root / "checksums.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


def _runtime_metadata(judge: QwenJudge, config: QwenRuntimeConfig) -> dict[str, Any]:
    return {
        "runtime": "transformers",
        "model_id": config.model_id,
        "requested_revision": config.revision,
        "resolved_revision": judge.runtime_revision,
        "device": judge.device,
        "dtype": judge.dtype,
        "quantization": config.quantization,
        "gpu_memory_fraction": config.gpu_memory_fraction,
        "context_cap": config.context_cap,
        "prompt_version": config.prompt_version,
        "score_semantics": "sum conditional log-likelihood of legal label continuation followed by softmax",
    }


def _report_markdown(result: dict[str, Any]) -> str:
    raw = result["raw_report"]["aggregate"]
    calibrated = result.get("calibrated_report", {}).get("aggregate") if result.get("calibrated_report") else None
    lines = [
        f"# {result['experiment_id']} — {result['partition']}",
        "",
        f"- Records: `{result['record_count']}`",
        f"- Model: `{result['runtime']['model_id']}`",
        f"- Runtime: `{result['runtime']['device']}` / `{result['runtime']['dtype']}`",
        "",
        "| View | Count | Accuracy | Brier | NLL | ECE |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    raw_metrics = raw.get("metrics") or {}
    lines.append(
        f"| raw | {raw.get('count', 0)} | {raw_metrics.get('accuracy')} | "
        f"{raw_metrics.get('brier')} | {raw_metrics.get('nll')} | {raw_metrics.get('ece')} |"
    )
    if calibrated is not None:
        calibrated_metrics = calibrated.get("metrics") or {}
        lines.append(
            f"| calibrated | {calibrated.get('count', 0)} | {calibrated_metrics.get('accuracy')} | "
            f"{calibrated_metrics.get('brier')} | {calibrated_metrics.get('nll')} | {calibrated_metrics.get('ece')} |"
        )
    lines.extend(
        [
            "",
            f"Status counts: `{result['status_counts']}`.",
            "Calibration is fit only on public_selection records and is never fit on blind labels.",
        ]
    )
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> Path:
    output = Path(args.output)
    if output.exists() and (output / "results.json").is_file() and not args.resume:
        raise FileExistsError(f"refusing to overwrite finalized output: {output}")
    if output.exists() and any(output.iterdir()) and not args.resume:
        raise FileExistsError(f"refusing to overwrite non-empty output: {output}")
    if args.resume and (output / "results.json").is_file():
        raise FileExistsError(f"refusing to resume finalized output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    records, domains, manifest = _load_records(Path(args.pool), args.partition, args.limit)
    config = QwenRuntimeConfig(
        model_id=args.model_id,
        revision=args.revision,
        context_cap=args.context_cap,
        device=args.device,
        dtype=args.dtype,
        quantization=args.quantization,
        gpu_memory_fraction=args.gpu_memory_fraction,
        prompt_version=PROMPT_VERSION,
    )
    started = time.perf_counter()
    judge = QwenJudge.from_pretrained(config)
    raw_path = output / "raw_predictions.jsonl"
    progress_path = output / "progress.json"
    existing = _load_predictions(raw_path) if args.resume and raw_path.is_file() else []
    by_id = {prediction.record_id: prediction for prediction in existing}
    expected_ids = {record.record_id for record in records}
    if len(by_id) != len(existing) or not set(by_id).issubset(expected_ids):
        raise ValueError("resume predictions contain duplicate or out-of-pool record IDs")
    if not existing:
        raw_path.write_text("", encoding="utf-8")
    pending = [record for record in records if record.record_id not in by_id]
    with raw_path.open("a", encoding="utf-8") as handle:
        for record in pending:
            prediction = _predict(judge, record, model_id=config.model_id, config=config)
            by_id[prediction.record_id] = prediction
            handle.write(prediction.model_dump_json() + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            _write_progress(progress_path, list(by_id.values()), record_count=len(records), model_id=config.model_id)
    if set(by_id) != expected_ids:
        raise RuntimeError("local Qwen run did not produce one result per selected record")
    predictions = [by_id[record.record_id] for record in records]
    runtime = _runtime_metadata(judge, config)
    raw_report = build_report(records, predictions, domain_by_record_id=domains)
    modes: dict[str, Any] | None = None
    if args.partition == "public_selection":
        modes = _fit_calibrators(records, predictions)
        (output / "calibration").mkdir()
        (output / "calibration" / "artifacts.json").write_text(
            json.dumps({"experiment_id": EXPERIMENT_ID, "modes": modes}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    elif args.calibration_run:
        modes = _load_calibration_artifacts(Path(args.calibration_run))
    calibrated_predictions = _apply_calibrators(records, predictions, modes or {}) if modes else None
    calibrated_report = (
        build_report(records, calibrated_predictions, domain_by_record_id=domains)
        if calibrated_predictions is not None
        else None
    )
    _write_jsonl(output / "raw_predictions.jsonl", predictions)
    if calibrated_predictions is not None:
        _write_jsonl(output / "calibrated_predictions.jsonl", calibrated_predictions)
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output.name,
        "partition": args.partition,
        "status": "completed_with_runtime_statuses",
        "record_count": len(records),
        "record_ids_sha256": hashlib.sha256("\n".join(record.record_id for record in records).encode()).hexdigest(),
        "source_pool": {
            "records_fingerprint": manifest["records_fingerprint"],
            "blind_record_ids_fingerprint": manifest["blind_record_ids_fingerprint"],
            "typed_question_spec_fingerprint": manifest["typed_question_spec_fingerprint"],
        },
        "runtime": runtime,
        "elapsed_seconds": time.perf_counter() - started,
        "status_counts": dict(sorted(Counter(prediction.execution_status.value for prediction in predictions).items())),
        "probability_count": sum(prediction.probabilities is not None for prediction in predictions),
        "latency": latency_summary([prediction.latency_ms for prediction in predictions if prediction.latency_ms is not None]),
        "raw_report": raw_report,
        "calibrated_report": calibrated_report,
        "calibration": {"modes": modes, "fit_source": "public_selection" if args.partition == "public_selection" else args.calibration_run},
        "environment": {"platform": platform.platform(), "python": platform.python_version()},
    }
    (output / "results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "provider-status.json").write_text(
        json.dumps({"experiment_id": EXPERIMENT_ID, "run_id": output.name, "status_counts": result["status_counts"], "runtime": runtime}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "report.md").write_text(_report_markdown(result), encoding="utf-8")
    _checksums(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", type=Path, default=POOL)
    parser.add_argument("--partition", choices=("public_selection", "blind_holdout"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--calibration-run", type=Path)
    parser.add_argument("--model-id", default="Qwen/Qwen3-4B")
    parser.add_argument("--revision", default="main")
    parser.add_argument("--context-cap", type=int, default=2048)
    parser.add_argument("--device")
    parser.add_argument("--dtype")
    parser.add_argument("--quantization", choices=("none", "4bit", "8bit"), default="4bit")
    parser.add_argument("--gpu-memory-fraction", type=float, default=0.8)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.limit < 0 or args.context_cap <= 0:
        raise SystemExit("--limit must be non-negative and --context-cap must be positive")
    print(run(args))


if __name__ == "__main__":
    main()
