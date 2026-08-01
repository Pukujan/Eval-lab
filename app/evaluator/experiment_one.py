"""Minimum public evaluation for Experiment 1.

One versioned Agent-workbench submission is validated before execution, applied to
a clean copy of the existing duplicate-processing fixture, and judged only by
ordered deterministic gates. No model or reviewer text selects the outcome. No
private verifier is invoked in this experiment.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.intake.bundle import IntakeBundle, IntakeRejected, intake_submission
from app.intake.schema_subset import schema_by_title, validate

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "duplicate-job-processing"
OUTCOME_SCHEMA = schema_by_title("evallab-outcome/1.0.0")
EXPECTED_JOBSPEC_ID = "duplicate-job-processing"
PERMITTED_PATCH_PATHS = frozenset({"src/processor.py", "src/store.py"})
_PATCH_HEADER = re.compile(r"^diff --git a/([^ ]+) b/([^ ]+)$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

Outcome = Literal[
    "accepted_for_review",
    "rejected",
    "abstained",
    "infrastructure_failure",
]


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool


class EvaluationInfrastructureError(RuntimeError):
    """The evaluation harness itself could not perform a required operation."""


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _scrubbed_environment() -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
    }


def _run(
    argv: tuple[str, ...],
    *,
    cwd: Path,
    timeout: float,
    env: dict[str, str] | None = None,
) -> CommandResult:
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env=env or _scrubbed_environment(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (
            exc.stdout.decode("utf-8", errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        stderr = (
            exc.stderr.decode("utf-8", errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        return CommandResult(argv, None, stdout, stderr, True)
    except OSError as exc:
        raise EvaluationInfrastructureError(
            f"could not start {argv[0]!r}: {type(exc).__name__}"
        ) from exc
    return CommandResult(
        argv=argv,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        timed_out=False,
    )


def _gate(
    order: int,
    gate_id: str,
    passed: bool,
    detail: str,
    evidence_pointer: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "order": order,
        "gate_id": gate_id,
        "passed": passed,
        "detail": detail[:1000] or "no detail",
    }
    if evidence_pointer is not None:
        record["evidence_pointer"] = evidence_pointer[:200]
    return record


def _safe_input_identity(bundle_root: Path) -> tuple[str, str]:
    manifest = Path(bundle_root) / "manifest.json"
    try:
        raw = manifest.read_bytes()
    except OSError:
        return "unreadable-bundle", "0" * 64
    digest = _sha256(raw)
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "unreadable-bundle", digest
    candidate = document.get("bundle_id") if isinstance(document, dict) else None
    if isinstance(candidate, str) and _IDENTIFIER.fullmatch(candidate):
        return candidate, digest
    return "unreadable-bundle", digest


def _outcome_report(
    *,
    evaluation_run_id: str,
    bundle_id: str,
    manifest_digest: str,
    outcome: Outcome,
    gates: list[dict[str, Any]],
    rationale: str,
    decided_at: str,
    caveats: list[str] | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": "evallab-outcome/1.0.0",
        "evaluation_run_id": evaluation_run_id,
        "bundle_id": bundle_id,
        "bundle_manifest_digest": manifest_digest,
        "outcome": outcome,
        "rationale": rationale[:4000],
        "decided_at": decided_at,
        "gate_results": gates,
        "scorers": [],
        "verifier_attestation": None,
        "caveats": caveats
        or [
            "Evaluation used the non-durable local Experiment 1 executor.",
            "The private verifier was not invoked in Experiment 1.",
            "The result covers one fixture and one submitted patch only.",
        ],
        "durable_execution": False,
        "no_merge_performed": True,
        "no_deployment_performed": True,
        "human_review_required": True,
    }
    violations = validate(report, OUTCOME_SCHEMA)
    if violations:
        rendered = ", ".join(f"{item.code}@{item.pointer}" for item in violations)
        raise EvaluationInfrastructureError(f"outcome report violated its schema: {rendered}")
    orders = [gate["order"] for gate in gates]
    if orders != list(range(len(gates))):
        raise EvaluationInfrastructureError(f"gate order is not contiguous: {orders}")
    return report


def _copy_public_fixture(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copytree(FIXTURE_ROOT / "src", destination / "src")
    shutil.copytree(FIXTURE_ROOT / "tests_visible", destination / "tests_visible")
    shutil.copy2(FIXTURE_ROOT / "probe.py", destination / "probe.py")
    if any((destination / name).exists() for name in ("patches", "reference", "tests_hidden")):
        raise EvaluationInfrastructureError(
            "private or reference fixture material entered workspace"
        )


def _patch_paths(patch_text: str) -> tuple[tuple[str, ...], str | None]:
    paths: list[str] = []
    for line in patch_text.splitlines():
        if not line.startswith("diff --git "):
            continue
        match = _PATCH_HEADER.fullmatch(line)
        if match is None:
            return (), f"malformed diff header: {line[:160]}"
        left, right = match.groups()
        if left != right:
            return (), f"rename or path mismatch is not permitted: {left} != {right}"
        if left.startswith("/") or ".." in Path(left).parts or "\\" in left:
            return (), f"unsafe patch path: {left}"
        paths.append(left)
    if not paths:
        return (), "patch contains no diff header"
    if len(set(paths)) != len(paths):
        return (), "patch changes one path more than once"
    return tuple(paths), None


def _initialise_workspace(workspace: Path) -> None:
    commands = (
        ("git", "init", "-q"),
        ("git", "config", "user.name", "Eval-lab"),
        ("git", "config", "user.email", "eval-lab@example.invalid"),
        ("git", "add", "src", "tests_visible", "probe.py"),
        ("git", "commit", "-q", "-m", "base public fixture"),
    )
    env = _scrubbed_environment() | {
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
    }
    for argv in commands:
        result = _run(argv, cwd=workspace, timeout=30, env=env)
        if result.timed_out or result.exit_code != 0:
            raise EvaluationInfrastructureError(
                f"workspace initialization failed for {argv}: {result.stderr[:300]}"
            )


def _apply_patch(workspace: Path, patch_path: Path) -> tuple[bool, str]:
    check = _run(
        ("git", "apply", "--check", "--whitespace=nowarn", str(patch_path)),
        cwd=workspace,
        timeout=30,
    )
    if check.timed_out:
        return False, "patch applicability check timed out"
    if check.exit_code != 0:
        return False, f"patch does not apply: {check.stderr[:500]}"
    applied = _run(
        ("git", "apply", "--whitespace=nowarn", str(patch_path)),
        cwd=workspace,
        timeout=30,
    )
    if applied.timed_out:
        return False, "patch application timed out"
    if applied.exit_code != 0:
        return False, f"patch application failed: {applied.stderr[:500]}"
    return True, "patch applied to the clean public fixture"


def _find_patch(bundle: IntakeBundle) -> tuple[Path | None, str]:
    declarations = [
        item for item in bundle.manifest["candidate_artifacts"] if item.get("role") == "patch"
    ]
    if len(declarations) != 1:
        return None, f"expected exactly one patch artifact, found {len(declarations)}"
    relative = declarations[0]["path"]
    return bundle.artifacts[relative], relative


def _probe_result(workspace: Path) -> tuple[dict[str, Any] | None, str]:
    database = workspace / "probe.db"
    result = _run(
        (sys.executable, "probe.py", str(database), "2"),
        cwd=workspace,
        timeout=30,
    )
    if result.timed_out:
        return None, "public duplicate-processing probe timed out"
    if result.exit_code != 0:
        return None, f"public probe failed with exit {result.exit_code}: {result.stderr[:400]}"
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None, "public probe did not emit one JSON document"
    if not isinstance(document, dict):
        return None, "public probe result was not an object"
    required = {
        "raw_result_rows",
        "effect_count",
        "reported_commits",
        "invariant_holds",
        "duplicate_processing",
    }
    if not required.issubset(document):
        return None, f"public probe result omitted {sorted(required - set(document))}"
    return document, "public probe completed"


def _finish(
    *,
    evaluation_run_id: str,
    bundle: IntakeBundle,
    gates: list[dict[str, Any]],
    decided_at: str,
    forced_outcome: Outcome | None = None,
    forced_rationale: str | None = None,
) -> dict[str, Any]:
    failed = [gate["gate_id"] for gate in gates if not gate["passed"]]
    outcome: Outcome = forced_outcome or ("rejected" if failed else "accepted_for_review")
    if forced_rationale is not None:
        rationale = forced_rationale
    elif failed:
        rationale = "Deterministic public gates failed: " + ", ".join(failed) + "."
    else:
        rationale = (
            "Every deterministic Experiment 1 public gate passed for the exact submitted "
            "bundle; a human review is required."
        )
    return _outcome_report(
        evaluation_run_id=evaluation_run_id,
        bundle_id=bundle.bundle_id,
        manifest_digest=bundle.manifest_digest,
        outcome=outcome,
        gates=gates,
        rationale=rationale,
        decided_at=decided_at,
    )


def evaluate_experiment_one(
    bundle_root: Path,
    *,
    evaluation_run_id: str,
    expected_jobspec_digest: str,
    expected_requested_model: str,
    expected_resolved_model: str,
    workspace_root: Path,
    decided_at: str | None = None,
) -> dict[str, Any]:
    """Evaluate one submission without a scorer or private verifier."""
    decided = decided_at or _utc_now()
    try:
        bundle = intake_submission(bundle_root)
    except IntakeRejected as exc:
        bundle_id, raw_digest = _safe_input_identity(bundle_root)
        detail = "; ".join(f"{item.code}@{item.pointer or '/'}" for item in exc.violations)[:1000]
        return _outcome_report(
            evaluation_run_id=evaluation_run_id,
            bundle_id=bundle_id,
            manifest_digest=raw_digest,
            outcome="rejected",
            gates=[_gate(0, "intake", False, detail or "intake rejected")],
            rationale="The submitted evidence failed deterministic intake before execution.",
            decided_at=decided,
        )

    gates: list[dict[str, Any]] = [
        _gate(
            0,
            "intake",
            True,
            "Schema, manifest, artifact, lineage, report, redaction, and model-audit checks passed.",
            "/",
        )
    ]

    jobspec = bundle.manifest["jobspec_reference"]
    if jobspec["jobspec_id"] != EXPECTED_JOBSPEC_ID:
        gates.append(
            _gate(
                1,
                "fixture_supported",
                False,
                f"No Experiment 1 evaluator is configured for {jobspec['jobspec_id']!r}.",
                "/jobspec_reference/jobspec_id",
            )
        )
        return _finish(
            evaluation_run_id=evaluation_run_id,
            bundle=bundle,
            gates=gates,
            decided_at=decided,
            forced_outcome="abstained",
            forced_rationale="Eval-lab has no approved Experiment 1 evaluator for this JobSpec.",
        )

    digest_matches = jobspec["jobspec_digest"] == expected_jobspec_digest
    gates.append(
        _gate(
            1,
            "jobspec_correspondence",
            digest_matches,
            (
                "JobSpec id and digest match the frozen Experiment 1 selection."
                if digest_matches
                else "JobSpec digest does not match the frozen Experiment 1 selection."
            ),
            "/jobspec_reference/jobspec_digest",
        )
    )
    if not digest_matches:
        return _finish(
            evaluation_run_id=evaluation_run_id,
            bundle=bundle,
            gates=gates,
            decided_at=decided,
        )

    audit = bundle.model_audit
    model_matches = (
        audit["requested_model"] == expected_requested_model
        and audit["resolved_model"] == expected_resolved_model
        and audit["client_retry_count"] == 0
        and audit["redirects_followed"] == 0
    )
    gates.append(
        _gate(
            2,
            "model_provenance",
            model_matches,
            (
                f"requested={audit['requested_model']!r}, resolved={audit['resolved_model']!r}, "
                f"client_retries={audit['client_retry_count']}, redirects={audit['redirects_followed']}"
            ),
            "/candidate_artifacts",
        )
    )
    if not model_matches:
        return _finish(
            evaluation_run_id=evaluation_run_id,
            bundle=bundle,
            gates=gates,
            decided_at=decided,
        )

    patch_path, patch_pointer = _find_patch(bundle)
    if patch_path is None:
        gates.append(_gate(3, "patch_paths", False, patch_pointer, "/candidate_artifacts"))
        return _finish(
            evaluation_run_id=evaluation_run_id,
            bundle=bundle,
            gates=gates,
            decided_at=decided,
        )
    patch_text = patch_path.read_text(encoding="utf-8", errors="strict")
    paths, path_error = _patch_paths(patch_text)
    permitted = path_error is None and set(paths).issubset(PERMITTED_PATCH_PATHS)
    detail = path_error or f"changed paths: {list(paths)}"
    if path_error is None and not permitted:
        detail = (
            f"changed paths outside the permit set: {sorted(set(paths) - PERMITTED_PATCH_PATHS)}"
        )
    gates.append(_gate(3, "patch_paths", permitted, detail, f"/{patch_pointer}"))
    if not permitted:
        return _finish(
            evaluation_run_id=evaluation_run_id,
            bundle=bundle,
            gates=gates,
            decided_at=decided,
        )

    workspace = Path(workspace_root) / evaluation_run_id
    if workspace.exists():
        shutil.rmtree(workspace)
    try:
        _copy_public_fixture(workspace)
        _initialise_workspace(workspace)
        applied, apply_detail = _apply_patch(workspace, patch_path)
        gates.append(_gate(4, "patch_applies", applied, apply_detail, f"/{patch_pointer}"))
        if not applied:
            return _finish(
                evaluation_run_id=evaluation_run_id,
                bundle=bundle,
                gates=gates,
                decided_at=decided,
            )

        build = _run(
            (sys.executable, "-m", "compileall", "-q", "src"),
            cwd=workspace,
            timeout=30,
        )
        build_passed = not build.timed_out and build.exit_code == 0
        gates.append(
            _gate(
                5,
                "build",
                build_passed,
                (
                    "Public fixture source compiled."
                    if build_passed
                    else f"Build failed or timed out: {build.stderr[:500]}"
                ),
            )
        )
        if not build_passed:
            return _finish(
                evaluation_run_id=evaluation_run_id,
                bundle=bundle,
                gates=gates,
                decided_at=decided,
            )

        visible = _run(
            (
                sys.executable,
                "-m",
                "pytest",
                "tests_visible",
                "-p",
                "no:cacheprovider",
                "-q",
                "--tb=no",
                "-o",
                "addopts=",
            ),
            cwd=workspace,
            timeout=60,
        )
        visible_passed = not visible.timed_out and visible.exit_code == 0
        gates.append(
            _gate(
                6,
                "public_visible_tests",
                visible_passed,
                (
                    "Independent visible-test execution passed."
                    if visible_passed
                    else f"Independent visible tests failed or timed out: {(visible.stdout + visible.stderr)[-500:]}"
                ),
            )
        )
        if not visible_passed:
            return _finish(
                evaluation_run_id=evaluation_run_id,
                bundle=bundle,
                gates=gates,
                decided_at=decided,
            )

        probe, probe_detail = _probe_result(workspace)
        if probe is None:
            gates.append(_gate(7, "effect_once", False, probe_detail))
            gates.append(_gate(8, "not_symptom_suppression", False, probe_detail))
            return _finish(
                evaluation_run_id=evaluation_run_id,
                bundle=bundle,
                gates=gates,
                decided_at=decided,
            )

        effect_once = probe["effect_count"] == 1
        gates.append(
            _gate(
                7,
                "effect_once",
                effect_once,
                (
                    f"effect_count={probe['effect_count']}, "
                    f"reported_commits={probe['reported_commits']}"
                ),
            )
        )
        not_suppressed = (
            probe["raw_result_rows"] == 1
            and probe["effect_count"] == 1
            and probe["duplicate_processing"] is False
            and probe["invariant_holds"] is True
        )
        gates.append(
            _gate(
                8,
                "not_symptom_suppression",
                not_suppressed,
                (
                    f"raw_result_rows={probe['raw_result_rows']}, "
                    f"effect_count={probe['effect_count']}, "
                    f"duplicate_processing={probe['duplicate_processing']}"
                ),
            )
        )
        return _finish(
            evaluation_run_id=evaluation_run_id,
            bundle=bundle,
            gates=gates,
            decided_at=decided,
        )
    except EvaluationInfrastructureError as exc:
        gates.append(
            _gate(
                len(gates),
                "evaluation_infrastructure",
                False,
                str(exc),
            )
        )
        return _finish(
            evaluation_run_id=evaluation_run_id,
            bundle=bundle,
            gates=gates,
            decided_at=decided,
            forced_outcome="infrastructure_failure",
            forced_rationale="The evaluation harness failed; this outcome says nothing about the submitted patch.",
        )
    finally:
        if workspace.exists():
            shutil.rmtree(workspace)
