"""TASK-0062: run telemetry ledger checks.

These run in CI through `pytest tests`:
- the committed ledger and findings are byte-identical to a fresh derivation, so
  the ledger cannot drift from the ``experiments/`` artifacts;
- every committed record validates against ``schemas/run-telemetry.v1.schema.json``;
- keys are unique and sorted;
- nullable metrics are never coerced to zero, floats are copied verbatim;
- all five directory conventions are covered, and run directories without a
  ``results.json`` are recorded as ``partial``/``quarantined`` rather than dropped.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from eval_lab.telemetry import (
    build_records,
    compute_findings,
    dumps_jsonl,
    render_findings,
    sha256_file,
)
from scripts.run_telemetry import FINDINGS_PATH, LEDGER_PATH, ROOT, SCHEMA_PATH, _expected


def _write(root: Path, relative: str, payload: Any) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload), encoding="utf-8")


def _synthetic_tree(root: Path) -> Path:
    experiments = root / "experiments"
    alpha = experiments / "EXP-20260920-001-alpha"
    _write(
        root,
        "experiments/EXP-20260920-001-alpha/results.json",
        {
            "experiment_id": "EXP-20260920-001-alpha",
            "aggregate": {"count": 10, "metrics": {"accuracy": 0.5}},
        },
    )
    _write(
        root,
        "experiments/EXP-20260920-001-alpha/child-one/results.json",
        {"experiment_id": "EXP-20260920-001-alpha", "metrics": {"accuracy": 0.25}},
    )
    _write(
        root,
        "experiments/EXP-20260920-001-alpha/runs/run-a/results.json",
        {
            "experiment_id": "EXP-20260920-001-alpha",
            "run_id": "run-a",
            "provider": "openrouter",
            "metrics": {"accuracy": 0.0, "brier": None},
            "status_counts": {"ok": 5, "provider_error": 1},
        },
    )
    (alpha / "runs" / "run-b").mkdir(parents=True, exist_ok=True)
    (alpha / "runs" / "run-b" / "predictions.jsonl").write_text("", encoding="utf-8")
    _write(
        root,
        "experiments/EXP-20260920-001-alpha/runs/group-1/arm-x/results.json",
        {
            "experiment_id": "EXP-20260920-001-alpha",
            "run_id": "arm-x",
            "correct_count": 3,
            "resolved_count": 4,
        },
    )
    _write(
        root,
        "experiments/EXP-20260920-001-alpha/diagnostics/diag-1/results.json",
        {
            "experiment_id": "EXP-20260920-001-alpha",
            "arms": {"a": {"accuracy": 0.1}, "b": {"accuracy": 0.2}},
        },
    )
    (experiments / "EXP-20260921-002-beta/runs/paused-run").mkdir(parents=True, exist_ok=True)
    (experiments / "EXP-20260921-002-beta/runs/paused-run" / "predictions.jsonl").write_text(
        "", encoding="utf-8"
    )
    return root


def _rows(root: Path) -> list[dict[str, Any]]:
    return build_records(root)


def test_all_directory_conventions_are_covered(tmp_path: Path) -> None:
    rows = _rows(_synthetic_tree(tmp_path))
    by_scope = {row["run_path"]: row["scope"] for row in rows}
    assert by_scope["experiments/EXP-20260920-001-alpha"] == "experiment"
    assert by_scope["experiments/EXP-20260920-001-alpha/child-one"] == "child_run"
    assert by_scope["experiments/EXP-20260920-001-alpha/runs/run-a"] == "run"
    assert by_scope["experiments/EXP-20260920-001-alpha/runs/group-1/arm-x"] == "nested_run"
    assert by_scope["experiments/EXP-20260920-001-alpha/diagnostics/diag-1"] == "diagnostic"


def test_container_directory_is_not_a_row(tmp_path: Path) -> None:
    rows = _rows(_synthetic_tree(tmp_path))
    paths = {row["run_path"] for row in rows}
    assert "experiments/EXP-20260920-001-alpha/runs/group-1" not in paths


def test_missing_results_are_recorded_not_dropped(tmp_path: Path) -> None:
    rows = _rows(_synthetic_tree(tmp_path))
    by_path = {row["run_path"]: row for row in rows}
    run_b = by_path["experiments/EXP-20260920-001-alpha/runs/run-b"]
    assert run_b["has_results"] is False
    assert run_b["completeness"] == "partial"
    assert run_b["results_sha256"] is None
    paused = by_path["experiments/EXP-20260921-002-beta/runs/paused-run"]
    assert paused["completeness"] == "quarantined"


def test_nullable_metrics_are_not_coerced(tmp_path: Path) -> None:
    rows = _rows(_synthetic_tree(tmp_path))
    by_path = {row["run_path"]: row for row in rows}
    run_a = by_path["experiments/EXP-20260920-001-alpha/runs/run-a"]
    assert run_a["accuracy"] == 0.0  # a real zero survives
    assert run_a["record_count"] is None  # absent stays absent
    assert run_a["status_counts"] == {"ok": 5, "provider_error": 1}


def test_accuracy_resolution_sources(tmp_path: Path) -> None:
    rows = _rows(_synthetic_tree(tmp_path))
    by_path = {row["run_path"]: row for row in rows}
    alpha = by_path["experiments/EXP-20260920-001-alpha"]
    assert alpha["accuracy"] == 0.5
    assert alpha["accuracy_source"] == "aggregate.metrics.accuracy"
    child = by_path["experiments/EXP-20260920-001-alpha/child-one"]
    assert child["accuracy_source"] == "metrics.accuracy"
    arm = by_path["experiments/EXP-20260920-001-alpha/runs/group-1/arm-x"]
    assert arm["accuracy"] == 0.75
    assert arm["accuracy_source"] == "correct_count/resolved_count"
    diag = by_path["experiments/EXP-20260920-001-alpha/diagnostics/diag-1"]
    assert diag["accuracy"] is None  # arms-only runs are not flattened
    assert diag["structure"]["has_arms"] is True
    assert diag["structure"]["arms_count"] == 2


def test_malformed_results_is_quarantined(tmp_path: Path) -> None:
    tree = _synthetic_tree(tmp_path)
    bad = tree / "experiments/EXP-20260920-001-alpha/runs/run-a/results.json"
    bad.write_text("{not json", encoding="utf-8")
    by_path = {row["run_path"]: row for row in _rows(tree)}
    record = by_path["experiments/EXP-20260920-001-alpha/runs/run-a"]
    assert record["has_results"] is True
    assert record["completeness"] == "quarantined"
    assert record["results_sha256"] is not None


def test_keys_unique_and_sorted(tmp_path: Path) -> None:
    rows = _rows(_synthetic_tree(tmp_path))
    keys = [row["run_path"] for row in rows]
    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys)


def test_derivation_is_byte_deterministic(tmp_path: Path) -> None:
    tree = _synthetic_tree(tmp_path)
    assert dumps_jsonl(build_records(tree)) == dumps_jsonl(build_records(tree))


def test_findings_are_derived_from_records(tmp_path: Path) -> None:
    rows = _rows(_synthetic_tree(tmp_path))
    findings = compute_findings(rows)
    assert findings["totals"]["rows"] == len(rows)
    assert findings["totals"]["with_results"] == sum(1 for row in rows if row["has_results"])
    markdown = render_findings(rows)
    assert f"| run units | {len(rows)} |" in markdown


def test_sha256_file_is_line_ending_insensitive(tmp_path: Path) -> None:
    lf = tmp_path / "lf.json"
    crlf = tmp_path / "crlf.json"
    lf.write_bytes(b'{"a": 1}\n')
    crlf.write_bytes(b'{"a": 1}\r\n')
    assert sha256_file(lf) == sha256_file(crlf)


def test_committed_ledger_is_current() -> None:
    expected_ledger, expected_findings = _expected()
    ledger = (ROOT / LEDGER_PATH).read_text(encoding="utf-8").replace("\r\n", "\n")
    findings = (ROOT / FINDINGS_PATH).read_text(encoding="utf-8").replace("\r\n", "\n")
    assert ledger == expected_ledger
    assert findings == expected_findings


def test_committed_ledger_validates_against_schema() -> None:
    schema = json.loads((ROOT / SCHEMA_PATH).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    records = [
        json.loads(line)
        for line in (ROOT / LEDGER_PATH).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert records
    for record in records:
        validator.validate(record)
