"""The complete walking-skeleton scenario (`make demo`).

Runs both candidates against the fixture and prints the two outcomes side by side:

* the repair that establishes the invariant  -> accepted_for_review
* the duct-tape patch that hides the symptom -> rejected

Needs no credentials. If the local services are up it uses them; if not it runs
the degraded local path and says so loudly rather than quietly producing a
weaker result that looks identical.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.runner import RunRequest, run_evaluation  # noqa: E402

SCENARIOS = (
    ("C-claim", "known-good repair (atomic claim before irreversible work)", "accepted_for_review"),
    ("C-dedupe-read", "duct-tape patch (de-duplicate results on read)", "rejected"),
)


async def main() -> int:
    output_dir = Path("evals/reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []

    for candidate_id, description, expected in SCENARIOS:
        print("=" * 78)
        print(f"CANDIDATE {candidate_id} — {description}")
        print(f"expected outcome: {expected}")
        print("=" * 78)

        report = await run_evaluation(RunRequest(candidate_id=candidate_id))
        for line in report.summary_lines():
            print(f"  {line}")

        destination = output_dir / f"reliability-report-{candidate_id}.json"
        destination.write_text(report.to_json(), encoding="utf-8")
        print(f"  report written  : {destination}")
        if report.run.trace_id:
            print(f"  trace id        : {report.run.trace_id}")
        print()

        if report.decision.outcome != expected:
            failures.append(f"{candidate_id}: expected {expected}, got {report.decision.outcome}")

    print("=" * 78)
    if failures:
        print("DEMO FAILED")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("DEMO OK — the incorrect patch was rejected and the correct patch was")
    print("accepted for review only. Nothing was merged or deployed, and no claim")
    print("of calibration, correctness, or production-readiness is made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
