"""Run the normalized Jev baseline over the deterministic synthetic fixture suite."""

from __future__ import annotations

import argparse
from pathlib import Path

from eval_lab.datasets.synthetic import generate_synthetic_fixtures
from eval_lab.jev import ATOMIC_PROTOCOL, DIRECT_PROTOCOL, run_jev_sync, write_predictions_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", choices=(DIRECT_PROTOCOL, ATOMIC_PROTOCOL), default=DIRECT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=Path("outputs/jev-predictions.jsonl"))
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    fixture = generate_synthetic_fixtures()
    records = fixture.records if args.limit is None else fixture.records[: args.limit]
    predictions = run_jev_sync(records, protocol_version=args.protocol)
    write_predictions_jsonl(predictions, args.output)
    counts: dict[str, int] = {}
    for prediction in predictions:
        status = prediction.execution_status.value
        counts[status] = counts.get(status, 0) + 1
    print(f"protocol={args.protocol} records={len(predictions)} statuses={counts}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
