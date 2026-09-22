"""Freeze the independent objective pool and typed protocol for TASK-0012."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval_lab.escalation.spec import build_decision_spec
from eval_lab.schema import JudgeRecord, JudgmentMode

EXPERIMENT_ID = "EXP-20260921-014-independent-jev-benchmark"
SOURCE_EXPERIMENT = "EXP-20260921-013-qwen-multidomain-holdout"
SEED = 20260921
SOURCE_FILES = ("records.jsonl", "source-manifest.json", "splits.json", "holdout-manifest.json")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _rank(seed: int, purpose: str, record_id: str) -> str:
    return hashlib.sha256(f"{seed}:{purpose}:{record_id}".encode()).hexdigest()


def _load_rows(source: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (source / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _freeze(source: Path, output: Path) -> dict[str, Any]:
    allowed_planning_files = {"README.md", "PLAN.md", "experiment.yaml"}
    existing = {
        path.name
        for path in output.rglob("*")
        if path.is_file()
    } if output.exists() else set()
    if existing - allowed_planning_files:
        raise FileExistsError(f"refusing to overwrite frozen output files: {sorted(existing - allowed_planning_files)}")
    output.mkdir(parents=True, exist_ok=True)
    for name in SOURCE_FILES:
        shutil.copyfile(source / name, output / name)

    rows = _load_rows(output)
    records = [JudgeRecord.model_validate(row["record"]) for row in rows]
    by_id = {record.record_id: record for record in records}
    if len(by_id) != len(records):
        raise ValueError("independent pool contains duplicate record IDs")
    if any("jevbench" in json.dumps(row, sort_keys=True).lower() for row in rows):
        raise ValueError("JevBench text or labels detected in primary pool")
    if any(record.gold.provenance.value not in {"answer_key", "deterministic_verifier"} for record in records):
        raise ValueError("primary pool contains non-objective gold provenance")

    source_manifest = json.loads((output / "source-manifest.json").read_text(encoding="utf-8"))
    source_manifest.update(
        {
            "experiment_id": EXPERIMENT_ID,
            "source_experiment": SOURCE_EXPERIMENT,
            "benchmark_role": "independent_primary_objective_pool",
            "jevbench_items_labels_and_results_excluded": True,
            "canonicalization_version": "source-manifest revisions and EvalLab canonical records as frozen in TASK-0011",
        }
    )
    _write_json(output / "source-manifest.json", source_manifest)
    for name in ("splits.json", "holdout-manifest.json"):
        payload = json.loads((output / name).read_text(encoding="utf-8"))
        payload["experiment_id"] = EXPERIMENT_ID
        payload["source_experiment"] = SOURCE_EXPERIMENT
        _write_json(output / name, payload)

    partitions: dict[str, list[str]] = {}
    for row in rows:
        partitions.setdefault(row["partition"], []).append(row["record"]["record_id"])
    blind_records = [by_id[record_id] for record_id in partitions["blind_holdout"]]
    repeat_ids = sorted(
        (record.record_id for record in blind_records),
        key=lambda record_id: _rank(SEED, "repeat", record_id),
    )[:12]
    option_ids = sorted(
        (record.record_id for record in blind_records if by_id[record.record_id].mode is JudgmentMode.SINGLE),
        key=lambda record_id: _rank(SEED, "option-order", record_id),
    )[:12]
    paraphrase_ids = sorted(
        (record.record_id for record in blind_records),
        key=lambda record_id: _rank(SEED, "paraphrase", record_id),
    )[:12]
    typed_packet = {
        "spec_id": "eval-lab-system-one",
        "spec_version": "0.1.0",
        "context_limit": 4096,
        "single_legal_labels": ["pass", "fail"],
        "pairwise_legal_labels": ["A", "B", "TIE"],
        "question_type": "choice",
        "confidence_definition": "native normalized provider probabilities only; label-only responses have no confidence metric",
        "target_error_rates": [0.01, 0.02, 0.05],
    }
    packet_fingerprint = _sha256_bytes(json.dumps(typed_packet, sort_keys=True).encode())
    example_specs = [
        build_decision_spec(by_id[record_id]).provider_payload()
        for record_id in sorted(by_id)[:3]
    ]
    perturbations = {
        "seed": SEED,
        "repeat_record_ids": repeat_ids,
        "option_order_record_ids": option_ids,
        "rubric_paraphrase_record_ids": paraphrase_ids,
        "repeat_count": 3,
        "option_order": {record_id: ["fail", "pass"] for record_id in option_ids},
        "rubric_paraphrase": "Decide whether the candidate is objectively correct for the stated task. Return exactly one legal label.",
        "example_typed_payloads": example_specs,
    }
    _write_json(output / "typed-question-spec.json", typed_packet)
    _write_json(output / "perturbations.json", perturbations)
    freeze = {
        "experiment_id": EXPERIMENT_ID,
        "frozen_at_utc": datetime.now(UTC).isoformat(),
        "source_experiment": SOURCE_EXPERIMENT,
        "source_files": list(SOURCE_FILES),
        "record_count": len(records),
        "partition_counts": dict(sorted(Counter(row["partition"] for row in rows).items())),
        "source_problem_id_count": len({record.source_problem_id for record in records}),
        "records_fingerprint": source_manifest["records_fingerprint"],
        "blind_record_ids_fingerprint": json.loads((output / "holdout-manifest.json").read_text(encoding="utf-8"))["record_ids_fingerprint"],
        "typed_question_spec_fingerprint": packet_fingerprint,
        "canonicalization_version": source_manifest["canonicalization_version"],
        "confidence_definition": typed_packet["confidence_definition"],
        "target_error_rates": typed_packet["target_error_rates"],
        "provider_model_arms": [
            {"arm": "jev_pinned", "provider": "openrouter", "model": "typesafe/jev-1.13"},
            {"arm": "jev_rolling_canary", "provider": "openrouter", "model": "~typesafe/jev-latest"},
            {"arm": "qwen_comparison", "provider": "yolo-auto", "model": "qwen3.8-flash"},
            {"arm": "local_comparison", "provider": "local", "model": "tfidf-logistic-v1", "task": "TASK-0009 arm D"},
            {"arm": "majority_baseline", "provider": "local", "model": "frozen-majority-label"},
        ],
        "gold_provenance": sorted({record.gold.provenance.value for record in records}),
        "primary_score_exclusions": ["JevBench task text", "JevBench labels", "JevBench composite score"],
        "perturbation_fingerprint": _sha256_bytes(json.dumps(perturbations, sort_keys=True).encode()),
        "status": "frozen_before_live_final_evaluation",
    }
    _write_json(output / "freeze.json", freeze)
    checksums: dict[str, str] = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "checksums.sha256":
            checksums[str(path.relative_to(output)).replace("\\", "/")] = _sha256_bytes(path.read_bytes())
    (output / "checksums.sha256").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in checksums.items()), encoding="utf-8"
    )
    return freeze | {"checksum_count": len(checksums)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("experiments") / SOURCE_EXPERIMENT)
    parser.add_argument("--output", type=Path, default=Path("experiments") / EXPERIMENT_ID)
    args = parser.parse_args()
    print(json.dumps(_freeze(args.source, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
