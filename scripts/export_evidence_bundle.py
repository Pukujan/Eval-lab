"""Export a raw-evidence bundle for an external verifier.

    python scripts/export_evidence_bundle.py --source artifacts --destination bundle
    python scripts/export_evidence_bundle.py --verify bundle

The first form collects the raw evidence a verification run produced, hashes every
file, and writes ``evidence-index.json``. The second recomputes every hash in an
already-exported bundle — the check the receiving side runs before trusting it.

This tool reaches no verdict. It reports what it copied and what it could not find;
whether that adds up to a demonstrated criterion is the verifier's call, and
deliberately not ours. See docs/verification-baseline.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from app.evidence.bundle import (  # noqa: E402
    BundleIntegrityError,
    export_bundle,
    load_baseline,
    verify_bundle,
)

DEFAULT_BASELINE = REPOSITORY_ROOT / "verification" / "task-2a-baseline.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", default="artifacts", help="artifact directory a verification run produced"
    )
    parser.add_argument(
        "--destination", default="evidence-bundle", help="where to write the bundle"
    )
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    parser.add_argument(
        "--commit",
        default=None,
        help="repository commit; falls back to the completion manifest, never invented",
    )
    parser.add_argument("--github-run-id", default=None)
    parser.add_argument(
        "--verify",
        metavar="BUNDLE",
        default=None,
        help="recompute every checksum in an exported bundle and exit",
    )
    args = parser.parse_args()

    try:
        if args.verify:
            checked = verify_bundle(Path(args.verify))
            print(f"bundle checksums recomputed: {len(checked)} files match the index")
            print("no criterion was evaluated; this checks integrity only")
            return 0

        index = export_bundle(
            Path(args.source),
            Path(args.destination),
            baseline=load_baseline(Path(args.baseline)),
            baseline_path=Path(args.baseline),
            commit_sha=args.commit,
            github_run_id=args.github_run_id,
        )
    except BundleIntegrityError as exc:
        print(f"evidence export FAILED: {exc}", file=sys.stderr)
        return 1

    counts = index["counts"]
    provenance = index["provenance"]
    print(f"evidence bundle written to {args.destination}")
    print(f"  files exported          : {counts['entries']}")
    print(f"  workflow executions     : {counts['workflow_executions']}")
    print(f"  optional evidence absent: {counts['missing_optional_evidence']}")
    print(f"  reports missing linkage : {counts['missing_execution_linkage']}")
    print(
        f"  repository commit       : {provenance['repository_commit']} "
        f"(from {provenance['repository_commit_source']})"
    )
    for execution in index["workflow_executions"]:
        print(f"  execution {execution['workflow_id']} run {execution['run_id']}")
    for absent in index["missing_optional_evidence"]:
        print(f"  ABSENT (optional): {absent['logical_name']} <- {absent['expected_source']}")
    for gap in index["missing_execution_linkage"]:
        print(f"  NO LINKAGE: {gap['bundle_path']} — {gap['reason']}")
    print("\nno criterion was evaluated here; the bundle carries evidence, not a verdict")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
