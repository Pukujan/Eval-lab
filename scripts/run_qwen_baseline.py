"""Run the bounded TASK-0006 Qwen feasibility slice."""

from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from eval_lab.calibration import apply_temperature_scaling, fit_temperature_scaling
from eval_lab.datasets.arc import ArcSourceMetadata, build_arc_dataset
from eval_lab.datasets.synthetic import generate_synthetic_fixtures
from eval_lab.judges.qwen import QwenJudge, QwenRuntimeConfig
from eval_lab.metrics.latency import latency_summary
from eval_lab.reporting import build_report, render_report_markdown
from eval_lab.schema import ExecutionStatus, JudgmentMode, Split


def _fetch_arc_rows(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    wanted = set(manifest["source_problem_ids"])
    rows_by_split: dict[str, list[dict[str, Any]]] = {"train": [], "validation": [], "test": []}
    for upstream_split in rows_by_split:
        response = httpx.get(
            "https://datasets-server.huggingface.co/rows",
            params={
                "dataset": manifest["dataset_id"],
                "config": manifest["config"],
                "split": upstream_split,
                "offset": 0,
                "length": 100,
                "revision": manifest["resolved_revision"],
            },
            timeout=30,
        )
        response.raise_for_status()
        rows_by_split[upstream_split] = [
            item["row"] for item in response.json().get("rows", []) if item["row"].get("id") in wanted
        ]
    found = {str(row["id"]) for rows in rows_by_split.values() for row in rows}
    if found != wanted:
        raise RuntimeError(f"ARC manifest IDs not fully retrievable: missing={sorted(wanted - found)}")
    return rows_by_split


def _runtime_observations(torch: Any) -> dict[str, Any]:
    observation: dict[str, Any] = {"platform": platform.platform()}
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info()
        observation["cuda"] = {
            "device": torch.cuda.get_device_name(0),
            "memory_total_bytes": int(total),
            "memory_free_bytes": int(free),
        }
    else:
        observation["cuda"] = {"available": False}
    try:
        import psutil

        observation["ram_available_bytes"] = int(psutil.virtual_memory().available)
    except ImportError:
        observation["ram_available_bytes"] = None
    return observation


def _write_jsonl(path: Path, values: list[Any]) -> None:
    path.write_text("".join(value.model_dump_json() + "\n" for value in values), encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    output_dir = Path(args.output_dir)
    existing = {path.name for path in output_dir.iterdir()} if output_dir.exists() else set()
    if existing - {"README.md", "experiment.yaml"}:
        raise FileExistsError(f"refusing to overwrite existing experiment: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    manifest_path = Path(args.arc_manifest)
    arc_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    metadata = ArcSourceMetadata(
        dataset_id=arc_manifest["dataset_id"],
        config=arc_manifest["config"],
        license=arc_manifest["license"],
        requested_revision=arc_manifest["requested_revision"],
        resolved_revision=arc_manifest["resolved_revision"],
        canonicalization_version=arc_manifest["canonicalization_version"],
        split_policy=arc_manifest["split_policy"],
        split_seed=arc_manifest["split_seed"],
        validation_dev_fraction=arc_manifest["validation_dev_fraction"],
        fingerprint=arc_manifest["fingerprint"],
    )
    arc_result = build_arc_dataset(_fetch_arc_rows(arc_manifest), metadata=metadata.model_copy(update={"fingerprint": None}))
    if arc_result.fingerprint != arc_manifest["fingerprint"]:
        raise RuntimeError("retrieved ARC rows do not match committed slice fingerprint")

    fixture = generate_synthetic_fixtures()
    synthetic = [record for record in fixture.records if record.split is Split.TEST][: max(args.limit - len(arc_result.records), 0)]
    if len(synthetic) < max(args.limit - len(arc_result.records), 0):
        synthetic.extend(record for record in fixture.records if record not in synthetic)
        synthetic = synthetic[: max(args.limit - len(arc_result.records), 0)]
    records = synthetic + arc_result.records[: max(args.limit - len(synthetic), 0)]
    records = records[: args.limit]

    config = QwenRuntimeConfig(model_id=args.model_id, revision=args.revision, context_cap=args.context_cap)
    judge = QwenJudge.from_pretrained(config)
    predictions = judge.predict(records)
    calibration_records = [
        record
        for record in fixture.records
        if record.split is Split.CALIBRATION and record.mode is JudgmentMode.SINGLE
    ]
    calibration_predictions = judge.predict(calibration_records)
    source_by_id = {source.source_problem_id: source for source in fixture.sources}
    domains = {
        record.record_id: source_by_id[record.source_problem_id].domain
        for record in synthetic
        if record.source_problem_id in source_by_id
    }
    domains.update({record.record_id: "arc_challenge" for record in arc_result.records})
    report = build_report(records, predictions, domain_by_record_id=domains)
    report["jev_comparison"] = {
        "status": "unavailable_provider_blocked",
        "reason": "no successful Jev predictions were available; TASK-0003 smoke was rate_limited",
    }
    calibrated_predictions = list(predictions)
    calibration_payload: dict[str, Any]
    calibration_applied = 0
    if calibration_records and all(
        prediction.execution_status is ExecutionStatus.OK and prediction.probabilities is not None
        for prediction in calibration_predictions
    ):
        artifact = fit_temperature_scaling(
            calibration_records,
            calibration_predictions,
            class_order=["pass", "fail"],
        )
        for index, (record, prediction) in enumerate(zip(records, predictions, strict=True)):
            if record.mode is not JudgmentMode.SINGLE or prediction.probabilities is None:
                continue
            calibrated_probabilities = apply_temperature_scaling(prediction.probabilities, artifact)
            assert isinstance(calibrated_probabilities, dict)
            calibrated_label = max(calibrated_probabilities, key=calibrated_probabilities.get)
            calibrated_predictions[index] = prediction.model_copy(
                update={
                    "label": calibrated_label,
                    "probabilities": calibrated_probabilities,
                    "provider_metadata": {
                        **prediction.provider_metadata,
                        "calibration_method": artifact.method,
                        "calibration_temperature": artifact.parameters["temperature"],
                    },
                }
            )
            calibration_applied += 1
        calibrated_report = build_report(records, calibrated_predictions, domain_by_record_id=domains)
        calibration_payload = {
            "status": "completed",
            "fit_record_count": len(calibration_records),
            "applied_record_count": calibration_applied,
            "artifact": artifact.model_dump(mode="json"),
        }
        report["calibrated"] = calibrated_report
    else:
        calibration_payload = {
            "status": "unavailable",
            "reason": "no successful single-label calibration predictions were available",
            "fit_record_count": len(calibration_records),
            "applied_record_count": 0,
        }
    report["calibration"] = calibration_payload
    report["experiment"] = {
        "model_id": config.model_id,
        "revision": judge.runtime_revision,
        "context_cap": config.context_cap,
        "record_ids": [record.record_id for record in records],
        "arc_manifest_fingerprint": arc_result.fingerprint,
    }
    _write_jsonl(output_dir / "predictions.jsonl", predictions)
    if calibration_applied:
        _write_jsonl(output_dir / "calibrated_predictions.jsonl", calibrated_predictions)
    (output_dir / "calibration.json").write_text(json.dumps(calibration_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "metrics.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "report.md").write_text(render_report_markdown(report), encoding="utf-8")
    observations = _runtime_observations(judge._torch)
    run_manifest = {
        "status": "completed",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": time.perf_counter() - started,
        "model_id": config.model_id,
        "requested_revision": config.revision,
        "resolved_revision": judge.runtime_revision,
        "runtime": "transformers",
        "device": judge.device,
        "dtype": judge.dtype,
        "context_cap": config.context_cap,
        "record_count": len(records),
        "record_ids": [record.record_id for record in records],
        "calibration_record_count": len(calibration_records),
        "calibration_record_ids": [record.record_id for record in calibration_records],
        "calibration": calibration_payload,
        "latency": latency_summary([prediction.latency_ms for prediction in predictions if prediction.latency_ms is not None]),
        "runtime_observations": observations,
        "arc_manifest_fingerprint": arc_result.fingerprint,
        "jev_comparison": report["jev_comparison"],
    }
    (output_dir / "manifest.json").write_text(json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--revision", default="main")
    parser.add_argument("--context-cap", type=int, default=4096)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--arc-manifest", default="manifests/arc-challenge-slice.json")
    parser.add_argument("--output-dir", default="experiments/EXP-20260920-002-qwen-0.6b-calibrated")
    args = parser.parse_args()
    print(run(args))


if __name__ == "__main__":
    main()
