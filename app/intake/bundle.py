"""Fail-closed intake for materialised ``evidence-intake/1.0.0`` bundles."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.intake.schema_subset import schema_by_title, validate

INTAKE_SCHEMA = schema_by_title("evidence-intake/1.0.0")
MAX_FILES = 64
MAX_TOTAL_BYTES = 64 * 1_048_576


@dataclass(frozen=True)
class IntakeViolation:
    code: str
    pointer: str
    detail: str | None = None


class IntakeRejected(ValueError):
    def __init__(self, violations: tuple[IntakeViolation, ...]) -> None:
        self.violations = violations
        rendered = "; ".join(
            f"{item.code}@{item.pointer or '/'}" + (f" ({item.detail})" if item.detail else "")
            for item in violations
        )
        super().__init__(rendered or "evidence intake rejected")


@dataclass(frozen=True)
class IntakeBundle:
    root: Path
    manifest: dict[str, Any]
    artifacts: dict[str, Path]
    model_audit: dict[str, Any]

    @property
    def bundle_id(self) -> str:
        return str(self.manifest["bundle_id"])

    @property
    def manifest_digest(self) -> str:
        return str(self.manifest["manifest_digest"])

    @property
    def jobspec_digest(self) -> str:
        return str(self.manifest["jobspec_reference"]["jobspec_digest"])


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_json(path: Path, *, code: str, pointer: str) -> tuple[Any | None, IntakeViolation | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, IntakeViolation(code, pointer, type(exc).__name__)


def _schema_violations(document: Any) -> list[IntakeViolation]:
    return [
        IntakeViolation(item.code, item.pointer, item.detail)
        for item in validate(document, INTAKE_SCHEMA)
    ]


def _artifact_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["path"]): item for item in manifest["candidate_artifacts"]}


def _check_manifest_digest(manifest: dict[str, Any]) -> IntakeViolation | None:
    stripped = {key: value for key, value in manifest.items() if key != "manifest_digest"}
    actual = _sha256_bytes(_canonical(stripped))
    if actual != manifest["manifest_digest"]:
        return IntakeViolation("manifest_digest_mismatch", "/manifest_digest", actual)
    return None


def _check_lineage(manifest: dict[str, Any]) -> list[IntakeViolation]:
    violations: list[IntakeViolation] = []
    attempts = manifest["attempts"]
    indices = [attempt["attempt_index"] for attempt in attempts]
    expected = list(range(len(attempts)))
    if indices != expected:
        violations.append(
            IntakeViolation("attempt_indices_not_contiguous", "/attempts", str(indices))
        )
    if attempts and attempts[0]["is_retry"]:
        violations.append(IntakeViolation("first_attempt_marked_retry", "/attempts/0/is_retry"))
    for index, attempt in enumerate(attempts[1:], start=1):
        if not attempt["is_retry"]:
            violations.append(
                IntakeViolation("later_attempt_not_marked_retry", f"/attempts/{index}/is_retry")
            )
    retry_budget = manifest["jobspec_reference"]["retry_budget"]
    if len(attempts) > retry_budget:
        violations.append(
            IntakeViolation(
                "attempt_budget_exceeded",
                "/attempts",
                f"{len(attempts)}>{retry_budget}",
            )
        )
    return violations


def _materialised_files(root: Path) -> tuple[dict[str, Path], list[IntakeViolation]]:
    files: dict[str, Path] = {}
    violations: list[IntakeViolation] = []
    total_bytes = 0
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path == root / "manifest.json":
            continue
        if path.is_symlink():
            violations.append(IntakeViolation("symlink_not_allowed", f"/{relative}"))
            continue
        if path.is_dir():
            continue
        try:
            stat = path.stat()
        except OSError as exc:
            violations.append(
                IntakeViolation("artifact_stat_failed", f"/{relative}", type(exc).__name__)
            )
            continue
        if not path.is_file():
            violations.append(IntakeViolation("non_regular_entry", f"/{relative}"))
            continue
        if stat.st_nlink != 1:
            violations.append(IntakeViolation("hard_link_not_allowed", f"/{relative}"))
        files[relative] = path
        total_bytes += stat.st_size
    if len(files) > MAX_FILES:
        violations.append(IntakeViolation("too_many_materialised_files", "", str(len(files))))
    if total_bytes > MAX_TOTAL_BYTES:
        violations.append(IntakeViolation("materialised_bytes_exceeded", "", str(total_bytes)))
    return files, violations


def _check_artifacts(
    root: Path,
    manifest: dict[str, Any],
) -> tuple[dict[str, Path], list[IntakeViolation]]:
    declared = _artifact_map(manifest)
    actual, violations = _materialised_files(root)
    declared_paths = set(declared)
    actual_paths = set(actual)
    for extra in sorted(actual_paths - declared_paths):
        violations.append(IntakeViolation("undeclared_artifact", f"/{extra}"))
    for missing in sorted(declared_paths - actual_paths):
        violations.append(IntakeViolation("declared_artifact_missing", f"/{missing}"))

    for relative in sorted(declared_paths & actual_paths):
        path = actual[relative]
        declaration = declared[relative]
        data = path.read_bytes()
        if len(data) != declaration["size_bytes"]:
            violations.append(
                IntakeViolation("artifact_size_mismatch", f"/candidate_artifacts/{relative}")
            )
        if _sha256_bytes(data) != declaration["sha256"]:
            violations.append(
                IntakeViolation("artifact_digest_mismatch", f"/candidate_artifacts/{relative}")
            )
    return actual, violations


def _counts_from_report(report: dict[str, Any]) -> tuple[int, int, int, int] | None:
    required = (
        "passed_node_ids",
        "failed_node_ids",
        "errored_node_ids",
        "skipped_node_ids",
    )
    if not all(isinstance(report.get(name), list) for name in required):
        return None
    return tuple(len(report[name]) for name in required)  # type: ignore[return-value]


def _check_test_reports(
    manifest: dict[str, Any], artifacts: dict[str, Path]
) -> list[IntakeViolation]:
    violations: list[IntakeViolation] = []
    by_digest = {item["sha256"]: item for item in manifest["candidate_artifacts"]}
    for phase in ("initial", "final"):
        summary = manifest["visible_test_results"][phase]
        if (
            summary["passed"] + summary["failed"] + summary["errors"] + summary["skipped"]
            != summary["total"]
        ):
            violations.append(
                IntakeViolation("test_counts_do_not_sum", f"/visible_test_results/{phase}")
            )
        declaration = by_digest.get(summary["report_sha256"])
        if declaration is None or declaration.get("role") != "test_report":
            violations.append(
                IntakeViolation(
                    "test_report_digest_not_declared",
                    f"/visible_test_results/{phase}/report_sha256",
                )
            )
            continue
        path = artifacts.get(declaration["path"])
        if path is None:
            continue
        report, error = _load_json(
            path,
            code="test_report_invalid_json",
            pointer=f"/{declaration['path']}",
        )
        if error:
            violations.append(error)
            continue
        if not isinstance(report, dict):
            violations.append(IntakeViolation("test_report_not_object", f"/{declaration['path']}"))
            continue
        counts = _counts_from_report(report)
        expected = (
            summary["passed"],
            summary["failed"],
            summary["errors"],
            summary["skipped"],
        )
        if counts != expected:
            violations.append(
                IntakeViolation(
                    "test_report_count_mismatch",
                    f"/visible_test_results/{phase}",
                    f"{counts}!={expected}",
                )
            )
    return violations


def _check_redactions(
    manifest: dict[str, Any], artifacts: dict[str, Path]
) -> list[IntakeViolation]:
    violations: list[IntakeViolation] = []
    observed: dict[str, int] = {}
    for relative, path in artifacts.items():
        text = path.read_text(encoding="utf-8", errors="replace")
        count = text.count("[redacted]") + text.count("[REDACTED]")
        if count:
            observed[relative] = count
    recorded = {item["location"]: item["occurrences"] for item in manifest["redactions"]}
    if recorded != observed:
        violations.append(
            IntakeViolation(
                "redaction_records_mismatch",
                "/redactions",
                f"recorded={recorded},observed={observed}",
            )
        )
    return violations


def _load_model_audit(
    manifest: dict[str, Any], artifacts: dict[str, Path]
) -> tuple[dict[str, Any] | None, list[IntakeViolation]]:
    violations: list[IntakeViolation] = []
    candidates = [
        item
        for item in manifest["candidate_artifacts"]
        if item.get("role") == "metadata" and item["path"].endswith("model-proxy-audit.json")
    ]
    if len(candidates) != 1:
        return None, [
            IntakeViolation(
                "model_audit_count_invalid", "/candidate_artifacts", str(len(candidates))
            )
        ]
    declaration = candidates[0]
    path = artifacts.get(declaration["path"])
    if path is None:
        return None, violations
    audit, error = _load_json(
        path,
        code="model_audit_invalid_json",
        pointer=f"/{declaration['path']}",
    )
    if error:
        return None, [error]
    if not isinstance(audit, dict):
        return None, [IntakeViolation("model_audit_not_object", f"/{declaration['path']}")]

    for key in ("requested_model", "resolved_model", "content_sha256"):
        if not isinstance(audit.get(key), str) or not audit[key]:
            violations.append(
                IntakeViolation("model_audit_field_missing", f"/{declaration['path']}/{key}")
            )
    if audit.get("client_retry_count") != 0:
        violations.append(
            IntakeViolation("client_retries_not_zero", f"/{declaration['path']}/client_retry_count")
        )
    if audit.get("redirects_followed") != 0:
        violations.append(
            IntakeViolation("redirects_followed", f"/{declaration['path']}/redirects_followed")
        )
    if "content" in audit:
        violations.append(
            IntakeViolation("model_content_persisted", f"/{declaration['path']}/content")
        )
    content_digest = audit.get("content_sha256")
    if isinstance(content_digest, str) and not (
        len(content_digest) == 64 and all(char in "0123456789abcdef" for char in content_digest)
    ):
        violations.append(
            IntakeViolation(
                "model_content_digest_invalid", f"/{declaration['path']}/content_sha256"
            )
        )
    return audit, violations


def intake_submission(bundle_root: Path) -> IntakeBundle:
    """Validate all public structure and materialisation before any execution."""
    root = Path(bundle_root)
    violations: list[IntakeViolation] = []
    if root.is_symlink() or not root.is_dir():
        raise IntakeRejected((IntakeViolation("bundle_root_not_directory", ""),))
    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise IntakeRejected((IntakeViolation("manifest_missing", "/manifest.json"),))

    document, error = _load_json(
        manifest_path,
        code="manifest_invalid_json",
        pointer="/manifest.json",
    )
    if error:
        raise IntakeRejected((error,))
    violations.extend(_schema_violations(document))
    if violations or not isinstance(document, dict):
        raise IntakeRejected(tuple(violations))

    digest_violation = _check_manifest_digest(document)
    if digest_violation:
        violations.append(digest_violation)
    violations.extend(_check_lineage(document))
    artifacts, materialisation = _check_artifacts(root, document)
    violations.extend(materialisation)
    violations.extend(_check_test_reports(document, artifacts))
    violations.extend(_check_redactions(document, artifacts))
    model_audit, audit_violations = _load_model_audit(document, artifacts)
    violations.extend(audit_violations)

    if violations or model_audit is None:
        raise IntakeRejected(tuple(violations))
    return IntakeBundle(
        root=root.resolve(),
        manifest=document,
        artifacts=artifacts,
        model_audit=model_audit,
    )
