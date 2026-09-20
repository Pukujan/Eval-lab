"""Build the pinned EvalLab-Select v0.1.0 release from public sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from eval_lab.datasets.arc import (
    ARC_CONFIG,
    ARC_DATASET_ID,
    ARC_LICENSE,
    ArcSourceMetadata,
    load_arc_rows,
)
from eval_lab.datasets.selective import (
    SELECTIVE_CANONICALIZATION_VERSION,
    arc_single_records,
    combine_selective_records,
    partition_records,
)
from eval_lab.datasets.synthetic import generate_synthetic_fixtures
from eval_lab.schema import Split

REVISION = "210d026faf9955653af8916fad021475a3f00453"
SEED = 20260920
OUTPUT = Path("benchmark/eval-lab-select-v0.1.0")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build(output: Path = OUTPUT) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    metadata = ArcSourceMetadata(
        dataset_id=ARC_DATASET_ID,
        config=ARC_CONFIG,
        license=ARC_LICENSE,
        requested_revision=REVISION,
        resolved_revision=REVISION,
        canonicalization_version="arc-challenge-canonical-v1",
        split_policy={"train": "threshold_selection", "validation": "threshold_selection", "test": "final_evaluation"},
        split_seed=SEED,
        validation_dev_fraction=0.5,
    )
    loaded = {name: load_arc_rows(name, metadata=metadata) for name in ("train", "validation", "test")}
    arc_sources: list[Any] = []
    arc_records: list[Any] = []
    for split_name in ("train", "validation", "test"):
        sources, records = arc_single_records(
            [dict(row) for row in loaded[split_name]],
            upstream_split=split_name,
            metadata=metadata,
        )
        arc_sources.extend(sources)
        arc_records.extend(records)

    synthetic = generate_synthetic_fixtures(seed=SEED, split_seed=SEED)
    synthetic.sources = [source for source in synthetic.sources if source.split is not Split.TRAIN]
    allowed_source_ids = {source.source_problem_id for source in synthetic.sources}
    synthetic.records = [
        record for record in synthetic.records if record.source_problem_id in allowed_source_ids
    ]
    sources, records = combine_selective_records(
        arc_sources=arc_sources,
        arc_records=arc_records,
        synthetic=synthetic,
    )
    partitions = partition_records(records)
    source_by_id = {source.source_problem_id: source for source in sources}
    record_rows = []
    for record in sorted(records, key=lambda item: item.record_id):
        source = source_by_id[record.source_problem_id]
        partition = "final_evaluation" if record.split is Split.TEST else "threshold_selection"
        record_rows.append(
            {
                "record": record.model_dump(mode="json"),
                "domain": source.domain,
                "partition": partition,
                "source_dataset": source.source_dataset,
            }
        )
    records_path = output / "records.jsonl"
    records_path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in record_rows),
        encoding="utf-8",
    )
    split_payload = {
        "threshold_selection": {
            "record_ids": sorted(record.record_id for record in partitions["threshold_selection"]),
            "source_problem_ids": sorted({record.source_problem_id for record in partitions["threshold_selection"]}),
            "record_count": len(partitions["threshold_selection"]),
            "source_count": len({record.source_problem_id for record in partitions["threshold_selection"]}),
        },
        "final_evaluation": {
            "record_ids": sorted(record.record_id for record in partitions["final_evaluation"]),
            "source_problem_ids": sorted({record.source_problem_id for record in partitions["final_evaluation"]}),
            "record_count": len(partitions["final_evaluation"]),
            "source_count": len({record.source_problem_id for record in partitions["final_evaluation"]}),
        },
    }
    source_manifest = {
        "benchmark": "EvalLab-Select",
        "version": "0.1.0",
        "seed": SEED,
        "arc": {
            "dataset_id": ARC_DATASET_ID,
            "config": ARC_CONFIG,
            "license": ARC_LICENSE,
            "requested_revision": REVISION,
            "resolved_revision": REVISION,
            "canonicalization_version": "arc-challenge-canonical-v1",
            "row_counts": {name: len(loaded[name]) for name in loaded},
        },
        "synthetic": {
            "fixture_fingerprint": generate_synthetic_fixtures(seed=SEED, split_seed=SEED).fingerprint,
            "excluded_training_source_count": 12,
            "canonicalization_version": "synthetic-objective-v1",
        },
        "canonicalization_version": SELECTIVE_CANONICALIZATION_VERSION,
        "source_count": len(sources),
        "record_count": len(records),
        "sources": [source.model_dump(mode="json") for source in sorted(sources, key=lambda item: item.source_problem_id)],
    }
    _write_json(output / "splits.json", split_payload)
    _write_json(output / "source-manifest.json", source_manifest)
    fingerprint_payload = {
        "records": record_rows,
        "splits": split_payload,
        "source_manifest": source_manifest,
        "canonicalization_version": SELECTIVE_CANONICALIZATION_VERSION,
    }
    benchmark_fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    _write_json(output / "fingerprint.json", {"benchmark": "EvalLab-Select", "version": "0.1.0", "fingerprint": benchmark_fingerprint})
    manifest = {
        "name": "EvalLab-Select",
        "version": "0.1.0",
        "status": "frozen",
        "purpose": "calibrated selective escalation and typed judge differential evaluation",
        "sources": ["synthetic-objective-v1", f"{ARC_DATASET_ID}:{ARC_CONFIG}"],
        "canonicalization_version": SELECTIVE_CANONICALIZATION_VERSION,
        "fingerprint": benchmark_fingerprint,
        "splits": {
            name: {"record_count": value["record_count"], "source_count": value["source_count"]}
            for name, value in split_payload.items()
        },
        "split_manifest": "splits.json",
        "source_revisions": {"arc": REVISION},
        "seed": SEED,
        "build_code_commit": _git_head(),
        "research_metadata": {"ro_crate": "1.3", "provenance": "PROV-O", "validation": "SHACL-2017"},
    }
    (output / "benchmark.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    checksums = []
    for path in sorted(output.iterdir()):
        if path.is_file() and path.name != "checksums.sha256":
            checksums.append(f"{_sha256(path)}  {path.name}")
    (output / "checksums.sha256").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = build(args.output)
    print(json.dumps({"fingerprint": result["fingerprint"], "splits": result["splits"]}, sort_keys=True))


if __name__ == "__main__":
    main()
