"""Build the EXP-033 LegalBench answer-key subset and its frozen source manifest.

The subset extends the legal objective axis beyond Hearsay with three pinned
answer-key subtasks: ``overruling``, ``definition_classification``, and
``citation_prediction_classification``. ``--freeze`` downloads each task's
``train.tsv``, ``test.tsv``, and ``base_prompt.txt`` from the pinned LegalBench
revision, verifies them by SHA-256 and byte count, copies them into the
committed ``source/`` tree, and writes ``source-manifest.json``. The default
build re-verifies every committed file against the manifest, assigns each case
to a split by its normalized text, and emits the canonical dataset, the pool
rows the shared runner consumes, the split manifest, and the typed-question
spec. Nothing here calls a model; scoring is a separate, later step.

Raw downloads live outside the dev root under the ACS scratch area
(``%LOCALAPPDATA%\\acs\\scratch\\legalbench-subset`` on Windows,
``~/.cache/acs/scratch/legalbench-subset`` elsewhere); ``LEGALBENCH_CACHE_DIR``
or ``--cache-dir`` overrides it.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from eval_lab.datasets.legalbench import (
    SUBTASK_NAMES,
    SUBTASK_SPECS,
    assign_case_splits,
    canonicalize_subtask_rows,
    label_distribution,
    majority_baseline,
)
from eval_lab.schema import JudgeRecord, Split

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "experiments" / "EXP-20261006-033-legalbench-answer-key-subset"
MANIFEST_PATH = EXPERIMENT_DIR / "source-manifest.json"
SOURCE_DIR = EXPERIMENT_DIR / "source"
EXPERIMENT_ID = "EXP-20261006-033-legalbench-answer-key-subset"
DATASET_REVISION = "daec8237410aa23e3faf4bc41ad8b3a7e1696826"
TASK_DOCS_REVISION = "b46bf4ffae90524b2b72aaa30e7745fe9db64481"
SEED = 261006
CONTEXT_LIMIT = 4096
PRIMARY_PARTITION = "blind_holdout"
PARTITION_FOR_SPLIT = {Split.CALIBRATION: "public_selection", Split.TEST: "blind_holdout"}
USER_AGENT = "eval-lab-legalbench-subset/1.0 (+https://github.com/Pukujan/Eval-lab)"
_CHUNK = 1 << 20

TASK_LICENSE = {
    "overruling": ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
    "definition_classification": (
        "CC BY-SA 4.0",
        "https://creativecommons.org/licenses/by-sa/4.0/",
    ),
    "citation_prediction_classification": (
        "CC BY 4.0",
        "https://creativecommons.org/licenses/by/4.0/",
    ),
}
PUBLISHED_TEST_SIZE = {
    "overruling": 2400,
    "definition_classification": 1346,
    "citation_prediction_classification": 110,
}


def default_cache_dir() -> Path:
    override = os.environ.get("LEGALBENCH_CACHE_DIR")
    if override:
        return Path(override)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "acs" / "scratch" / "legalbench-subset"
    return Path.home() / ".cache" / "acs" / "scratch" / "legalbench-subset"


def sha256_and_size(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(_CHUNK):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _data_url(task: str, name: str) -> str:
    return (
        "https://huggingface.co/datasets/nguha/legalbench/resolve/"
        f"{DATASET_REVISION}/data/{task}/{name}"
    )


def _prompt_url(task: str) -> str:
    return (
        "https://raw.githubusercontent.com/HazyResearch/legalbench/"
        f"{TASK_DOCS_REVISION}/tasks/{task}/base_prompt.txt"
    )


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request) as response, partial.open("wb") as sink:
        while chunk := response.read(_CHUNK):
            sink.write(chunk)
    partial.replace(destination)


def _row_count(path: Path, *, expected_columns: frozenset[str]) -> int:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames is None or set(reader.fieldnames) != set(expected_columns):
            raise ValueError(f"unexpected {path.name} columns: {reader.fieldnames}")
        return sum(1 for _ in reader)


def _read_rows(path: Path, *, expected_columns: frozenset[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames is None or set(reader.fieldnames) != set(expected_columns):
            raise ValueError(f"unexpected {path.name} columns: {reader.fieldnames}")
        return list(reader)


def _task_files(task: str) -> list[dict[str, str]]:
    return [
        {"name": "train.tsv", "url": _data_url(task, "train.tsv")},
        {"name": "test.tsv", "url": _data_url(task, "test.tsv")},
        {"name": "base_prompt.txt", "url": _prompt_url(task)},
    ]


def freeze(cache_dir: Path) -> dict[str, Any]:
    manifest_files: list[dict[str, Any]] = []
    task_entries: dict[str, Any] = {}
    for task in SUBTASK_NAMES:
        spec = SUBTASK_SPECS[task]
        committed = SOURCE_DIR / task
        committed.mkdir(parents=True, exist_ok=True)
        per_task: dict[str, Any] = {}
        for item in _task_files(task):
            name = item["name"]
            cache_path = cache_dir / task / name
            if not cache_path.is_file():
                download(item["url"], cache_path)
            digest, size = sha256_and_size(cache_path)
            target = committed / name
            target.write_bytes(cache_path.read_bytes())
            entry: dict[str, Any] = {
                "task": task,
                "path": f"data/{task}/{name}" if name.endswith(".tsv") else f"tasks/{task}/{name}",
                "url": item["url"],
                "bytes": size,
                "sha256": digest,
                "repository_path": target.relative_to(ROOT).as_posix(),
            }
            if name.endswith(".tsv"):
                entry["rows_excluding_header"] = _row_count(target, expected_columns=spec.columns)
            per_task[name] = entry
            manifest_files.append(entry)
        train_rows = per_task["train.tsv"]["rows_excluding_header"]
        test_rows = per_task["test.tsv"]["rows_excluding_header"]
        license_name, license_url = TASK_LICENSE[task]
        published = PUBLISHED_TEST_SIZE[task]
        discrepancy = None
        if published != test_rows:
            discrepancy = (
                f"task page reports {published} test examples; the pinned machine-readable "
                f"source contains {test_rows}; preserve the source as distributed and do not "
                "fabricate a missing item."
            )
        task_entries[task] = {
            "license": license_name,
            "license_url": license_url,
            "verifier_id": spec.verifier_id,
            "prompt_version": spec.prompt_version,
            "columns": sorted(spec.columns),
            "observed_source_train_rows": train_rows,
            "observed_source_test_rows": test_rows,
            "published_test_size": published,
            "test_row_discrepancy": discrepancy,
        }
    manifest = {
        "dataset": "LegalBench answer-key subset",
        "dataset_repository": "https://huggingface.co/datasets/nguha/legalbench",
        "dataset_revision": DATASET_REVISION,
        "task_documentation_repository": "https://github.com/HazyResearch/legalbench",
        "task_documentation_revision": TASK_DOCS_REVISION,
        "retrieved_date": "2026-10-06",
        "attribution": "Neel Guha; LegalBench task authors as identified by the project",
        "tasks": task_entries,
        "files": manifest_files,
        "canonical_records_sha256": None,
        "notes": (
            "Each task's rows are the pinned LegalBench machine-readable source. "
            "Per-task licenses differ: overruling and citation_prediction_classification "
            "are CC BY 4.0; definition_classification is CC BY-SA 4.0 (see "
            "source/LICENSE-NOTICE.txt). Published task-page sizes may "
            "exceed the pinned row counts; each task records its own observed-vs-published "
            "row counts and discrepancy note, and no record is fabricated."
        ),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def _verify_committed(manifest: dict[str, Any]) -> None:
    for entry in manifest["files"]:
        path = ROOT / entry["repository_path"]
        if not path.is_file():
            raise FileNotFoundError(f"committed source file missing: {path}")
        digest, size = sha256_and_size(path)
        if digest != entry["sha256"] or size != entry["bytes"]:
            raise ValueError(f"{path.name} does not match the pinned source manifest")


def _fingerprint_records(records: list[JudgeRecord]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(record.model_dump_json().encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _json_fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def build() -> dict[str, Any]:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"run --freeze first; no manifest at {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    _verify_committed(manifest)

    records: list[JudgeRecord] = []
    per_task_report: dict[str, Any] = {}
    for task in SUBTASK_NAMES:
        spec = SUBTASK_SPECS[task]
        test_path = SOURCE_DIR / task / "test.tsv"
        prompt = (SOURCE_DIR / task / "base_prompt.txt").read_text(encoding="utf-8")
        rows = _read_rows(test_path, expected_columns=spec.columns)
        expected = manifest["tasks"][task]["observed_source_test_rows"]
        if len(rows) != expected:
            raise ValueError(f"{task} test row count {len(rows)} != manifest {expected}")

        by_split: dict[Split, list[dict[str, str]]] = {Split.CALIBRATION: [], Split.TEST: []}
        for row, split in assign_case_splits(rows, task=task, seed=SEED):
            by_split[split].append(dict(row))
        task_records: list[JudgeRecord] = []
        for split, split_rows in by_split.items():
            task_records.extend(
                canonicalize_subtask_rows(
                    split_rows, task=task, split=split, prompt_template=prompt
                )
            )
        records.extend(task_records)

        case_to_split: dict[str, Split] = {}
        for record in task_records:
            prior = case_to_split.setdefault(record.source_problem_id, record.split)
            if prior is not record.split:
                raise ValueError(f"{task}: case {record.source_problem_id} crosses splits")
        per_task_report[task] = {
            "test_rows": len(rows),
            "distinct_cases": len(case_to_split),
            "record_counts": dict(
                sorted(Counter(record.split.value for record in task_records).items())
            ),
            "gold_label_distribution": label_distribution(
                [record.gold.label for record in task_records]
            ),
            "majority_baseline": majority_baseline([record.gold.label for record in task_records]),
        }

    records.sort(key=lambda record: record.record_id)
    record_ids = [record.record_id for record in records]
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("duplicate record IDs in the canonical dataset")

    (EXPERIMENT_DIR / "canonical-records.jsonl").write_text(
        "".join(record.model_dump_json() + "\n" for record in records),
        encoding="utf-8",
        newline="\n",
    )

    split_counts = Counter(record.split for record in records)
    cases_by_split: dict[str, set[str]] = {"calibration": set(), "test": set()}
    for record in records:
        cases_by_split[record.split.value].add(record.source_problem_id)
    overlap = cases_by_split["calibration"] & cases_by_split["test"]
    if overlap:
        raise ValueError(f"case split is not disjoint: {sorted(overlap)[:5]}")

    split_manifest = {
        "experiment_id": EXPERIMENT_ID,
        "seed": SEED,
        "split_policy": (
            "case-disjoint calibration/test on the SHA-256 of the normalized text; "
            "all rows sharing a text share a split"
        ),
        "case_normalization": "text collapsed on Unicode whitespace: ' '.join(text.split())",
        "record_counts": {split.value: split_counts[split] for split in Split},
        "case_counts": {name: len(members) for name, members in cases_by_split.items()},
        "per_task": per_task_report,
        "record_ids_fingerprint": _json_fingerprint(record_ids),
    }
    (EXPERIMENT_DIR / "split-manifest.json").write_text(
        json.dumps(split_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    rows_out = [
        {
            "dataset": "legalbench-subset",
            "partition": PARTITION_FOR_SPLIT[record.split],
            "record": record.model_dump(mode="json"),
            "source_problem_id": record.source_problem_id,
            "source_revision": DATASET_REVISION,
        }
        for record in records
    ]
    (EXPERIMENT_DIR / "records.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows_out),
        encoding="utf-8",
        newline="\n",
    )

    typed_spec = {
        "confidence_definition": "native normalized provider probabilities only; label-only responses have no confidence metric",
        "context_limit": CONTEXT_LIMIT,
        "question_type": "choice",
        "single_legal_labels": ["Yes", "No"],
        "per_task": {
            task: {
                "legal_labels": ["Yes", "No"],
                "verifier_id": SUBTASK_SPECS[task].verifier_id,
                "prompt_version": SUBTASK_SPECS[task].prompt_version,
            }
            for task in SUBTASK_NAMES
        },
        "spec_id": "legalbench-answer-key-subset-v1",
        "spec_version": "legalbench-answer-key-subset-v1",
        "target_error_rates": [0.01, 0.02, 0.05],
    }
    (EXPERIMENT_DIR / "typed-question-spec.json").write_text(
        json.dumps(typed_spec, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    blind_ids = sorted(record.record_id for record in records if record.split is Split.TEST)
    pool_manifest = {
        "experiment_id": EXPERIMENT_ID,
        "source_experiment": EXPERIMENT_ID,
        "source_files": [entry["repository_path"] for entry in manifest["files"]],
        "dataset_revision": DATASET_REVISION,
        "record_count": len(records),
        "partition_counts": dict(sorted(Counter(row["partition"] for row in rows_out).items())),
        "source_problem_id_count": len({record.source_problem_id for record in records}),
        "records_fingerprint": _fingerprint_records(records),
        "blind_record_ids_fingerprint": _json_fingerprint(blind_ids),
        "typed_question_spec_fingerprint": _json_fingerprint(typed_spec),
        "typed_spec_id": typed_spec["spec_id"],
        "typed_spec_version": typed_spec["spec_version"],
        "primary_partition": PRIMARY_PARTITION,
        "gold_provenance": sorted({record.gold.provenance.value for record in records}),
        "status": "frozen_before_blind_evaluation",
    }
    (EXPERIMENT_DIR / "pool-manifest.json").write_text(
        json.dumps(pool_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    checksums = []
    for name in sorted(
        (
            "canonical-records.jsonl",
            "records.jsonl",
            "split-manifest.json",
            "typed-question-spec.json",
            "pool-manifest.json",
        )
    ):
        path = EXPERIMENT_DIR / name
        checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {name}")
    (EXPERIMENT_DIR / "pool-checksums.sha256").write_text(
        "\n".join(checksums) + "\n", encoding="utf-8", newline="\n"
    )

    canonical_sha = hashlib.sha256(
        (EXPERIMENT_DIR / "canonical-records.jsonl").read_bytes()
    ).hexdigest()
    manifest["canonical_records_sha256"] = canonical_sha
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")

    return pool_manifest | {
        "canonical_records_sha256": canonical_sha,
        "per_task": per_task_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=default_cache_dir())
    parser.add_argument(
        "--freeze", action="store_true", help="download and record the pinned source files"
    )
    args = parser.parse_args()
    try:
        if args.freeze:
            manifest = freeze(args.cache_dir)
            print(f"froze {len(manifest['files'])} files -> {MANIFEST_PATH.relative_to(ROOT)}")
            return 0
        summary = build()
    except (OSError, ValueError) as exc:
        print(f"LegalBench subset stopped: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
