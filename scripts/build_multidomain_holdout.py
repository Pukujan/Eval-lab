"""Build and freeze the TASK-0011 multidomain public/holdout pool."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval_lab.datasets.arc import ArcSourceMetadata, canonicalize_arc_row
from eval_lab.datasets.multidomain import (
    canonicalize_choice_row,
    canonicalize_gsm8k_row,
    stable_rank,
)
from eval_lab.datasets.synthetic import generate_synthetic_fixtures
from eval_lab.schema import JudgeRecord, Split

EXPERIMENT_ID = "EXP-20260921-013-qwen-multidomain-holdout"
SEED = 20260921
ARC_REVISION = "210d026faf9955653af8916fad021475a3f00453"
GSM8K_REVISION = "740312add88f781978c0658806c59bc2815b9866"
MMLU_REVISION = "c30699e8356da336a370243923dbaf21066bb9fe"
MMLU_SUBJECTS = (
    "abstract_algebra",
    "elementary_mathematics",
    "high_school_biology",
    "high_school_world_history",
    "logical_fallacies",
    "machine_learning",
    "professional_law",
    "computer_security",
)


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def _ranked(rows: list[dict[str, Any]], *, family: str, limit: int) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: stable_rank(SEED, family, str(row["source_problem_id"])),
    )[:limit]


def _existing_records(benchmark: Path, *, public_limit: int, holdout_limit: int) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in (benchmark / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    threshold = [
        {"source_problem_id": row["record"]["source_problem_id"], "record": row["record"]}
        for row in rows
        if row["partition"] == "threshold_selection"
    ]
    final = [
        {"source_problem_id": row["record"]["source_problem_id"], "record": row["record"]}
        for row in rows
        if row["partition"] == "final_evaluation"
    ]
    output: list[dict[str, Any]] = []
    for partition, candidates, limit, split in (
        ("public_selection", threshold, public_limit, Split.CALIBRATION),
        ("blind_holdout", final, holdout_limit, Split.TEST),
    ):
        for row in _ranked(candidates, family="eval-lab-select-v0.1.0", limit=limit):
            record = JudgeRecord.model_validate(row["record"]).model_copy(update={"split": split})
            output.append(
                {
                    "dataset": "eval-lab-select-v0.1.0",
                    "partition": partition,
                    "source_problem_id": record.source_problem_id,
                    "source_revision": "18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5",
                    "record": record.model_dump(mode="json"),
                }
            )
    return output


def _load_dataset(path: str, config: str, split: str, revision: str) -> list[dict[str, Any]]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("the datasets package is required to build the multidomain pool") from exc
    return list(load_dataset(path, config, split=split, revision=revision))


def _arc_easy(*, public_limit: int, holdout_limit: int) -> list[dict[str, Any]]:
    metadata = ArcSourceMetadata(
        dataset_id="allenai/ai2_arc",
        config="ARC-Easy",
        license="CC BY-SA 4.0",
        requested_revision="main",
        resolved_revision=ARC_REVISION,
        canonicalization_version="arc-easy-canonical-v1",
        split_policy={"train": "public_selection", "validation": "public_selection", "test": "blind_holdout"},
        split_seed=SEED,
        validation_dev_fraction=0.5,
    )
    output: list[dict[str, Any]] = []
    for upstream_split, partition, limit, split in (
        ("train", "public_selection", public_limit, Split.CALIBRATION),
        ("validation", "public_selection", public_limit, Split.CALIBRATION),
        ("test", "blind_holdout", holdout_limit, Split.TEST),
    ):
        rows = _load_dataset("allenai/ai2_arc", "ARC-Easy", upstream_split, ARC_REVISION)
        selected = _ranked(
            [{"source_problem_id": str(row["id"]), "row": row} for row in rows],
            family=f"arc-easy:{upstream_split}",
            limit=limit,
        )
        for item in selected:
            _, record = canonicalize_arc_row(item["row"], upstream_split=upstream_split, metadata=metadata)
            record = record.model_copy(
                update={
                    "split": split,
                    "perturbation": {**record.perturbation, "experiment_partition": partition},
                }
            )
            output.append(
                {
                    "dataset": "allenai/ai2_arc:ARC-Easy",
                    "partition": partition,
                    "source_problem_id": record.source_problem_id,
                    "source_revision": ARC_REVISION,
                    "record": record.model_dump(mode="json"),
                }
            )
    return output


def _gsm8k(*, public_limit: int, holdout_limit: int) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for upstream_split, partition, limit, split in (
        ("train", "public_selection", public_limit, Split.CALIBRATION),
        ("test", "blind_holdout", holdout_limit, Split.TEST),
    ):
        rows = _load_dataset("openai/gsm8k", "main", upstream_split, GSM8K_REVISION)
        selected = _ranked(
            [
                {"source_problem_id": f"{upstream_split}-{index:05d}", "row": row}
                for index, row in enumerate(rows)
            ],
            family=f"gsm8k:{upstream_split}",
            limit=limit,
        )
        for item in selected:
            source_id = f"gsm8k-main:{item['source_problem_id']}"
            records = canonicalize_gsm8k_row(
                source_problem_id=source_id,
                question=str(item["row"]["question"]),
                answer=str(item["row"]["answer"]),
                split=split,
            )
            for record in records:
                record = record.model_copy(
                    update={"perturbation": {**record.perturbation, "experiment_partition": partition}}
                )
                output.append(
                    {
                        "dataset": "openai/gsm8k:main",
                        "partition": partition,
                        "source_problem_id": record.source_problem_id,
                        "source_revision": GSM8K_REVISION,
                        "record": record.model_dump(mode="json"),
                    }
                )
    return output


def _mmlu(*, per_subject_public: int, per_subject_holdout: int) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for subject in MMLU_SUBJECTS:
        for upstream_split, partition, limit, split in (
            ("validation", "public_selection", per_subject_public, Split.CALIBRATION),
            ("test", "blind_holdout", per_subject_holdout, Split.TEST),
        ):
            rows = _load_dataset("cais/mmlu", subject, upstream_split, MMLU_REVISION)
            selected = _ranked(
                [
                    {"source_problem_id": f"{subject}:{upstream_split}:{index:04d}", "row": row}
                    for index, row in enumerate(rows)
                ],
                family=f"mmlu:{subject}:{upstream_split}",
                limit=limit,
            )
            for item in selected:
                raw = item["row"]
                answer = int(raw["answer"])
                records = canonicalize_choice_row(
                    dataset="mmlu",
                    source_problem_id=item["source_problem_id"],
                    question=f"Subject: {subject}\n{raw['question']}",
                    choices=[str(choice) for choice in raw["choices"]],
                    answer_index=answer,
                    split=split,
                    evidence={
                        "source_dataset": "cais/mmlu",
                        "subject": subject,
                        "upstream_split": upstream_split,
                        "answer_index": answer,
                    },
                )
                for record in records:
                    record = record.model_copy(
                        update={"perturbation": {**record.perturbation, "experiment_partition": partition}}
                    )
                    output.append(
                        {
                            "dataset": f"cais/mmlu:{subject}",
                            "partition": partition,
                            "source_problem_id": record.source_problem_id,
                            "source_revision": MMLU_REVISION,
                            "record": record.model_dump(mode="json"),
                        }
                    )
    return output


def _synthetic(*, public_limit: int, holdout_limit: int) -> list[dict[str, Any]]:
    fixture = generate_synthetic_fixtures()
    groups: dict[str, list[JudgeRecord]] = defaultdict(list)
    for record in fixture.records:
        groups[record.source_problem_id.split("-")[1]].append(record)
    output: list[dict[str, Any]] = []
    for family, records in sorted(groups.items()):
        for partition, source_split, limit in (
            ("public_selection", {Split.TRAIN, Split.DEV, Split.CALIBRATION}, public_limit),
            ("blind_holdout", {Split.TEST}, holdout_limit),
        ):
            candidates = [record for record in records if record.split in source_split]
            for record in _ranked(
                [{"source_problem_id": record.record_id, "record": record} for record in candidates],
                family=f"synthetic:{family}:{partition}",
                limit=limit,
            ):
                canonical = record["record"].model_copy(
                    update={"split": Split.CALIBRATION if partition == "public_selection" else Split.TEST}
                )
                output.append(
                    {
                        "dataset": f"eval-lab-synthetic:{family}",
                        "partition": partition,
                        "source_problem_id": canonical.source_problem_id,
                        "source_revision": f"synthetic-seed-{fixture.seed}-split-{fixture.split_seed}",
                        "record": canonical.model_dump(mode="json"),
                    }
                )
    return output


def _checksums(root: Path) -> None:
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "checksums.sha256":
            continue
        entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
    (root / "checksums.sha256").write_bytes(("\n".join(entries) + "\n").encode("utf-8"))


def build(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output)
    if output.exists():
        existing = {path.name for path in output.iterdir()}
        allowed = {"PLAN.md", "README.md", "experiment.yaml"} | {
            name for name in existing if name.startswith("smoke-qwen-")
        }
        unexpected = existing - allowed
        if unexpected:
            raise FileExistsError(f"refusing to overwrite existing artifacts: {sorted(unexpected)}")
    output.mkdir(parents=True, exist_ok=True)
    rows = _existing_records(Path(args.benchmark), public_limit=args.existing_public, holdout_limit=args.existing_holdout)
    rows.extend(_arc_easy(public_limit=args.dataset_public, holdout_limit=args.dataset_holdout))
    rows.extend(_gsm8k(public_limit=args.dataset_public, holdout_limit=args.dataset_holdout))
    rows.extend(_mmlu(per_subject_public=args.mmlu_public, per_subject_holdout=args.mmlu_holdout))
    rows.extend(_synthetic(public_limit=args.synthetic_public, holdout_limit=args.synthetic_holdout))
    record_ids = [row["record"]["record_id"] for row in rows]
    source_ids_by_partition: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        source_ids_by_partition[row["partition"]].add(row["source_problem_id"])
    overlap = source_ids_by_partition["public_selection"] & source_ids_by_partition["blind_holdout"]
    if overlap:
        raise ValueError(f"source families cross the public/holdout boundary: {sorted(overlap)[:5]}")
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("canonical record IDs are duplicated")
    records_path = output / "records.jsonl"
    records_path.write_bytes(
        b"".join((json.dumps(row, sort_keys=True) + "\n").encode("utf-8") for row in rows)
    )
    counts = Counter(row["partition"] for row in rows)
    dataset_counts = Counter((row["partition"], row["dataset"]) for row in rows)
    source_manifest = {
        "experiment_id": EXPERIMENT_ID,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "code_commit": args.code_commit,
        "seed": SEED,
        "datasets": {
            "eval-lab-select-v0.1.0": {"revision_or_fingerprint": "18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5", "license": "CC BY-SA 4.0 / repository release"},
            "allenai/ai2_arc:ARC-Easy": {"revision": ARC_REVISION, "license": "CC BY-SA 4.0"},
            "openai/gsm8k:main": {"revision": GSM8K_REVISION, "license": "MIT"},
            "cais/mmlu": {"revision": MMLU_REVISION, "license": "MIT", "subjects": list(MMLU_SUBJECTS)},
            "eval-lab-synthetic": {"revision": "deterministic fixture seed 20260920"},
        },
        "counts": dict(sorted(counts.items())),
        "dataset_counts": {f"{partition}|{dataset}": count for (partition, dataset), count in sorted(dataset_counts.items())},
        "source_problem_ids": sorted({row["source_problem_id"] for row in rows}),
        "record_ids": record_ids,
    }
    source_manifest["records_fingerprint"] = hashlib.sha256(records_path.read_bytes()).hexdigest()
    _write_json(output / "source-manifest.json", source_manifest)
    _write_json(
        output / "splits.json",
        {
            "seed": SEED,
            "partitions": {partition: sorted(ids) for partition, ids in sorted(source_ids_by_partition.items())},
            "source_family_overlap": sorted(overlap),
            "record_counts": dict(sorted(counts.items())),
        },
    )
    holdout_ids = [row["record"]["record_id"] for row in rows if row["partition"] == "blind_holdout"]
    _write_json(
        output / "holdout-manifest.json",
        {
            "experiment_id": EXPERIMENT_ID,
            "status": "frozen_before_holdout_evaluation",
            "gold_used_for_selection": False,
            "record_ids": holdout_ids,
            "record_count": len(holdout_ids),
            "record_ids_fingerprint": hashlib.sha256("\n".join(holdout_ids).encode()).hexdigest(),
        },
    )
    _checksums(output)
    return {"experiment_id": EXPERIMENT_ID, "counts": dict(sorted(counts.items())), "fingerprint": source_manifest["records_fingerprint"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=Path("benchmark/eval-lab-select-v0.1.0"))
    parser.add_argument("--output", type=Path, default=Path("experiments/EXP-20260921-013-qwen-multidomain-holdout"))
    parser.add_argument("--code-commit", default="working-tree")
    parser.add_argument("--existing-public", type=int, default=120)
    parser.add_argument("--existing-holdout", type=int, default=120)
    parser.add_argument("--dataset-public", type=int, default=80)
    parser.add_argument("--dataset-holdout", type=int, default=100)
    parser.add_argument("--mmlu-public", type=int, default=10)
    parser.add_argument("--mmlu-holdout", type=int, default=20)
    parser.add_argument("--synthetic-public", type=int, default=12)
    parser.add_argument("--synthetic-holdout", type=int, default=12)
    args = parser.parse_args()
    print(json.dumps(build(args), sort_keys=True))


if __name__ == "__main__":
    main()
