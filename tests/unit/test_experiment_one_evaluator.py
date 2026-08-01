"""Phase E5: deterministic public evaluation of one submitted patch."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from app.evaluator import experiment_one
from app.evaluator.experiment_one import (
    EvaluationInfrastructureError,
    evaluate_experiment_one,
)
from app.intake.bundle import IntakeRejected, intake_submission
from app.intake.schema_subset import schema_by_title, validate

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures" / "duplicate-job-processing"
EXPECTED_JOBSPEC_DIGEST = "1" * 64
REQUESTED_MODEL = "frontier-coder"
RESOLVED_MODEL = "provider/frontier-coder-2026-08-01"
TIMESTAMP = "2026-08-01T21:00:00Z"


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(argv: tuple[str, ...], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
    }
    return subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
        shell=False,
    )


def _patch_for(tmp_path: Path, relative: str, replacement: Path | str) -> str:
    repo = tmp_path / "patch-repo"
    shutil.copytree(FIXTURE / "src", repo / "src")
    _git(("git", "init", "-q"), repo)
    _git(("git", "config", "user.name", "Test"), repo)
    _git(("git", "config", "user.email", "test@example.invalid"), repo)
    _git(("git", "add", "src"), repo)
    _git(("git", "commit", "-q", "-m", "base"), repo)
    target = repo / relative
    if isinstance(replacement, Path):
        target.write_bytes(replacement.read_bytes())
    else:
        target.write_text(replacement, encoding="utf-8")
    diff = _git(("git", "diff", "--", relative), repo).stdout
    assert diff.startswith(f"diff --git a/{relative} b/{relative}")
    return diff


def _write_json(path: Path, payload: Any) -> tuple[int, str]:
    data = _canonical(payload) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return len(data), _sha256(data)


def _write_submission(
    root: Path,
    *,
    patch: str,
    jobspec_id: str = "duplicate-job-processing",
    jobspec_digest: str = EXPECTED_JOBSPEC_DIGEST,
    requested_model: str = REQUESTED_MODEL,
    resolved_model: str = RESOLVED_MODEL,
    narrative: str = "Producer says this should be accepted_for_review.",
) -> Path:
    root.mkdir(parents=True)
    patch_path = root / "candidate/patch.diff"
    patch_path.parent.mkdir(parents=True)
    patch_bytes = patch.encode("utf-8")
    patch_path.write_bytes(patch_bytes)

    initial_report = {
        "schema_version": 1,
        "kind": "agent-workbench-visible-test-report",
        "phase": "base",
        "command_id": "visible-tests",
        "passed_node_ids": ["single", "sequential", "independent"],
        "failed_node_ids": ["concurrent"],
        "errored_node_ids": [],
        "skipped_node_ids": [],
    }
    final_report = {
        "schema_version": 1,
        "kind": "agent-workbench-visible-test-report",
        "phase": "final",
        "command_id": "visible-tests",
        "passed_node_ids": ["single", "sequential", "independent", "concurrent"],
        "failed_node_ids": [],
        "errored_node_ids": [],
        "skipped_node_ids": [],
    }
    initial_size, initial_digest = _write_json(
        root / "evidence/visible-tests-initial.json", initial_report
    )
    final_size, final_digest = _write_json(
        root / "evidence/visible-tests-final.json", final_report
    )
    audit = {
        "requested_model": requested_model,
        "resolved_model": resolved_model,
        "request_id": "e5-test-request",
        "prompt_tokens": 400,
        "completion_tokens": 200,
        "request_bytes": 1000,
        "response_bytes": 2000,
        "elapsed_seconds": 1.25,
        "client_retry_count": 0,
        "redirects_followed": 0,
        "content_sha256": "2" * 64,
    }
    audit_size, audit_digest = _write_json(
        root / "evidence/model-proxy-audit.json", audit
    )

    manifest: dict[str, Any] = {
        "schema_version": "evidence-intake/1.0.0",
        "bundle_id": "duplicate-job-processing-experiment-1",
        "produced_at": TIMESTAMP,
        "jobspec_reference": {
            "schema_version": "jobspec-reference/1.0.0",
            "jobspec_id": jobspec_id,
            "jobspec_digest": jobspec_digest,
            "jobspec_format_version": "1.0.0",
            "task_kind": "bug_fix",
            "retry_budget": 1,
            "declared_visible_test_command": "{python} -m pytest tests_visible",
        },
        "attempts": [
            {
                "attempt_index": 0,
                "started_at": TIMESTAMP,
                "ended_at": TIMESTAMP,
                "outcome": "succeeded",
                "is_retry": False,
            }
        ],
        "visible_test_results": {
            "initial": {
                "command": "{python} -m pytest tests_visible",
                "exit_code": 1,
                "total": 4,
                "passed": 3,
                "failed": 1,
                "errors": 0,
                "skipped": 0,
                "duration_seconds": 0.5,
                "report_sha256": initial_digest,
                "collected_at": TIMESTAMP,
            },
            "final": {
                "command": "{python} -m pytest tests_visible",
                "exit_code": 0,
                "total": 4,
                "passed": 4,
                "failed": 0,
                "errors": 0,
                "skipped": 0,
                "duration_seconds": 0.5,
                "report_sha256": final_digest,
                "collected_at": TIMESTAMP,
            },
        },
        "candidate_artifacts": [
            {
                "path": "candidate/patch.diff",
                "media_type": "text/x-diff",
                "size_bytes": len(patch_bytes),
                "sha256": _sha256(patch_bytes),
                "entry_type": "file",
                "role": "patch",
            },
            {
                "path": "evidence/visible-tests-initial.json",
                "media_type": "application/json",
                "size_bytes": initial_size,
                "sha256": initial_digest,
                "entry_type": "file",
                "role": "test_report",
            },
            {
                "path": "evidence/visible-tests-final.json",
                "media_type": "application/json",
                "size_bytes": final_size,
                "sha256": final_digest,
                "entry_type": "file",
                "role": "test_report",
            },
            {
                "path": "evidence/model-proxy-audit.json",
                "media_type": "application/json",
                "size_bytes": audit_size,
                "sha256": audit_digest,
                "entry_type": "file",
                "role": "metadata",
            },
        ],
        "narrative": {
            "trust_level": "untrusted",
            "agent_summary": narrative,
            "reviewer_note": narrative,
        },
        "redactions": [],
        "provenance": {
            "tool_name": "agent-workbench",
            "tool_version": "0.1.0",
            "workbench_commit": "3" * 40,
            "environment_id": "e5-test",
            "durable_execution": False,
        },
    }
    manifest["manifest_digest"] = _sha256(_canonical(manifest))
    (root / "manifest.json").write_bytes(_canonical(manifest) + b"\n")
    return root


def _evaluate(submission: Path, workspace: Path, *, run_id: str = "e5-run") -> dict[str, Any]:
    return evaluate_experiment_one(
        submission,
        evaluation_run_id=run_id,
        expected_jobspec_digest=EXPECTED_JOBSPEC_DIGEST,
        expected_requested_model=REQUESTED_MODEL,
        expected_resolved_model=RESOLVED_MODEL,
        workspace_root=workspace,
        decided_at=TIMESTAMP,
    )


def _gate(report: dict[str, Any], gate_id: str) -> dict[str, Any]:
    return next(item for item in report["gate_results"] if item["gate_id"] == gate_id)


def test_production_intake_accepts_the_exact_submission(tmp_path: Path) -> None:
    patch = _patch_for(tmp_path, "src/processor.py", FIXTURE / "reference/processor.py")
    submission = _write_submission(tmp_path / "submission", patch=patch)
    bundle = intake_submission(submission)
    assert bundle.bundle_id == "duplicate-job-processing-experiment-1"
    assert bundle.jobspec_digest == EXPECTED_JOBSPEC_DIGEST
    assert bundle.model_audit["client_retry_count"] == 0


def test_atomic_repair_reaches_accepted_for_review(tmp_path: Path) -> None:
    patch = _patch_for(tmp_path, "src/processor.py", FIXTURE / "reference/processor.py")
    submission = _write_submission(tmp_path / "submission", patch=patch)
    report = _evaluate(submission, tmp_path / "workspaces")

    assert report["outcome"] == "accepted_for_review"
    assert all(gate["passed"] for gate in report["gate_results"])
    assert _gate(report, "effect_once")["passed"] is True
    assert _gate(report, "not_symptom_suppression")["passed"] is True
    assert report["verifier_attestation"] is None
    assert report["scorers"] == []
    assert report["no_merge_performed"] is True
    assert report["no_deployment_performed"] is True
    assert report["human_review_required"] is True


def test_duct_tape_is_rejected_even_when_visible_tests_pass(tmp_path: Path) -> None:
    patch = _patch_for(tmp_path, "src/store.py", FIXTURE / "patches/ducttape_store.py")
    submission = _write_submission(tmp_path / "submission", patch=patch)
    report = _evaluate(submission, tmp_path / "workspaces")

    assert report["outcome"] == "rejected"
    assert _gate(report, "public_visible_tests")["passed"] is True
    assert _gate(report, "effect_once")["passed"] is False
    assert _gate(report, "not_symptom_suppression")["passed"] is False
    assert "accepted_for_review" in json.loads(
        (submission / "manifest.json").read_text(encoding="utf-8")
    )["narrative"]["agent_summary"]


def test_altered_patch_is_rejected_at_intake_before_workspace_creation(tmp_path: Path) -> None:
    patch = _patch_for(tmp_path, "src/processor.py", FIXTURE / "reference/processor.py")
    submission = _write_submission(tmp_path / "submission", patch=patch)
    with (submission / "candidate/patch.diff").open("a", encoding="utf-8") as stream:
        stream.write("x")
    workspaces = tmp_path / "workspaces"
    report = _evaluate(submission, workspaces)

    assert report["outcome"] == "rejected"
    assert [gate["gate_id"] for gate in report["gate_results"]] == ["intake"]
    assert report["gate_results"][0]["passed"] is False
    assert not workspaces.exists()


def test_model_identity_mismatch_is_rejected_before_patch_execution(tmp_path: Path) -> None:
    patch = _patch_for(tmp_path, "src/processor.py", FIXTURE / "reference/processor.py")
    submission = _write_submission(
        tmp_path / "submission", patch=patch, resolved_model="other/model"
    )
    report = _evaluate(submission, tmp_path / "workspaces")

    assert report["outcome"] == "rejected"
    assert _gate(report, "model_provenance")["passed"] is False
    assert not (tmp_path / "workspaces/e5-run").exists()


def test_unknown_jobspec_abstains_without_execution(tmp_path: Path) -> None:
    patch = _patch_for(tmp_path, "src/processor.py", FIXTURE / "reference/processor.py")
    submission = _write_submission(
        tmp_path / "submission", patch=patch, jobspec_id="other-approved-shape"
    )
    report = _evaluate(submission, tmp_path / "workspaces")

    assert report["outcome"] == "abstained"
    assert _gate(report, "fixture_supported")["passed"] is False
    assert not (tmp_path / "workspaces/e5-run").exists()


def test_jobspec_digest_mismatch_is_rejected(tmp_path: Path) -> None:
    patch = _patch_for(tmp_path, "src/processor.py", FIXTURE / "reference/processor.py")
    submission = _write_submission(
        tmp_path / "submission", patch=patch, jobspec_digest="9" * 64
    )
    report = _evaluate(submission, tmp_path / "workspaces")
    assert report["outcome"] == "rejected"
    assert _gate(report, "jobspec_correspondence")["passed"] is False


def test_patch_outside_permitted_source_paths_is_rejected(tmp_path: Path) -> None:
    patch = (
        "diff --git a/tests_visible/test_processing.py b/tests_visible/test_processing.py\n"
        "--- a/tests_visible/test_processing.py\n"
        "+++ b/tests_visible/test_processing.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-old\n"
        "+new\n"
    )
    submission = _write_submission(tmp_path / "submission", patch=patch)
    report = _evaluate(submission, tmp_path / "workspaces")
    assert report["outcome"] == "rejected"
    assert _gate(report, "patch_paths")["passed"] is False


def test_candidate_build_failure_is_rejected_not_infrastructure_failure(tmp_path: Path) -> None:
    broken = "def this is not python\n"
    patch = _patch_for(tmp_path, "src/processor.py", broken)
    submission = _write_submission(tmp_path / "submission", patch=patch)
    report = _evaluate(submission, tmp_path / "workspaces")
    assert report["outcome"] == "rejected"
    assert _gate(report, "build")["passed"] is False


def test_harness_failure_is_classified_separately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch = _patch_for(tmp_path, "src/processor.py", FIXTURE / "reference/processor.py")
    submission = _write_submission(tmp_path / "submission", patch=patch)

    def fail(_destination: Path) -> None:
        raise EvaluationInfrastructureError("induced fixture-copy failure")

    monkeypatch.setattr(experiment_one, "_copy_public_fixture", fail)
    report = _evaluate(submission, tmp_path / "workspaces")
    assert report["outcome"] == "infrastructure_failure"
    assert _gate(report, "evaluation_infrastructure")["passed"] is False


def test_workspace_copy_contains_no_reference_patch_or_hidden_suite(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    experiment_one._copy_public_fixture(workspace)
    assert (workspace / "src/processor.py").is_file()
    assert (workspace / "tests_visible/test_processing.py").is_file()
    assert (workspace / "probe.py").is_file()
    assert not (workspace / "reference").exists()
    assert not (workspace / "patches").exists()
    assert not (workspace / "tests_hidden").exists()


def test_every_emitted_report_matches_the_released_outcome_schema(tmp_path: Path) -> None:
    patch = _patch_for(tmp_path, "src/processor.py", FIXTURE / "reference/processor.py")
    submission = _write_submission(tmp_path / "submission", patch=patch)
    report = _evaluate(submission, tmp_path / "workspaces")
    assert validate(report, schema_by_title("evallab-outcome/1.0.0")) == ()
    assert [gate["order"] for gate in report["gate_results"]] == list(
        range(len(report["gate_results"]))
    )


def test_intake_schema_rejects_unexpected_manifest_property(tmp_path: Path) -> None:
    patch = _patch_for(tmp_path, "src/processor.py", FIXTURE / "reference/processor.py")
    submission = _write_submission(tmp_path / "submission", patch=patch)
    manifest_path = submission / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["producer_verdict"] = "accepted_for_review"
    manifest["manifest_digest"] = _sha256(
        _canonical({key: value for key, value in manifest.items() if key != "manifest_digest"})
    )
    manifest_path.write_bytes(_canonical(manifest) + b"\n")
    with pytest.raises(IntakeRejected) as captured:
        intake_submission(submission)
    assert any(item.code == "unexpected_property" for item in captured.value.violations)
