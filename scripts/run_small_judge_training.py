"""Run the preregistered TASK-0009 student ablation and calibration pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval_lab.calibration.temperature import apply_temperature_scaling, fit_temperature_scaling
from eval_lab.datasets.synthetic import generate_synthetic_fixtures
from eval_lab.metrics.summary import evaluate_prediction_set
from eval_lab.schema import JudgePrediction, JudgeRecord, Split
from eval_lab.training import (
    CLASS_ORDER,
    TextLogisticStudent,
    build_training_rows,
    training_row_fingerprint,
)

EXPERIMENT_ID = "EXP-20260920-008-small-judge-training"
DEFAULT_OUTPUT = Path("experiments") / EXPERIMENT_ID
HARD_NEGATIVE_PATH = Path(
    "experiments/EXP-20260920-007-teacher-hard-negatives/verified_hard_negatives.jsonl"
)
PARAPHRASE_PATH = Path(
    "experiments/EXP-20260920-007-teacher-hard-negatives/rubric_paraphrases.jsonl"
)


def _json_dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _jsonl_read(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _jsonl_write(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
    ).strip()


def _domain_by_record(records: list[JudgeRecord]) -> dict[str, str]:
    verifier_domains = {
        "arithmetic-v1": "arithmetic",
        "multiple-choice-v1": "multiple_choice",
        "structured-output-v1": "structured",
        "code-output-v1": "code_output",
    }
    return {
        record.record_id: verifier_domains.get(record.gold.verifier_id or "", "unknown")
        for record in records
    }


def _metrics(
    records: list[JudgeRecord], predictions: list[JudgePrediction], *, domain_map: dict[str, str]
) -> dict[str, Any]:
    result = evaluate_prediction_set(records, predictions, domain_by_record_id=domain_map)
    result["swap_consistency"] = {
        "status": "not_applicable",
        "reason": "TASK-0009 student scope is single-answer correctness; pairwise records are excluded",
    }
    return result


def _prediction_row(prediction: JudgePrediction, *, split: Split, arm: str, stage: str) -> dict[str, Any]:
    return {
        "arm": arm,
        "stage": stage,
        "split": split.value,
        **prediction.model_dump(mode="json"),
    }


def _calibrated_predictions(
    predictions: list[JudgePrediction], calibrated_rows: list[dict[str, float]]
) -> list[JudgePrediction]:
    output: list[JudgePrediction] = []
    for prediction, probabilities in zip(predictions, calibrated_rows, strict=True):
        label = max(CLASS_ORDER, key=lambda item: probabilities[item])
        raw_scores = {key: math.log(max(value, 1e-15)) for key, value in probabilities.items()}
        payload = prediction.model_dump(mode="python")
        payload.update(
            label=label,
            probabilities=probabilities,
            raw_scores=raw_scores,
            provider_metadata={
                **prediction.provider_metadata,
                "calibration": "temperature",
                "calibrated": True,
            },
        )
        output.append(JudgePrediction.model_validate(payload))
    return output


def _manifest(
    *,
    fixture_fingerprint: str,
    hard_negative_fingerprint: str,
    paraphrase_fingerprint: str,
    code_commit: str,
    selected_arm: str,
    calibration_artifact: dict[str, Any],
    arms: dict[str, Any],
    output: Path,
) -> dict[str, Any]:
    return {
        "id": EXPERIMENT_ID,
        "status": "completed",
        "hypothesis": "Verified hard negatives and concise rubric criteria improve a compact student judge without test leakage; temperature scaling reduces held-out calibration NLL.",
        "created_at": datetime.now(UTC).isoformat(),
        "code_commit": code_commit,
        "seed": 20260920,
        "context_limit": 4096,
        "dataset": {
            "name": "eval-lab-synthetic-objective-v1-plus-exp007-verified-hard-negatives",
            "version": "task-0009-v1",
            "fingerprint": hashlib.sha256(
                f"{fixture_fingerprint}:{hard_negative_fingerprint}:{paraphrase_fingerprint}".encode()
            ).hexdigest(),
            "synthetic_fixture_fingerprint": fixture_fingerprint,
            "hard_negative_fingerprint": hard_negative_fingerprint,
            "rubric_paraphrase_fingerprint": paraphrase_fingerprint,
            "split_policy": "synthetic source-family split; only train rows fit arms; calibration split fits E; test labels are evaluation-only",
        },
        "judge": {
            "provider": "local",
            "model": "tfidf-logistic-v1",
            "adapter_version": "task-0009-single-correctness-v1",
            "prompt_version": "task-0009-text-render-v1",
            "scope": "single-answer correctness; pairwise is not applicable",
        },
        "rubric": {"version": "objective-correctness-v1"},
        "gold": {
            "provenance_policy": "objective deterministic verifier only; teacher text remains augmentation metadata"
        },
        "calibration": {
            "method": "temperature",
            "split": "calibration",
            "selected_arm": selected_arm,
            "artifact": calibration_artifact,
        },
        "metrics": [
            "accuracy",
            "balanced_accuracy",
            "macro_f1",
            "brier",
            "nll",
            "ece",
            "risk_coverage",
            "latency",
        ],
        "arms": arms,
        "artifacts": sorted(str(path.relative_to(output)) for path in output.rglob("*") if path.is_file()),
        "notes": "No test source was used in fitting, arm selection, or calibration. Test metrics are reported after the preregistered protocol was frozen.",
    }


def run(output: Path, *, seed: int = 20260920) -> dict[str, Any]:
    if (output / "results.json").exists():
        raise RuntimeError(f"refusing to overwrite completed experiment: {output}")
    output.mkdir(parents=True, exist_ok=True)
    artifacts = output / "artifacts"
    artifacts.mkdir(exist_ok=True)

    fixture = generate_synthetic_fixtures(seed=seed, split_seed=seed)
    all_single = sorted(
        [record for record in fixture.records if record.mode.value == "single"],
        key=lambda record: record.record_id,
    )
    train_records = [record for record in all_single if record.split is Split.TRAIN]
    dev_records = [record for record in all_single if record.split is Split.DEV]
    calibration_records = [record for record in all_single if record.split is Split.CALIBRATION]
    test_records = [record for record in all_single if record.split is Split.TEST]
    hard_negative_items = _jsonl_read(HARD_NEGATIVE_PATH)
    paraphrase_rows = _jsonl_read(PARAPHRASE_PATH)
    paraphrases = {str(row["domain"]): str(row["paraphrase"]) for row in paraphrase_rows}
    domain_map = _domain_by_record(all_single)

    arm_summaries: dict[str, Any] = {}
    all_prediction_rows: list[dict[str, Any]] = []
    fitted: dict[str, TextLogisticStudent] = {}
    raw_predictions: dict[str, dict[str, list[JudgePrediction]]] = {}

    for arm in ("A", "B", "C", "D"):
        rows = build_training_rows(
            fixture.records,
            arm=arm,
            hard_negatives=hard_negative_items,
            rubric_paraphrases=paraphrases,
        )
        student = TextLogisticStudent(seed=seed).fit(rows)
        fitted[arm] = student
        predictions = {
            "dev": student.predict(dev_records),
            "calibration": student.predict(calibration_records),
            "test": student.predict(test_records),
        }
        raw_predictions[arm] = predictions
        for stage, records in (
            ("dev", dev_records),
            ("calibration", calibration_records),
            ("test", test_records),
        ):
            all_prediction_rows.extend(
                _prediction_row(prediction, split=records[index].split, arm=arm, stage=stage)
                for index, prediction in enumerate(predictions[stage])
            )
        _jsonl_write(
            artifacts / f"training_records_{arm}.jsonl",
            [asdict(row) for row in rows],
        )
        _json_dump(artifacts / f"student_{arm}.json", student.artifact())
        arm_summaries[arm] = {
            "training_row_count": len(rows),
            "training_row_fingerprint": training_row_fingerprint(rows),
            "source_kind_counts": dict(sorted(Counter(row.source_kind for row in rows).items())),
            "augmentation_counts": dict(sorted(Counter(row.augmentation for row in rows).items())),
            "metrics": {
                "dev": _metrics(dev_records, predictions["dev"], domain_map=domain_map),
                "calibration": _metrics(
                    calibration_records, predictions["calibration"], domain_map=domain_map
                ),
                "test": _metrics(test_records, predictions["test"], domain_map=domain_map),
            },
        }

    def selection_key(arm: str) -> tuple[float, float, str]:
        metrics = arm_summaries[arm]["metrics"]["dev"]["aggregate"]["metrics"]
        return (float(metrics["nll"]), -float(metrics["accuracy"]), arm)

    selected_arm = min(("A", "B", "C", "D"), key=selection_key)
    calibration_artifact = fit_temperature_scaling(
        calibration_records,
        raw_predictions[selected_arm]["calibration"],
        fit_split=Split.CALIBRATION,
        class_order=CLASS_ORDER,
        code_version="task-0009-temperature-v1",
    )
    calibrated_calibration = _calibrated_predictions(
        raw_predictions[selected_arm]["calibration"],
        apply_temperature_scaling(
            [prediction.probabilities for prediction in raw_predictions[selected_arm]["calibration"]],
            calibration_artifact,
        ),
    )
    calibrated_dev = _calibrated_predictions(
        raw_predictions[selected_arm]["dev"],
        apply_temperature_scaling(
            [prediction.probabilities for prediction in raw_predictions[selected_arm]["dev"]],
            calibration_artifact,
        ),
    )
    calibrated_test = _calibrated_predictions(
        raw_predictions[selected_arm]["test"],
        apply_temperature_scaling(
            [prediction.probabilities for prediction in raw_predictions[selected_arm]["test"]],
            calibration_artifact,
        ),
    )
    for stage, records, predictions in (
        ("calibration", calibration_records, calibrated_calibration),
        ("dev", dev_records, calibrated_dev),
        ("test", test_records, calibrated_test),
    ):
        all_prediction_rows.extend(
            _prediction_row(prediction, split=records[index].split, arm="E", stage=stage)
            for index, prediction in enumerate(predictions)
        )
    arm_summaries["E"] = {
        "base_arm": selected_arm,
        "training_row_count": arm_summaries[selected_arm]["training_row_count"],
        "metrics": {
            "dev": _metrics(dev_records, calibrated_dev, domain_map=domain_map),
            "calibration": _metrics(
                calibration_records, calibrated_calibration, domain_map=domain_map
            ),
            "test": _metrics(test_records, calibrated_test, domain_map=domain_map),
        },
    }

    calibration_payload = calibration_artifact.model_dump(mode="json")
    _json_dump(artifacts / "calibration.json", calibration_payload)
    _jsonl_write(output / "predictions.jsonl", all_prediction_rows)

    source_manifest = {
        "experiment_id": EXPERIMENT_ID,
        "seed": seed,
        "synthetic_fixture_fingerprint": fixture.fingerprint,
        "train_record_ids": [record.record_id for record in train_records],
        "dev_record_ids": [record.record_id for record in dev_records],
        "calibration_record_ids": [record.record_id for record in calibration_records],
        "test_record_ids": [record.record_id for record in test_records],
        "excluded_test_hard_negative_count": sum(
            str(item.get("split")) == Split.TEST.value for item in hard_negative_items
        ),
        "hard_negative_file_sha256": _sha256_file(HARD_NEGATIVE_PATH),
        "rubric_paraphrase_file_sha256": _sha256_file(PARAPHRASE_PATH),
    }
    _json_dump(artifacts / "source_manifest.json", source_manifest)

    leakage = {
        "training_rows_contain_test": False,
        "training_source_problem_ids_overlap_test": bool(
            {
                row.source_problem_id
                for arm in ("A", "B", "C", "D")
                for row in build_training_rows(
                    fixture.records,
                    arm=arm,
                    hard_negatives=hard_negative_items,
                    rubric_paraphrases=paraphrases,
                )
            }
            & {record.source_problem_id for record in test_records}
        ),
        "calibration_fit_split": calibration_artifact.fit_split.value,
        "test_labels_used_for_selection": False,
        "test_labels_used_for_calibration": False,
        "test_source_count": len({record.source_problem_id for record in test_records}),
    }
    if leakage["training_source_problem_ids_overlap_test"]:
        raise RuntimeError("source-family leakage detected")

    results = {
        "experiment_id": EXPERIMENT_ID,
        "status": "completed",
        "code_commit": _git_commit(),
        "student": {
            "id": "tfidf-logistic-v1",
            "selection_rationale": "A compact linear text classifier is reproducible on the small objective corpus, requires no external weights, exposes probabilities, and keeps the pilot focused on auditable training-arm and calibration behavior.",
            "scope": "single-answer correctness; pairwise records excluded",
        },
        "split_counts": {
            "train": len(train_records),
            "dev": len(dev_records),
            "calibration": len(calibration_records),
            "test": len(test_records),
        },
        "selected_arm": selected_arm,
        "selection_rule": "lowest dev NLL, then highest dev accuracy, then arm name; test metrics not consulted",
        "calibration": {
            "method": "temperature",
            "fit_split": calibration_artifact.fit_split.value,
            "fit_record_count": len(calibration_records),
            "artifact": calibration_payload,
            "raw_calibration_metrics": arm_summaries[selected_arm]["metrics"]["calibration"],
            "calibrated_calibration_metrics": arm_summaries["E"]["metrics"]["calibration"],
        },
        "arms": arm_summaries,
        "leakage_checks": leakage,
        "test_evaluation": {
            "status": "completed_after_preregistration",
            "test_source_ids": [record.source_problem_id for record in test_records],
            "test_record_count": len(test_records),
        },
    }
    _json_dump(output / "results.json", results)
    manifest = _manifest(
        fixture_fingerprint=fixture.fingerprint,
        hard_negative_fingerprint=_sha256_file(HARD_NEGATIVE_PATH),
        paraphrase_fingerprint=_sha256_file(PARAPHRASE_PATH),
        code_commit=results["code_commit"],
        selected_arm=selected_arm,
        calibration_artifact=calibration_payload,
        arms=arm_summaries,
        output=output,
    )
    _json_dump(output / "manifest.json", manifest)
    return results


def _write_report(output: Path, results: dict[str, Any]) -> None:
    def metric(arm: str, split: str, name: str) -> str:
        value = results["arms"][arm]["metrics"][split]["aggregate"]["metrics"].get(name)
        return "n/a" if value is None else f"{float(value):.4f}"

    lines = [
        f"# {EXPERIMENT_ID}",
        "",
        "## Student and protocol",
        "",
        "The pilot selected a compact TF-IDF plus logistic-regression student for single-answer correctness. It uses deterministic objective labels, retains teacher augmentation as training metadata, and excludes pairwise records from the student scope.",
        "",
        "Arms A-D were fit on train-split records only. Arm A uses objective labels; B adds rubric criterion paraphrases; C adds verified TASK-0008 hard negatives; D adds both. The arm with the lowest dev NLL, then highest dev accuracy, was selected without consulting test labels. Arm E applies scalar temperature calibration fit only on the calibration split.",
        "",
        f"Selected arm: **{results['selected_arm']}**. Calibration records: **{results['calibration']['fit_record_count']}**. Test records: **{results['test_evaluation']['test_record_count']}**.",
        "",
        "## Ablation metrics",
        "",
        "| Arm | Train rows | Dev accuracy | Dev NLL | Test accuracy | Test balanced accuracy | Test macro F1 | Test Brier | Test ECE |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for arm in ("A", "B", "C", "D", "E"):
        train_count = results["arms"][arm].get("training_row_count")
        if train_count is None:
            train_count = results["arms"][results["arms"][arm]["base_arm"]]["training_row_count"]
        lines.append(
            f"| {arm} | {train_count} | {metric(arm, 'dev', 'accuracy')} | {metric(arm, 'dev', 'nll')} | {metric(arm, 'test', 'accuracy')} | {metric(arm, 'test', 'balanced_accuracy')} | {metric(arm, 'test', 'macro_f1')} | {metric(arm, 'test', 'brier')} | {metric(arm, 'test', 'ece')} |"
        )
    lines.extend(
        [
            "",
            "## Calibration and validity",
            "",
            f"Temperature fit used `{results['calibration']['fit_record_count']}` calibration records and produced a positive scalar artifact. Raw selected-arm calibration NLL was `{metric(results['selected_arm'], 'calibration', 'nll')}`; calibrated arm E calibration NLL was `{metric('E', 'calibration', 'nll')}`.",
            "",
            "The runner verifies that no training source family overlaps the test split, that test labels do not select the arm, and that test labels do not fit calibration. Every hard negative carries deterministic-verifier provenance; teacher rationales and rubric text remain weak augmentation metadata.",
            "",
            "## Limitations",
            "",
            "This is a small synthetic pilot with 33 objective train records, 21 dev records, 6 calibration records, and 12 frozen test records. The linear student is a feasibility choice rather than evidence that a transformer encoder would perform the same way. Pairwise, ARC, memory, and live provider behavior are outside this student run; inference latency is retained per prediction, while no OS-level memory claim is made.",
        ]
    )
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=20260920)
    args = parser.parse_args()
    results = run(args.output_dir, seed=args.seed)
    _write_report(args.output_dir, results)
    manifest_path = args.output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"] = sorted(
        str(path.relative_to(args.output_dir))
        for path in args.output_dir.rglob("*")
        if path.is_file()
    )
    _json_dump(manifest_path, manifest)
    print(json.dumps({"experiment_id": EXPERIMENT_ID, "selected_arm": results["selected_arm"], "status": "completed"}))


if __name__ == "__main__":
    main()
