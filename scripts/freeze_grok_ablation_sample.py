"""Freeze the deterministic public sample used by EXP-025 protocol selection."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def freeze_sample(*, pool: Path, output: Path, single_count: int, pairwise_count: int) -> dict[str, object]:
    rows = [json.loads(line) for line in (pool / "records.jsonl").read_text(encoding="utf-8").splitlines() if line]
    public = [row for row in rows if row["partition"] == "public_selection"]
    selected: list[dict[str, object]] = []
    for mode, count in (("single", single_count), ("pairwise", pairwise_count)):
        candidates = [row for row in public if row["record"]["mode"] == mode]
        if len(candidates) < count:
            raise ValueError(f"public pool has only {len(candidates)} {mode} rows; need {count}")
        selected.extend(candidates[:count])

    record_ids = [row["record"]["record_id"] for row in selected]
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("diagnostic sample contains duplicate record IDs")
    output.mkdir(parents=True, exist_ok=True)
    (output / "diagnostic-record-ids.txt").write_text("\n".join(record_ids) + "\n", encoding="utf-8")
    pool_manifest = json.loads((pool / "pool-manifest.json").read_text(encoding="utf-8"))
    manifest = {
        "experiment_id": "EXP-20260922-025-grok-protocol-ablation",
        "source_experiment": pool_manifest["experiment_id"],
        "records_fingerprint": pool_manifest["records_fingerprint"],
        "blind_record_ids_fingerprint": pool_manifest["blind_record_ids_fingerprint"],
        "selection": "first rows in canonical records.jsonl order within public_selection, by mode",
        "counts": {"single": single_count, "pairwise": pairwise_count, "total": len(record_ids)},
        "record_ids_sha256": hashlib.sha256("\n".join(record_ids).encode("utf-8")).hexdigest(),
        "record_ids": record_ids,
    }
    (output / "diagnostic-selection.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--single-count", type=int, default=32)
    parser.add_argument("--pairwise-count", type=int, default=32)
    args = parser.parse_args()
    if args.single_count <= 0 or args.pairwise_count <= 0:
        raise SystemExit("sample counts must be positive")
    print(json.dumps(freeze_sample(pool=args.pool, output=args.output, single_count=args.single_count, pairwise_count=args.pairwise_count), sort_keys=True))


if __name__ == "__main__":
    main()
