"""Deterministic raw-evidence bundle export.

This is the public interface handed to an **external, protected verifier** — one
holding holdouts and mutants that deliberately do not exist in this repository. It
therefore has one job and a very short list of things it must never do.

The job: take the artifact directory a verification run produced, copy the raw
evidence out of it byte-for-byte, hash every file, and write a machine-readable
index saying where each file came from, which system produced it, which Temporal
execution it belongs to, and what its SHA-256 is.

What it must never do:

* **decide whether anything passed.** It copies and hashes. A verdict computed by
  the party being verified is not a verdict.
* **write a self-attesting field.** No ``verified``, ``passed``, ``verdict``. This
  is enforced by :func:`_reject_self_attestation` on the exporter's own output
  rather than left to reviewer discipline, because a bundle that certifies itself
  is worth nothing to the party receiving it.
* **rewrite evidence.** Files are copied verbatim so the recorded hash is checkable
  against the source artifact. Producer-written fields survive inside copied
  evidence — ``phoenix-trace.json`` really does contain ``"verified": true``,
  because the script that produced it wrote that. Those are *claims by the
  producer*, data for the verifier to check, not findings of this bundle.

The export is deterministic: same source tree, byte-identical index. There is
deliberately no generation timestamp — a wall-clock field would destroy that
property in exchange for information the evidence already carries.

An export that cannot be trusted fails rather than warns. Four conditions abort it:
a missing required file, a checksum that does not match after the copy, a workflow
id that maps to more than one run id, and malformed evidence.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Bumped when the shape of ``evidence-index.json`` changes.
BUNDLE_INDEX_VERSION = 1

INDEX_FILENAME = "evidence-index.json"

#: Keys the exporter refuses to author. Copied evidence may contain them; anything
#: this module writes may not.
SELF_ATTESTING_KEYS = frozenset(
    {
        "verified",
        "verdict",
        "passed",
        "attestation",
        "attested",
        "certified",
        "approved",
        "conclusion",
        "criteria_passed",
        "production_ready",
    }
)


class BundleIntegrityError(Exception):
    """Base class: the bundle could not be produced in a trustworthy state."""


class MissingEvidenceError(BundleIntegrityError):
    """A required piece of evidence is absent from the source artifact."""


class ChecksumMismatchError(BundleIntegrityError):
    """A file's content does not match the hash recorded for it."""


class AmbiguousWorkflowError(BundleIntegrityError):
    """The bundle cannot say which Temporal execution some evidence describes."""


class MalformedEvidenceError(BundleIntegrityError):
    """Evidence is unparseable, structurally wrong, or self-contradictory."""


# ---------------------------------------------------------------------------
# What gets collected
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceSpec:
    """One collection rule.

    ``source`` is relative to the artifact root. A trailing ``/**`` collects a
    subtree (relative layout preserved); a ``*`` collects a flat glob; anything
    else is a single file.
    """

    logical_name: str
    source: str
    destination_dir: str
    category: str
    source_system: str
    kind: str = "opaque"
    required: bool = True


#: The collection table. Ordered for readability; collection order is sorted, so
#: rearranging this list cannot change the bundle.
EVIDENCE_SPECS: tuple[EvidenceSpec, ...] = (
    # -- Temporal ---------------------------------------------------------
    EvidenceSpec(
        "temporal-histories",
        "evidence/*.history.json",
        "temporal/histories",
        "temporal_history",
        "temporal",
        kind="temporal_history",
    ),
    EvidenceSpec(
        "worker-interruption-recovery",
        "evidence/durability-recovery.json",
        "temporal/evidence",
        "recovery_evidence",
        "temporal",
        kind="json_evidence",
    ),
    EvidenceSpec(
        "retry-behaviour",
        "evidence/retry-behaviour.json",
        "temporal/evidence",
        "retry_evidence",
        "temporal",
        kind="json_evidence",
    ),
    EvidenceSpec(
        "timeout-behaviour",
        "evidence/timeout-behaviour.json",
        "temporal/evidence",
        "timeout_evidence",
        "temporal",
        kind="json_evidence",
    ),
    EvidenceSpec(
        "replay-determinism",
        "evidence/replay-determinism.json",
        "temporal/evidence",
        "replay_evidence",
        "temporal",
        kind="json_evidence",
    ),
    EvidenceSpec(
        "coding-workflow-smoke",
        "evidence/workflow-smoke.json",
        "temporal/evidence",
        "workflow_execution_evidence",
        "temporal",
        kind="json_evidence",
    ),
    # -- Phoenix ----------------------------------------------------------
    EvidenceSpec(
        "phoenix-trace-query",
        "evidence/phoenix-trace.json",
        "phoenix",
        "trace_query_result",
        "phoenix",
        kind="json_evidence",
    ),
    # -- candidate reliability reports ------------------------------------
    EvidenceSpec(
        "candidate-reliability-reports",
        "reports/reliability-report-*.json",
        "reports",
        "candidate_reliability_report",
        "evaluation_harness",
        kind="reliability_report",
    ),
    EvidenceSpec(
        "evaluation-outcomes",
        "evidence/evaluation-outcomes.json",
        "reports",
        "evaluation_outcome_evidence",
        "evaluation_harness",
        kind="json_evidence",
    ),
    # -- other evaluation platforms ---------------------------------------
    EvidenceSpec(
        "promptfoo-report",
        "reports/promptfoo-report.json",
        "promptfoo",
        "comparison_report",
        "promptfoo",
        kind="report",
    ),
    EvidenceSpec(
        "inspect-logs",
        "reports/inspect-logs/**",
        "inspect",
        "evaluation_log",
        "inspect_ai",
        kind="log",
    ),
    EvidenceSpec(
        "integration-test-report",
        "reports/integration.xml",
        "reports",
        "junit_report",
        "pytest",
        kind="report",
        required=False,
    ),
    # -- packaging and services -------------------------------------------
    EvidenceSpec(
        "compose-verification-clean",
        "evidence/compose-verification-clean.json",
        "compose",
        "compose_verification",
        "docker_compose",
        kind="json_evidence",
    ),
    EvidenceSpec(
        "compose-verification-restart",
        "evidence/compose-verification-restart.json",
        "compose",
        "compose_verification",
        "docker_compose",
        kind="json_evidence",
        required=False,
    ),
    EvidenceSpec(
        "persistence-across-restart",
        "evidence/persistence-across-restart.json",
        "compose",
        "persistence_evidence",
        "docker_compose",
        kind="json_evidence",
    ),
    EvidenceSpec(
        "state-initialisation",
        "evidence/state-initialisation.json",
        "compose",
        "state_initialisation",
        "evaluation_harness",
        kind="json_evidence",
        required=False,
    ),
    EvidenceSpec(
        "dependency-and-image-pins",
        "evidence/pin-verification.json",
        "pins",
        "dependency_and_image_pins",
        "python_package_index",
        kind="json_evidence",
    ),
    # -- logs -------------------------------------------------------------
    EvidenceSpec(
        "container-logs",
        "logs/containers/*",
        "logs/containers",
        "container_log",
        "docker_compose",
        kind="log",
    ),
    EvidenceSpec(
        "harness-logs",
        "logs/*.log",
        "logs",
        "harness_log",
        "evaluation_harness",
        kind="log",
        required=False,
    ),
    # -- the run's own manifest -------------------------------------------
    EvidenceSpec(
        "completion-manifest",
        "completion-manifest.json",
        "manifest",
        "completion_manifest",
        "evaluation_harness",
        kind="completion_manifest",
    ),
)


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _matching_files(root: Path, pattern: str) -> list[Path]:
    """Files a spec's ``source`` selects, in a stable order."""
    if pattern.endswith("/**"):
        base = root / pattern[: -len("/**")]
        if not base.is_dir():
            return []
        return sorted(p for p in base.rglob("*") if p.is_file())
    if any(character in pattern for character in "*?["):
        return sorted(p for p in root.glob(pattern) if p.is_file())
    candidate = root / pattern
    return [candidate] if candidate.is_file() else []


def _destination_for(spec: EvidenceSpec, root: Path, path: Path) -> str:
    """Where a matched file lands in the bundle, as a POSIX path.

    POSIX rather than native so an index written on Windows is byte-identical to
    one written on Linux — this repository's CI runs both.
    """
    if spec.source.endswith("/**"):
        base = root / spec.source[: -len("/**")]
        return (Path(spec.destination_dir) / path.relative_to(base)).as_posix()
    return (Path(spec.destination_dir) / path.name).as_posix()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MalformedEvidenceError(f"{path.name}: not readable as JSON ({exc})") from exc


# ---------------------------------------------------------------------------
# Reading identity out of evidence
# ---------------------------------------------------------------------------


def _history_run_id(path: Path, payload: Any) -> str:
    """Run id recorded inside a serialised Temporal history.

    ``WorkflowHistory.to_json_dict`` omits the workflow id by design, so the run id
    from the first event is the only identity a history file carries on its own.
    Pairing it back to a workflow id is the job of the sibling evidence file.
    """
    if not isinstance(payload, dict):
        raise MalformedEvidenceError(f"{path.name}: history is not a JSON object")
    events = payload.get("events")
    if not isinstance(events, list) or not events:
        raise MalformedEvidenceError(f"{path.name}: history has no events")
    first = events[0]
    if not isinstance(first, dict):
        raise MalformedEvidenceError(f"{path.name}: first history event is not an object")
    attributes = first.get("workflowExecutionStartedEventAttributes")
    if not isinstance(attributes, dict):
        raise MalformedEvidenceError(
            f"{path.name}: first history event is not WorkflowExecutionStarted, so the "
            "run id cannot be read from it"
        )
    run_id = attributes.get("originalExecutionRunId") or attributes.get("firstExecutionRunId")
    if not isinstance(run_id, str) or not run_id:
        raise MalformedEvidenceError(f"{path.name}: history start event carries no run id")
    return run_id


def executions_in_evidence(payload: Any) -> list[tuple[str | None, str | None]]:
    """``(workflow_id, run_id)`` pairs an evidence payload names.

    Different verification scripts name them differently, which is itself a reason
    to normalise here rather than at each reader.
    """
    if not isinstance(payload, dict):
        return []

    pairs: list[tuple[str | None, str | None]] = []

    def add(workflow_id: Any, run_id: Any) -> None:
        workflow = workflow_id if isinstance(workflow_id, str) and workflow_id else None
        run = run_id if isinstance(run_id, str) and run_id else None
        if workflow or run:
            pairs.append((workflow, run))

    # retry / timeout / durability / smoke evidence
    add(payload.get("workflow_id"), payload.get("run_id"))
    # replay evidence names the history it replayed
    add(payload.get("history_workflow_id"), payload.get("history_run_id"))
    # persistence evidence is keyed by workflow id
    survived = payload.get("survived_workflows") or payload.get("survived")
    if isinstance(survived, dict):
        for workflow_id, detail in survived.items():
            add(workflow_id, detail.get("run_id") if isinstance(detail, dict) else None)
    # evaluation-outcome evidence carries one entry per candidate
    outcomes = payload.get("outcomes")
    if isinstance(outcomes, dict):
        for summary in outcomes.values():
            if isinstance(summary, dict):
                add(summary.get("workflow_id"), summary.get("workflow_run_id"))
    # a reliability report
    run = payload.get("run")
    if isinstance(run, dict):
        add(run.get("workflow_id"), run.get("workflow_run_id"))

    return pairs


def _report_linkage(path: Path, payload: Any) -> dict[str, Any]:
    """Execution linkage for one candidate reliability report."""
    if not isinstance(payload, dict):
        raise MalformedEvidenceError(f"{path.name}: reliability report is not a JSON object")
    run = payload.get("run")
    decision = payload.get("decision")
    if not isinstance(run, dict) or not isinstance(decision, dict):
        raise MalformedEvidenceError(f"{path.name}: reliability report has no run/decision object")
    return {
        "harness_run_id": run.get("run_id"),
        "execution_mode": run.get("execution_mode"),
        "workflow_id": run.get("workflow_id"),
        "workflow_run_id": run.get("workflow_run_id"),
        "candidate_id": (payload.get("verification") or {}).get("candidate_id"),
        "recorded_outcome": decision.get("outcome"),
    }


# ---------------------------------------------------------------------------
# Consistency checks
# ---------------------------------------------------------------------------


def _reconcile_executions(
    observed: list[dict[str, Any]],
    history_run_ids: dict[str, str],
    history_pairs: dict[str, str],
) -> list[dict[str, Any]]:
    """Fold every observation into one execution list, or refuse.

    Two ways this refuses. A workflow id seen with two different run ids means the
    bundle cannot say which execution a piece of evidence describes. A history file
    whose own recorded run id contradicts the evidence that points at it means one
    of the two is lying about what was executed.
    """
    for stem, declared_run_id in history_pairs.items():
        actual = history_run_ids.get(stem)
        if actual is not None and declared_run_id != actual:
            raise MalformedEvidenceError(
                f"{stem}.json records run id {declared_run_id!r} but "
                f"{stem}.history.json contains run id {actual!r}; the evidence and the "
                "history it points at describe different executions"
            )

    by_workflow: dict[str, set[str]] = {}
    by_run: dict[str, set[str]] = {}
    sources: dict[str, set[str]] = {}

    for record in observed:
        workflow_id = record["workflow_id"]
        run_id = record["run_id"]
        source = record["observed_in"]
        if workflow_id:
            by_workflow.setdefault(workflow_id, set())
            sources.setdefault(workflow_id, set()).add(source)
            if run_id:
                by_workflow[workflow_id].add(run_id)
        if run_id:
            by_run.setdefault(run_id, set())
            if workflow_id:
                by_run[run_id].add(workflow_id)

    for workflow_id, run_ids in sorted(by_workflow.items()):
        if len(run_ids) > 1:
            raise AmbiguousWorkflowError(
                f"workflow id {workflow_id!r} is recorded against {len(run_ids)} different "
                f"run ids {sorted(run_ids)} in {sorted(sources[workflow_id])}; the bundle "
                "cannot say which execution the evidence describes"
            )
    for run_id, workflow_ids in sorted(by_run.items()):
        if len(workflow_ids) > 1:
            raise AmbiguousWorkflowError(
                f"run id {run_id!r} is recorded against {len(workflow_ids)} different "
                f"workflow ids {sorted(workflow_ids)}; a run id belongs to exactly one "
                "workflow execution"
            )

    executions = [
        {
            "workflow_id": workflow_id,
            "run_id": next(iter(run_ids)) if run_ids else None,
            "observed_in": sorted(sources.get(workflow_id, set())),
        }
        for workflow_id, run_ids in sorted(by_workflow.items())
    ]
    unattached = sorted(run_id for run_id, workflows in by_run.items() if not workflows)
    executions.extend(
        {"workflow_id": None, "run_id": run_id, "observed_in": []} for run_id in unattached
    )
    return executions


def _reject_self_attestation(payload: Any, path: str = "index") -> None:
    """Refuse to write anything that certifies itself.

    Enforced in code, not left to review, because the whole value of this bundle to
    an external verifier is that the party being verified did not grade it.
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in SELF_ATTESTING_KEYS:
                raise BundleIntegrityError(
                    f"{path}.{key}: the evidence index must not contain self-attesting "
                    "fields. The bundle carries evidence; a verdict is the verifier's "
                    "to reach."
                )
            _reject_self_attestation(value, f"{path}.{key}")
    elif isinstance(payload, list):
        for position, value in enumerate(payload):
            _reject_self_attestation(value, f"{path}[{position}]")


def _cross_check_manifest(manifest: Any, baseline: dict[str, Any], name: str) -> None:
    """The manifest and the frozen baseline must describe the same criteria.

    This is a structural check, not a verdict: it says the two documents disagree
    about *what the criteria are*, which would make any per-criterion linkage in the
    index meaningless. It says nothing about whether a criterion was met.
    """
    if not isinstance(manifest, dict):
        raise MalformedEvidenceError(f"{name}: completion manifest is not a JSON object")
    criteria = manifest.get("criteria")
    if not isinstance(criteria, dict) or not criteria:
        raise MalformedEvidenceError(f"{name}: completion manifest has no criteria")
    expected = set(baseline.get("criteria", {}))
    if expected and set(criteria) != expected:
        missing = sorted(expected - set(criteria))
        extra = sorted(set(criteria) - expected)
        raise MalformedEvidenceError(
            f"{name}: criteria disagree with the frozen baseline "
            f"(missing {missing}, unexpected {extra})"
        )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def load_baseline(path: Path) -> dict[str, Any]:
    baseline = _load_json(path)
    if not isinstance(baseline, dict) or "acceptance_contract" not in baseline:
        raise MalformedEvidenceError(f"{path}: not a Task 2A baseline document")
    return baseline


def export_bundle(
    source_root: Path,
    destination: Path,
    *,
    baseline: dict[str, Any],
    baseline_path: Path | None = None,
    commit_sha: str | None = None,
    github_run_id: str | None = None,
    specs: tuple[EvidenceSpec, ...] = EVIDENCE_SPECS,
) -> dict[str, Any]:
    """Copy raw evidence into ``destination`` and return the index it wrote."""
    source_root = Path(source_root)
    destination = Path(destination)
    if not source_root.is_dir():
        raise MissingEvidenceError(f"no artifact directory at {source_root}")

    entries: list[dict[str, Any]] = []
    absent: list[dict[str, str]] = []
    observed: list[dict[str, Any]] = []
    history_run_ids: dict[str, str] = {}
    history_pairs: dict[str, str] = {}
    missing_linkage: list[dict[str, Any]] = []
    claimed: dict[str, str] = {}
    manifest_payload: Any = None
    manifest_name = ""

    for spec in sorted(specs, key=lambda item: item.logical_name):
        matches = _matching_files(source_root, spec.source)
        if not matches:
            if spec.required:
                raise MissingEvidenceError(
                    f"required evidence '{spec.logical_name}' matched nothing at "
                    f"{source_root / spec.source}. A bundle that silently omits evidence "
                    "understates what is unproven."
                )
            absent.append({"logical_name": spec.logical_name, "expected_source": spec.source})
            continue

        for path in matches:
            bundle_path = _destination_for(spec, source_root, path)
            previous = claimed.get(bundle_path)
            if previous is not None:
                raise BundleIntegrityError(
                    f"two collection rules ('{previous}' and '{spec.logical_name}') both "
                    f"write {bundle_path}; the bundle would hide one of them"
                )
            claimed[bundle_path] = spec.logical_name

            entry: dict[str, Any] = {
                "bundle_path": bundle_path,
                "logical_name": spec.logical_name,
                "category": spec.category,
                "source_system": spec.source_system,
                "kind": spec.kind,
                "source_path": path.relative_to(source_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }

            if spec.kind == "temporal_history":
                stem = path.name[: -len(".history.json")]
                run_id = _history_run_id(path, _load_json(path))
                history_run_ids[stem] = run_id
                entry["run_id"] = run_id
                entry["workflow_id"] = None
                entry["linkage_note"] = (
                    "a serialised history records the run id but not the workflow id; "
                    f"the pairing comes from {stem}.json"
                )
                observed.append(
                    {"workflow_id": None, "run_id": run_id, "observed_in": entry["bundle_path"]}
                )

            elif spec.kind in {"json_evidence", "reliability_report", "completion_manifest"}:
                payload = _load_json(path)
                if spec.kind == "completion_manifest":
                    manifest_payload, manifest_name = payload, path.name
                if spec.kind == "reliability_report":
                    linkage = _report_linkage(path, payload)
                    entry.update(linkage)
                    if linkage["execution_mode"] == "temporal" and not linkage["workflow_id"]:
                        missing_linkage.append(
                            {
                                "bundle_path": bundle_path,
                                "reason": "durable run records no Temporal workflow id",
                            }
                        )
                declared = payload.get("history_artifact") if isinstance(payload, dict) else None
                if isinstance(declared, str) and declared.endswith(".history.json"):
                    stem = Path(declared).name[: -len(".history.json")]
                    declared_run = payload.get("run_id") or payload.get("history_run_id")
                    if isinstance(declared_run, str) and declared_run:
                        history_pairs[stem] = declared_run
                for named_workflow, named_run in executions_in_evidence(payload):
                    observed.append(
                        {
                            "workflow_id": named_workflow,
                            "run_id": named_run,
                            "observed_in": entry["bundle_path"],
                        }
                    )

            entries.append(entry)
            target = destination / bundle_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            copied = sha256_file(target)
            if copied != entry["sha256"]:
                raise ChecksumMismatchError(
                    f"{bundle_path}: copied content hashes to {copied} but the source "
                    f"hashed to {entry['sha256']}"
                )

    if manifest_payload is not None:
        _cross_check_manifest(manifest_payload, baseline, manifest_name)

    if baseline_path is not None and Path(baseline_path).is_file():
        baseline_path = Path(baseline_path)
        bundle_path = f"baseline/{baseline_path.name}"
        target = destination / bundle_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(baseline_path, target)
        entries.append(
            {
                "bundle_path": bundle_path,
                "logical_name": "task-2a-baseline",
                "category": "frozen_baseline",
                "source_system": "repository",
                "kind": "baseline",
                "source_path": baseline_path.name,
                "bytes": baseline_path.stat().st_size,
                "sha256": sha256_file(baseline_path),
            }
        )

    executions = _reconcile_executions(observed, history_run_ids, history_pairs)

    # Back-fill the workflow id onto history entries. A history file cannot name
    # its own workflow, but reconciliation has just established which one owns each
    # run id — recording it here is what lets a verifier go from a history file to
    # the report that describes it without re-deriving the pairing.
    workflow_by_run = {
        execution["run_id"]: execution["workflow_id"]
        for execution in executions
        if execution["run_id"] and execution["workflow_id"]
    }
    for entry in entries:
        if entry.get("kind") != "temporal_history" or entry.get("workflow_id"):
            continue
        owner = workflow_by_run.get(entry.get("run_id"))
        if owner:
            entry["workflow_id"] = owner
            entry["workflow_id_source"] = "paired evidence naming the same run id"

    manifest_commit = None
    manifest_run_id = None
    if isinstance(manifest_payload, dict):
        manifest_commit = manifest_payload.get("repository_commit")
        ci = manifest_payload.get("ci")
        if isinstance(ci, dict):
            manifest_run_id = ci.get("github_run_id")

    resolved_commit = commit_sha or manifest_commit
    resolved_run_id = github_run_id or manifest_run_id

    index = {
        "index_version": BUNDLE_INDEX_VERSION,
        "bundle_kind": "raw_evidence_export",
        "asserts": (
            "Nothing. This index records which files were exported, where each came "
            "from, and what it hashes to. It does not evaluate any criterion. Fields "
            "inside copied evidence were written by the tool that produced that "
            "evidence and are claims to be checked, not findings of this bundle."
        ),
        "provenance": {
            "repository_commit": resolved_commit,
            "repository_commit_source": (
                "argument" if commit_sha else ("completion_manifest" if manifest_commit else None)
            ),
            "github_run_id": resolved_run_id,
            "github_run_id_source": (
                "argument"
                if github_run_id
                else ("completion_manifest" if manifest_run_id else None)
            ),
            "source_root": source_root.name,
        },
        "frozen_baseline": baseline,
        "workflow_executions": executions,
        "entries": sorted(entries, key=lambda item: item["bundle_path"]),
        "missing_optional_evidence": sorted(absent, key=lambda item: item["logical_name"]),
        "missing_execution_linkage": sorted(missing_linkage, key=lambda item: item["bundle_path"]),
        "counts": {
            "entries": len(entries),
            "workflow_executions": len(executions),
            "missing_optional_evidence": len(absent),
            "missing_execution_linkage": len(missing_linkage),
        },
    }

    _reject_self_attestation(index)

    destination.mkdir(parents=True, exist_ok=True)
    (destination / INDEX_FILENAME).write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return index


def verify_bundle(bundle_root: Path) -> list[str]:
    """Recompute every hash in an exported bundle.

    This is what the receiving side runs. Returns the list of files checked;
    raises on the first discrepancy rather than accumulating, because a bundle with
    one broken checksum is already untrustworthy.
    """
    bundle_root = Path(bundle_root)
    index_path = bundle_root / INDEX_FILENAME
    if not index_path.is_file():
        raise MissingEvidenceError(f"no {INDEX_FILENAME} at {bundle_root}")

    index = _load_json(index_path)
    if not isinstance(index, dict) or not isinstance(index.get("entries"), list):
        raise MalformedEvidenceError(f"{index_path}: not an evidence index")

    checked: list[str] = []
    for entry in index["entries"]:
        if not isinstance(entry, dict) or "bundle_path" not in entry or "sha256" not in entry:
            raise MalformedEvidenceError(f"{index_path}: entry without a path or checksum")
        path = bundle_root / entry["bundle_path"]
        if not path.is_file():
            raise MissingEvidenceError(
                f"{entry['bundle_path']}: indexed but absent from the bundle"
            )
        actual = sha256_file(path)
        if actual != entry["sha256"]:
            raise ChecksumMismatchError(
                f"{entry['bundle_path']}: hashes to {actual}, index records {entry['sha256']}"
            )
        checked.append(entry["bundle_path"])
    return checked
