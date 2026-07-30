"""Confirm the two evaluation outcomes are unchanged under durable execution.

Task 2A must not move the correctness goalposts to make infrastructure tests pass.
So this re-asserts exactly what Task 1 asserted — duct tape rejected on the effect
counter, known-good accepted for review and nothing stronger — and additionally
requires that both ran with ``execution_mode=temporal``.

Reads the reliability reports produced by ``scripts/demo.py``.

Usage:  python scripts/verify_outcomes.py [--reports DIR] [--require-durable]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from app.evidence.artifacts import EvidenceError, require, write_evidence  # noqa: E402

EXPECTED = {
    "C-claim": "accepted_for_review",
    "C-dedupe-read": "rejected",
}
FORBIDDEN_OUTCOMES = {"approved", "correct", "safe", "production_ready"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", default="evals/reports")
    parser.add_argument("--require-durable", action="store_true", default=True)
    parser.add_argument("--allow-non-durable", dest="require_durable", action="store_false")
    args = parser.parse_args()

    reports_dir = Path(args.reports)
    findings: dict[str, object] = {"reports_directory": str(reports_dir)}

    try:
        summaries = {}
        for candidate_id, expected_outcome in EXPECTED.items():
            path = reports_dir / f"reliability-report-{candidate_id}.json"
            require(path.is_file(), f"missing reliability report: {path}")

            try:
                report = json.loads(path.read_text(encoding="utf-8"))
            except ValueError as exc:
                raise EvidenceError(f"corrupt evaluation artifact {path}: {exc}") from exc

            decision = report["decision"]
            run = report["run"]
            verification = report.get("verification") or {}

            require(
                decision["outcome"] == expected_outcome,
                f"{candidate_id}: expected {expected_outcome}, got {decision['outcome']}",
            )
            require(
                decision["outcome"] not in FORBIDDEN_OUTCOMES,
                f"{candidate_id}: forbidden outcome vocabulary {decision['outcome']}",
            )
            require(
                report["merged_or_deployed"] is False,
                f"{candidate_id}: report claims something was merged or deployed",
            )

            if args.require_durable:
                require(
                    run["execution_mode"] == "temporal",
                    f"{candidate_id}: execution_mode was {run['execution_mode']}, "
                    "expected 'temporal' — the point of this task is durable execution",
                )
                require(
                    decision["durable_execution"] is True,
                    f"{candidate_id}: durable_execution flag is false",
                )

            summaries[candidate_id] = {
                "outcome": decision["outcome"],
                "execution_mode": run["execution_mode"],
                "durable_execution": decision["durable_execution"],
                "workflow_id": run.get("workflow_id"),
                "trace_id": run.get("trace_id"),
                "failed_gates": [
                    g["gate_name"] for g in decision["gate_results"] if not g["passed"]
                ],
                "effect_invocation_count": verification.get("effect_invocation_count"),
                "hidden_tests_passed": verification.get("hidden_tests_passed"),
            }

        # The specific evidence that the duct-tape rejection is still the *right*
        # rejection, not an accidental one from some unrelated failure.
        ducttape = summaries["C-dedupe-read"]
        require(
            "not_symptom_suppression" in ducttape["failed_gates"],
            "the duct-tape patch was rejected, but not by the symptom-suppression gate; "
            f"failed gates were {ducttape['failed_gates']}",
        )
        require(
            ducttape["effect_invocation_count"] == 2,
            f"duct-tape effect counter was {ducttape['effect_invocation_count']}, expected 2",
        )

        known_good = summaries["C-claim"]
        require(
            not known_good["failed_gates"],
            f"known-good patch failed gates: {known_good['failed_gates']}",
        )
        require(
            known_good["effect_invocation_count"] == 1,
            f"known-good effect counter was {known_good['effect_invocation_count']}, expected 1",
        )

        findings.update({"outcomes": summaries, "verified": True})
        evidence_path = write_evidence("evaluation-outcomes", findings)

        print("evaluation outcomes VERIFIED (unchanged under durable execution)")
        for candidate_id, summary in summaries.items():
            print(
                f"  {candidate_id:<15} {summary['outcome']:<20} "
                f"mode={summary['execution_mode']} effects={summary['effect_invocation_count']}"
            )
        print(f"  evidence: {evidence_path}")
        return 0

    except EvidenceError as exc:
        findings.update({"verified": False, "failure": str(exc)})
        write_evidence("evaluation-outcomes", findings)
        print(f"evaluation outcomes NOT VERIFIED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
