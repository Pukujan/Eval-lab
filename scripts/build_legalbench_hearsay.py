"""Build deterministic canonical records from the pinned Hearsay task files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from eval_lab.datasets.legalbench import canonicalize_hearsay_rows
from eval_lab.schema import Split

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "EXP-20260924-028-legalbench-hearsay"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames is None or set(reader.fieldnames) != {
            "index",
            "answer",
            "text",
            "slice",
        }:
            raise ValueError(f"unexpected Hearsay TSV columns in {path}")
        return list(reader)


def build(source_dir: Path, output: Path) -> dict[str, object]:
    manifest_path = EXPERIMENT / "source-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    file_entries = {Path(item["path"]).name: item for item in manifest["files"]}
    test_path = source_dir / "test.tsv"
    prompt_path = source_dir / "base_prompt.txt"
    for name in ("train.tsv", "test.tsv", "base_prompt.txt"):
        entry = file_entries.get(name)
        path = source_dir / name
        if entry is None or sha256(path) != entry["sha256"]:
            raise ValueError(f"{name} does not match the pinned LegalBench source manifest")

    train_rows = read_tsv(source_dir / "train.tsv")
    rows = read_tsv(test_path)
    if len(train_rows) != manifest["observed_source_train_rows"]:
        raise ValueError("train row count differs from the frozen source manifest")
    if len(rows) != manifest["observed_source_test_rows"]:
        raise ValueError("test row count differs from the frozen source manifest")
    template = prompt_path.read_text(encoding="utf-8")
    records = canonicalize_hearsay_rows(rows, split=Split.TEST, prompt_template=template)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n"
        for record in records
    )
    output.write_text(payload, encoding="utf-8", newline="\n")
    output_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return {"record_count": len(records), "sha256": output_hash, "output": str(output)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=EXPERIMENT / "source")
    parser.add_argument("--output", type=Path, default=EXPERIMENT / "canonical-records.jsonl")
    args = parser.parse_args()
    result = build(args.source_dir, args.output)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
