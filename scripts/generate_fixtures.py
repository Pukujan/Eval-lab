"""Generate the deterministic synthetic fixture artifact without network access."""

from __future__ import annotations

import argparse
from pathlib import Path

from eval_lab.datasets.synthetic import (
    DEFAULT_SPLIT_SEED,
    generate_synthetic_fixtures,
    serialize_fixture,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SPLIT_SEED)
    parser.add_argument("--split-seed", type=int, default=DEFAULT_SPLIT_SEED)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/synthetic-fixtures.json"),
        help="output path for the stable JSON fixture artifact",
    )
    args = parser.parse_args()

    fixture = generate_synthetic_fixtures(seed=args.seed, split_seed=args.split_seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialize_fixture(fixture), encoding="utf-8")
    print(
        f"generated {len(fixture.sources)} sources and {len(fixture.records)} records "
        f"(single={len(fixture.single_records)}, pairwise={len(fixture.pairwise_records)})"
    )
    print(f"fingerprint={fixture.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
