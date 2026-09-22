"""Freeze the exact rate-limited Qwen IDs from a completed prior run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=317)
    args = parser.parse_args()

    ids: list[str] = []
    for line in args.source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        prediction = json.loads(line)
        if prediction.get("execution_status") == "rate_limited":
            ids.append(str(prediction["record_id"]))

    if len(ids) != args.expected_count:
        raise SystemExit(f"expected {args.expected_count} rate-limited IDs, found {len(ids)}")
    if len(set(ids)) != len(ids):
        raise SystemExit("rate-limited ID list contains duplicates")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(ids) + "\n", encoding="utf-8")
    print(json.dumps({"count": len(ids), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
