"""Export integrity for the raw-evidence bundle.

These tests cover exactly one property: that a bundle handed to an external
verifier is either trustworthy or absent. They do **not** test whether any
criterion was met — nothing in this repository is allowed to answer that, and a
test here that graded evidence would be the circular verification the whole
arrangement exists to avoid.

Four failure modes, each fatal:

* a required file is missing — a bundle that silently omits evidence understates
  what is unproven;
* a checksum does not match — the file is not the one that was hashed;
* a workflow id maps to two run ids — the bundle cannot say which execution its
  evidence describes;
* evidence is malformed — unparseable, or self-contradictory about what ran.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from app.evidence.bundle import (
    EVIDENCE_SPECS,
    INDEX_FILENAME,
    SELF_ATTESTING_KEYS,
    AmbiguousWorkflowError,
    BundleIntegrityError,
    ChecksumMismatchError,
    MalformedEvidenceError,
    MissingEvidenceError,
    export_bundle,
    load_baseline,
    verify_bundle,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPOSITORY_ROOT / "verification" / "task-2a-baseline.json"

WORKFLOW_ID = "durable-checkpoint-1"
RUN_ID = "11111111-1111-1111-1111-111111111111"
SMOKE_WORKFLOW_ID = "coding-evaluation-smoke-1"
SMOKE_RUN_ID = "22222222-2222-2222-2222-222222222222"


def _history(run_id: str) -> dict[str, Any]:
    """The shape ``WorkflowHistory.to_json_dict()`` produces.

    Note what is *not* here: a workflow id. The SDK omits it, which is why a
    history file has to be paired back to its evidence rather than read alone.
    """
    return {
        "events": [
            {
                "eventId": "1",
                "eventType": "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED",
                "workflowExecutionStartedEventAttributes": {"originalExecutionRunId": run_id},
            },
            {"eventId": "2", "eventType": "EVENT_TYPE_WORKFLOW_EXECUTION_COMPLETED"},
        ]
    }


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


@pytest.fixture
def baseline() -> dict[str, Any]:
    return load_baseline(BASELINE_PATH)


@pytest.fixture
def source(tmp_path: Path, baseline: dict[str, Any]) -> Path:
    """A minimal but complete artifact directory, as CI would produce."""
    root = tmp_path / "artifacts"
    evidence = root / "evidence"

    _write(evidence / "durability-recovery.history.json", _history(RUN_ID))
    _write(evidence / "workflow-smoke.history.json", _history(SMOKE_RUN_ID))

    _write(
        evidence / "durability-recovery.json",
        {
            "claim": "worker loss survived",
            "workflow_id": WORKFLOW_ID,
            "run_id": RUN_ID,
            "history_artifact": "/home/runner/work/artifacts/evidence/"
            "durability-recovery.history.json",
        },
    )
    _write(
        evidence / "workflow-smoke.json",
        {
            "claim": "coding workflow executed",
            "workflow_id": SMOKE_WORKFLOW_ID,
            "run_id": SMOKE_RUN_ID,
            "verified": True,
            "history_artifact": "/home/runner/work/artifacts/evidence/workflow-smoke.history.json",
        },
    )
    _write(
        evidence / "retry-behaviour.json",
        {"workflow_id": "retry-probe-1", "run_id": "33333333-3333-3333-3333-333333333333"},
    )
    _write(
        evidence / "timeout-behaviour.json",
        {"workflow_id": "timeout-probe-1", "run_id": "44444444-4444-4444-4444-444444444444"},
    )
    _write(
        evidence / "replay-determinism.json",
        {"history_workflow_id": WORKFLOW_ID, "history_run_id": RUN_ID},
    )
    _write(evidence / "phoenix-trace.json", {"trace_count": 2, "missing_spans": []})
    _write(evidence / "evaluation-outcomes.json", {"outcomes": {}})
    _write(evidence / "compose-verification-clean.json", {"health": {}})
    _write(evidence / "persistence-across-restart.json", {"survived": {}})
    _write(evidence / "pin-verification.json", {"problems": []})

    _write(
        root / "reports" / "reliability-report-C-claim.json",
        {
            "run": {
                "run_id": "run-abc",
                "execution_mode": "temporal",
                "workflow_id": SMOKE_WORKFLOW_ID,
                "workflow_run_id": SMOKE_RUN_ID,
            },
            "decision": {"outcome": "accepted_for_review"},
            "verification": {"candidate_id": "C-claim"},
        },
    )
    _write(root / "reports" / "promptfoo-report.json", {"results": []})
    _write(root / "reports" / "inspect-logs" / "eval.json", {"samples": []})
    (root / "logs" / "containers").mkdir(parents=True, exist_ok=True)
    (root / "logs" / "containers" / "temporal.log").write_text("started\n", encoding="utf-8")

    _write(
        root / "completion-manifest.json",
        {
            "manifest_version": 2,
            "repository_commit": "a1017b24de9738dc576da3ded2d2d82d23bef47c",
            "ci": {"github_run_id": "30580082420"},
            "criteria": dict.fromkeys(baseline["criteria"], {"status": "demonstrated"}),
        },
    )
    return root


def _export(source: Path, destination: Path, baseline: dict[str, Any]) -> dict[str, Any]:
    return export_bundle(source, destination, baseline=baseline, baseline_path=BASELINE_PATH)


# ---------------------------------------------------------------------------
# The happy path, only far enough to make the failure tests meaningful
# ---------------------------------------------------------------------------


def test_export_writes_an_index_and_verifies(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    destination = tmp_path / "bundle"
    index = _export(source, destination, baseline)

    assert (destination / INDEX_FILENAME).is_file()
    assert index["counts"]["entries"] == len(index["entries"])
    assert verify_bundle(destination)

    paths = {entry["bundle_path"] for entry in index["entries"]}
    assert "temporal/histories/durability-recovery.history.json" in paths
    assert "reports/reliability-report-C-claim.json" in paths
    assert "logs/containers/temporal.log" in paths
    assert "promptfoo/promptfoo-report.json" in paths
    assert "inspect/eval.json" in paths


def test_every_entry_carries_source_system_and_checksum(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    index = _export(source, tmp_path / "bundle", baseline)
    for entry in index["entries"]:
        assert entry["source_system"]
        assert len(entry["sha256"]) == 64
        assert entry["source_path"]
    assert index["provenance"]["repository_commit"].startswith("a1017b2")
    assert index["provenance"]["repository_commit_source"] == "completion_manifest"


def test_export_is_deterministic(source: Path, tmp_path: Path, baseline: dict[str, Any]) -> None:
    """Byte-identical, or the digest of a bundle means nothing."""
    first = tmp_path / "one"
    second = tmp_path / "two"
    _export(source, first, baseline)
    _export(source, second, baseline)
    assert (first / INDEX_FILENAME).read_bytes() == (second / INDEX_FILENAME).read_bytes()


def test_candidate_reports_carry_both_temporal_identifiers(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    index = _export(source, tmp_path / "bundle", baseline)
    report = next(
        entry for entry in index["entries"] if entry["category"] == "candidate_reliability_report"
    )
    assert report["workflow_id"] == SMOKE_WORKFLOW_ID
    assert report["workflow_run_id"] == SMOKE_RUN_ID
    assert index["counts"]["missing_execution_linkage"] == 0


def test_histories_are_linked_back_to_their_workflow_id(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    """A history cannot name its own workflow; the pairing has to be recorded."""
    index = _export(source, tmp_path / "bundle", baseline)
    history = next(
        entry
        for entry in index["entries"]
        if entry["bundle_path"].endswith("durability-recovery.history.json")
    )
    assert history["run_id"] == RUN_ID
    assert history["workflow_id"] == WORKFLOW_ID
    assert "paired evidence" in history["workflow_id_source"]


def test_a_durable_report_without_a_workflow_id_is_recorded_as_a_gap(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    """Absent linkage is visible, not fatal — old reports predate the field."""
    path = source / "reports" / "reliability-report-C-claim.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["run"]["workflow_id"] = None
    payload["run"]["workflow_run_id"] = None
    _write(path, payload)

    index = _export(source, tmp_path / "bundle", baseline)
    assert index["counts"]["missing_execution_linkage"] == 1


# ---------------------------------------------------------------------------
# 1. missing files fail the export
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "removed",
    [
        "evidence/durability-recovery.json",
        "evidence/retry-behaviour.json",
        "evidence/phoenix-trace.json",
        "reports/promptfoo-report.json",
        "completion-manifest.json",
    ],
)
def test_missing_required_evidence_fails_the_export(
    source: Path, tmp_path: Path, baseline: dict[str, Any], removed: str
) -> None:
    (source / removed).unlink()
    with pytest.raises(MissingEvidenceError, match="matched nothing"):
        _export(source, tmp_path / "bundle", baseline)


def test_an_absent_source_directory_fails(tmp_path: Path, baseline: dict[str, Any]) -> None:
    with pytest.raises(MissingEvidenceError):
        _export(tmp_path / "nothing-here", tmp_path / "bundle", baseline)


def test_absent_optional_evidence_is_recorded_rather_than_dropped(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    index = _export(source, tmp_path / "bundle", baseline)
    absent = {item["logical_name"] for item in index["missing_optional_evidence"]}
    assert "compose-verification-restart" in absent
    assert index["counts"]["missing_optional_evidence"] == len(absent)


def test_an_indexed_file_deleted_from_the_bundle_fails_verification(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    destination = tmp_path / "bundle"
    _export(source, destination, baseline)
    (destination / "phoenix" / "phoenix-trace.json").unlink()
    with pytest.raises(MissingEvidenceError, match="absent from the bundle"):
        verify_bundle(destination)


# ---------------------------------------------------------------------------
# 2. checksum mismatch fails
# ---------------------------------------------------------------------------


def test_a_tampered_file_fails_verification(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    destination = tmp_path / "bundle"
    _export(source, destination, baseline)

    target = destination / "phoenix" / "phoenix-trace.json"
    target.write_text(json.dumps({"trace_count": 999}), encoding="utf-8")

    with pytest.raises(ChecksumMismatchError, match="phoenix-trace.json"):
        verify_bundle(destination)


def test_an_edited_checksum_in_the_index_fails_verification(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    """Editing the index instead of the file must not rescue it either."""
    destination = tmp_path / "bundle"
    _export(source, destination, baseline)

    index_path = destination / INDEX_FILENAME
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["entries"][0]["sha256"] = "0" * 64
    _write(index_path, index)

    with pytest.raises(ChecksumMismatchError):
        verify_bundle(destination)


def test_verification_needs_an_index(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    with pytest.raises(MissingEvidenceError, match=INDEX_FILENAME):
        verify_bundle(tmp_path / "empty")


# ---------------------------------------------------------------------------
# 3. duplicate or ambiguous workflow ids fail
# ---------------------------------------------------------------------------


def test_one_workflow_id_with_two_run_ids_fails(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    _write(
        source / "evidence" / "retry-behaviour.json",
        {"workflow_id": WORKFLOW_ID, "run_id": "99999999-9999-9999-9999-999999999999"},
    )
    with pytest.raises(AmbiguousWorkflowError, match="different"):
        _export(source, tmp_path / "bundle", baseline)


def test_one_run_id_shared_by_two_workflow_ids_fails(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    _write(
        source / "evidence" / "retry-behaviour.json",
        {"workflow_id": "some-other-workflow", "run_id": RUN_ID},
    )
    with pytest.raises(AmbiguousWorkflowError):
        _export(source, tmp_path / "bundle", baseline)


def test_a_history_contradicting_its_evidence_fails(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    """The evidence says one execution, the history it points at says another."""
    _write(
        source / "evidence" / "durability-recovery.history.json",
        _history("55555555-5555-5555-5555-555555555555"),
    )
    with pytest.raises(MalformedEvidenceError, match="different executions"):
        _export(source, tmp_path / "bundle", baseline)


# ---------------------------------------------------------------------------
# 4. malformed evidence fails
# ---------------------------------------------------------------------------


def test_unparseable_evidence_fails(source: Path, tmp_path: Path, baseline: dict[str, Any]) -> None:
    _write(source / "evidence" / "retry-behaviour.json", "{not json at all")
    with pytest.raises(MalformedEvidenceError, match="not readable as JSON"):
        _export(source, tmp_path / "bundle", baseline)


def test_a_history_with_no_events_fails(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    _write(source / "evidence" / "workflow-smoke.history.json", {"events": []})
    with pytest.raises(MalformedEvidenceError, match="no events"):
        _export(source, tmp_path / "bundle", baseline)


def test_a_history_whose_first_event_is_not_a_start_fails(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    _write(
        source / "evidence" / "workflow-smoke.history.json",
        {"events": [{"eventId": "1", "eventType": "EVENT_TYPE_ACTIVITY_TASK_COMPLETED"}]},
    )
    with pytest.raises(MalformedEvidenceError, match="WorkflowExecutionStarted"):
        _export(source, tmp_path / "bundle", baseline)


def test_a_reliability_report_without_a_run_object_fails(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    _write(source / "reports" / "reliability-report-C-claim.json", {"decision": {}})
    with pytest.raises(MalformedEvidenceError, match="run/decision"):
        _export(source, tmp_path / "bundle", baseline)


def test_a_manifest_disagreeing_with_the_baseline_criteria_fails(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    """Not a verdict: the two documents disagree about what the criteria *are*."""
    manifest_path = source / "completion-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["criteria"].pop("timeout_behaviour")
    manifest["criteria"]["invented_criterion"] = {"status": "demonstrated"}
    _write(manifest_path, manifest)

    with pytest.raises(MalformedEvidenceError, match="disagree with the frozen baseline"):
        _export(source, tmp_path / "bundle", baseline)


def test_a_baseline_that_is_not_a_baseline_fails(tmp_path: Path) -> None:
    path = tmp_path / "not-a-baseline.json"
    _write(path, {"hello": "world"})
    with pytest.raises(MalformedEvidenceError, match="not a Task 2A baseline"):
        load_baseline(path)


# ---------------------------------------------------------------------------
# The exporter must not certify its own output
# ---------------------------------------------------------------------------


def test_the_index_contains_no_self_attesting_field(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    """A bundle that grades itself is worth nothing to the party receiving it."""
    destination = tmp_path / "bundle"
    _export(source, destination, baseline)
    index = json.loads((destination / INDEX_FILENAME).read_text(encoding="utf-8"))

    offenders: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in SELF_ATTESTING_KEYS:
                    offenders.append(f"{path}.{key}")
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for position, value in enumerate(node):
                walk(value, f"{path}[{position}]")

    walk(index, "index")
    assert not offenders, f"the evidence index attests to its own result at {offenders}"


def test_copied_evidence_keeps_producer_written_fields(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    """The counterpart to the test above, and the reason it is scoped to the index.

    ``workflow-smoke.json`` contains ``"verified": true`` because the script that
    produced it wrote that. Stripping it would change the bytes and make the
    recorded hash uncheckable against the source artifact. It survives, as a claim
    by the producer rather than a finding of the bundle.
    """
    destination = tmp_path / "bundle"
    _export(source, destination, baseline)
    copied = destination / "temporal" / "evidence" / "workflow-smoke.json"
    assert json.loads(copied.read_text(encoding="utf-8"))["verified"] is True
    assert copied.read_bytes() == (source / "evidence" / "workflow-smoke.json").read_bytes()


def test_two_rules_writing_the_same_path_would_fail(
    source: Path, tmp_path: Path, baseline: dict[str, Any]
) -> None:
    """A collision would hide one file behind another; refuse instead."""
    shadow = dataclasses.replace(EVIDENCE_SPECS[1], logical_name="zz-shadowing-rule")
    colliding = (*EVIDENCE_SPECS, shadow)
    with pytest.raises(BundleIntegrityError, match="both write"):
        export_bundle(
            source,
            tmp_path / "bundle",
            baseline=baseline,
            baseline_path=BASELINE_PATH,
            specs=colliding,
        )
