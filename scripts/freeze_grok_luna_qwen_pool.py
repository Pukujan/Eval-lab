"""Copy the completed EXP-014 pool into the new comparison experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EXPERIMENT_ID = "EXP-20260921-015-grok-luna-qwen-bakeoff"
SOURCE_EXPERIMENT = "EXP-20260921-014-independent-jev-benchmark"
SOURCE_FILES = (
    "records.jsonl",
    "source-manifest.json",
    "splits.json",
    "holdout-manifest.json",
    "typed-question-spec.json",
    "perturbations.json",
)
EXPECTED_RECORD_FINGERPRINT = "b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8"
EXPECTED_TYPED_FINGERPRINT = "0d07bd8b8b60bd7f0b5b7a5f5819b7d329ea121f686b240e465695b6f6eca1e4"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _freeze(source: Path, output: Path) -> dict[str, Any]:
    if not source.is_dir():
        raise FileNotFoundError(f"source experiment does not exist: {source}")
    output.mkdir(parents=True, exist_ok=True)
    allowed = {"README.md", "PLAN.md", "experiment.yaml"}
    unexpected = {
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_file() and path.name not in allowed
    }
    if unexpected:
        raise FileExistsError(f"refusing to overwrite frozen output files: {sorted(unexpected)}")

    for name in SOURCE_FILES:
        source_path = source / name
        if not source_path.is_file():
            raise FileNotFoundError(f"missing source freeze file: {source_path}")
        shutil.copyfile(source_path, output / name)

    source_manifest = _json(output / "source-manifest.json")
    if source_manifest.get("records_fingerprint") != EXPECTED_RECORD_FINGERPRINT:
        raise ValueError("source record fingerprint does not match EXP-014")
    typed_spec = _json(output / "typed-question-spec.json")
    if _json_fingerprint(typed_spec) != EXPECTED_TYPED_FINGERPRINT:
        raise ValueError("typed question specification does not match EXP-014")
    rows = [
        json.loads(line)
        for line in (output / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    record_ids = [row["record"]["record_id"] for row in rows]
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("frozen pool contains duplicate record IDs")
    if any("jevbench" in json.dumps(row, sort_keys=True).lower() for row in rows):
        raise ValueError("JevBench content detected in primary comparison pool")
    partitions = Counter(row["partition"] for row in rows)
    if dict(partitions) != {"blind_holdout": 760, "public_selection": 648}:
        raise ValueError(f"unexpected partition counts: {dict(partitions)}")

    holdout_manifest = _json(output / "holdout-manifest.json")
    pool_manifest = {
        "experiment_id": EXPERIMENT_ID,
        "source_experiment": SOURCE_EXPERIMENT,
        "frozen_at_utc": datetime.now(UTC).isoformat(),
        "source_files": list(SOURCE_FILES),
        "record_count": len(rows),
        "partition_counts": dict(sorted(partitions.items())),
        "source_problem_id_count": len({row["record"]["source_problem_id"] for row in rows}),
        "records_fingerprint": source_manifest["records_fingerprint"],
        "blind_record_ids_fingerprint": holdout_manifest["record_ids_fingerprint"],
        "typed_question_spec_fingerprint": EXPECTED_TYPED_FINGERPRINT,
        "typed_spec_id": typed_spec["spec_id"],
        "typed_spec_version": typed_spec["spec_version"],
        "primary_partition": "blind_holdout",
        "provider_model_arms": [
            {"arm": "grok", "provider": "opencode", "requested_model": "opencode/grok-build-0.1"},
            {"arm": "luna", "provider": "opencode", "requested_model": "opencode/gpt-5.6-luna"},
            {"arm": "qwen_flash", "provider": "yolo-auto", "requested_model": "qwen3.8-flash"},
            {"arm": "sol", "provider": "opencode", "requested_model": "opencode/gpt-5.6-sol", "optional": True},
        ],
        "gold_provenance": sorted({row["record"]["gold"]["provenance"] for row in rows}),
        "status": "frozen_before_live_final_evaluation",
    }
    (output / "pool-manifest.json").write_text(
        json.dumps(pool_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    checksums = []
    for path in sorted(output.iterdir()):
        if path.is_file() and path.name != "pool-checksums.sha256":
            checksums.append(f"{_sha256(path)}  {path.name}")
    (output / "pool-checksums.sha256").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    return pool_manifest | {"pool_checksum_count": len(checksums)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("experiments") / SOURCE_EXPERIMENT,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("experiments") / EXPERIMENT_ID,
    )
    args = parser.parse_args()
    print(json.dumps(_freeze(args.source, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
