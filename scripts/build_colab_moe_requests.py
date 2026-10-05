"""Build label-only typed-choice requests from the frozen EXP-015 pool.

Writes one JSON object per record containing only the information the judge is
allowed to see (record_id, mode, state, question, options, labels).  No gold
label is included, so the file is safe to upload to a shared compute host.

Usage:
    .venv\\Scripts\\python.exe scripts\\build_colab_moe_requests.py \\
        blind_holdout experiments/EXP-20261005-031-colab-t4-moe-judge-arms/requests/blind.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eval_lab.judges.local_decision_models import request_for_record

RECORDS = ROOT / "experiments" / "EXP-20260921-015-grok-luna-qwen-bakeoff" / "records.jsonl"
BENCHMARK = "exp027-frozen-pool"


def build(partition: str, limit: int = 0) -> list[dict]:
    rows = [
        json.loads(line)
        for line in RECORDS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected: list[dict] = []
    for row in rows:
        if row.get("partition") != partition:
            continue
        record = row["record"]
        request = request_for_record(record, BENCHMARK)
        request["mode"] = record["mode"]
        selected.append(request)
        if limit and len(selected) >= limit:
            break
    if not selected:
        raise ValueError(f"no records matched partition {partition!r}")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("partition", choices=("public_selection", "blind_holdout"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    selected = build(args.partition, args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in selected),
        encoding="utf-8",
        newline="\n",
    )
    modes: dict[str, int] = {}
    for r in selected:
        modes[r["mode"]] = modes.get(r["mode"], 0) + 1
    print(f"{args.partition}: {len(selected)} requests {modes} -> {args.output}")


if __name__ == "__main__":
    main()
