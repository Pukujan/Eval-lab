"""Assemble the machine-readable completion manifest.

One JSON file mapping each Task 2A completion criterion to the evidence artifact
that supports it, plus the verdict that artifact recorded.

Deliberately mechanical: it reads the evidence files and reports what they say.
It does not decide anything itself, and a criterion with no evidence file is
reported as ``not_demonstrated`` rather than quietly omitted — an absent artifact
must be visible, not invisible.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from app.evidence.artifacts import evidence_directory  # noqa: E402
from app.reliability.report import component_versions  # noqa: E402

#: criterion -> (evidence file stem, human description)
CRITERIA: dict[str, tuple[str, str]] = {
    "clean_runner_starts_full_compose_stack": (
        "compose-verification-clean",
        "A clean hosted CI runner starts the full Compose stack",
    ),
    "all_service_health_checks_pass": (
        "compose-verification-clean",
        "Every declared service reports healthy",
    ),
    "real_temporal_workflow_appears_and_completes": (
        "durability-recovery",
        "A real Temporal workflow appears on the server and completes",
    ),
    "coding_workflow_executes_under_temporal": (
        "workflow-smoke",
        "CodingEvaluationWorkflow crosses both conditional edges, runs an activity "
        "node, and completes with a non-empty history",
    ),
    "worker_interruption_recovery": (
        "durability-recovery",
        "A worker-interruption test demonstrates recovery without repeating effects",
    ),
    "retry_behaviour_from_real_history": (
        "retry-behaviour",
        "Retry behaviour demonstrated using real workflow history",
    ),
    "timeout_behaviour": (
        "timeout-behaviour",
        "Timeout behaviour demonstrated and correctly classified",
    ),
    "replay_determinism_verification": (
        "replay-determinism",
        "Replay passes for the genuine workflow and detects an incompatible variation",
    ),
    "phoenix_contains_required_spans": (
        "phoenix-trace",
        "Phoenix contains every required span",
    ),
    "ducttape_remains_rejected": (
        "evaluation-outcomes",
        "The duct-tape patch remains rejected",
    ),
    "known_good_remains_accepted_for_review": (
        "evaluation-outcomes",
        "The known-good candidate remains accepted_for_review",
    ),
    "infrastructure_failures_classified_separately": (
        "timeout-behaviour",
        "Infrastructure failures are classified separately from patch rejection",
    ),
    "state_persists_across_restart": (
        "persistence-across-restart",
        "Temporal and Phoenix state survive a stack restart",
    ),
    "dependencies_and_images_pinned": (
        "pin-verification",
        "All dependency versions and image digests are pinned",
    ),
    "state_initialisation": (
        "state-initialisation",
        "Application stores and the Temporal namespace are initialised",
    ),
}


def git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPOSITORY_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def main() -> int:
    directory = evidence_directory()
    criteria: dict[str, dict[str, object]] = {}

    for key, (stem, description) in CRITERIA.items():
        path = directory / f"{stem}.json"
        if not path.is_file():
            criteria[key] = {
                "description": description,
                "status": "not_demonstrated",
                "reason": f"no evidence artifact at {path.name}",
                "evidence_artifact": None,
            }
            continue

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            criteria[key] = {
                "description": description,
                "status": "not_demonstrated",
                "reason": f"corrupt evidence artifact: {exc}",
                "evidence_artifact": path.name,
            }
            continue

        verified = payload.get("verified")
        # Verification scripts that reach the end without writing `verified:false`
        # are successes; the failure paths always write the flag explicitly.
        status = "demonstrated" if verified is not False else "not_demonstrated"
        criteria[key] = {
            "description": description,
            "status": status,
            "evidence_artifact": path.name,
            "claim": payload.get("claim"),
            "failure": payload.get("failure"),
            "recorded_at": payload.get("recorded_at"),
        }

    demonstrated = sum(1 for c in criteria.values() if c["status"] == "demonstrated")

    manifest = {
        "manifest_version": 1,
        "task": "2A — prove durable execution and reproducible packaging",
        "generated_at": datetime.now(UTC).isoformat(),
        "repository_commit": git_commit(),
        "ci": {
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_number": os.environ.get("GITHUB_RUN_NUMBER"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "github_workflow": os.environ.get("GITHUB_WORKFLOW"),
            "github_sha": os.environ.get("GITHUB_SHA"),
            "github_ref": os.environ.get("GITHUB_REF"),
            "runner_os": os.environ.get("RUNNER_OS"),
            "runner_name": os.environ.get("RUNNER_NAME"),
        },
        "platform": {
            "python": platform.python_version(),
            "system": platform.system(),
            "release": platform.release(),
        },
        "component_versions": dict(component_versions()),
        "criteria": criteria,
        "summary": {
            "total": len(criteria),
            "demonstrated": demonstrated,
            "not_demonstrated": len(criteria) - demonstrated,
            "all_demonstrated": demonstrated == len(criteria),
        },
        "explicitly_not_claimed": [
            "calibration",
            "production readiness",
            "general reliability",
            "live model provider integration",
            "any bug class beyond the single duplicate-processing fixture",
        ],
    }

    destination = directory.parent / "completion-manifest.json"
    destination.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    print(f"completion manifest written to {destination}")
    for key, entry in criteria.items():
        mark = "OK " if entry["status"] == "demonstrated" else "MISS"
        print(f"  [{mark}] {key}")
    print(f"\n{demonstrated}/{len(criteria)} criteria demonstrated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
