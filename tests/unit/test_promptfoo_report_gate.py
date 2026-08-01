"""Tests for the promptfoo comparison gate.

The gate exists so that a step which *must* tolerate a non-zero exit code still
fails for every real reason. That only holds if each rejection path is exercised,
so every failure mode gets its own test and every test asserts on the diagnostic
text -- a gate that fails with the wrong reason sends the next person down the
wrong trail.

Fixtures are built inline from the shape of a real promptfoo 0.121.19 report.
Nothing here runs promptfoo, node or the network: these tests must stay runnable
on a machine that has never installed any of them.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_promptfoo_report import (
    EXPECTED_FAILURES,
    EXPECTED_PASSES,
    PROMPTFOO_EXIT_ALL_PASSED,
    PROMPTFOO_EXIT_ASSERTIONS_FAILED,
    SUPPORTED_RESULTS_VERSION,
    ReportCheckError,
    main,
    verify,
)

FAILING_LABEL = "identity-c"
PASSING_LABELS = ("identity-a", "identity-b")


def _row(label: str, test_index: int, *, success: bool, failure_reason: int | None = None) -> dict:
    """One (provider, test) row, matching the fields the gate actually reads."""
    if failure_reason is None:
        failure_reason = 0 if success else 1
    return {
        "provider": {"id": "file://provider_bridge.py", "label": label},
        "testIdx": test_index,
        "promptIdx": 0,
        "success": success,
        "failureReason": failure_reason,
        "score": 1.0 if success else 0.94,
        "gradingResult": {
            "pass": success,
            "score": 1.0 if success else 0.94,
            "reason": "All assertions passed" if success else "2 distinct mechanism classes",
        },
    }


def _report(
    *,
    rows: list[dict] | None = None,
    successes: int | None = None,
    failures: int | None = None,
    errors: int = 0,
    version: object = SUPPORTED_RESULTS_VERSION,
    include_prompt_metrics: bool = True,
    prompt_metrics: list[dict] | None = None,
) -> dict:
    """A full report envelope, defaulting to the designed 4-pass / 2-fail run."""
    if rows is None:
        rows = []
        for test_index in (0, 1):
            rows.append(_row(FAILING_LABEL, test_index, success=False))
            for label in PASSING_LABELS:
                rows.append(_row(label, test_index, success=True))

    if successes is None:
        successes = sum(1 for row in rows if row["success"])
    if failures is None:
        failures = len(rows) - successes - errors

    prompts: list[dict] = []
    if include_prompt_metrics:
        if prompt_metrics is None:
            prompt_metrics = []
            for label in (*PASSING_LABELS, FAILING_LABEL):
                passed = sum(1 for r in rows if r["success"] and r["provider"]["label"] == label)
                failed = sum(
                    1 for r in rows if not r["success"] and r["provider"]["label"] == label
                )
                prompt_metrics.append(
                    {"testPassCount": passed, "testFailCount": failed, "testErrorCount": 0}
                )
        prompts = [{"label": "prompt", "metrics": metrics} for metrics in prompt_metrics]

    return {
        "evalId": "eval-test-0000",
        "results": {
            "version": version,
            "timestamp": "2026-08-01T00:00:00.000Z",
            "prompts": prompts,
            "results": rows,
            "stats": {"successes": successes, "failures": failures, "errors": errors},
        },
        "config": {},
    }


def _write(tmp_path: Path, payload: object, name: str = "promptfoo-report.json") -> Path:
    path = tmp_path / name
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# -- the designed outcome is accepted ---------------------------------------


def test_designed_four_two_report_passes(tmp_path: Path) -> None:
    path = _write(tmp_path, _report())
    results = verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)
    assert results["stats"]["successes"] == EXPECTED_PASSES
    assert results["stats"]["failures"] == EXPECTED_FAILURES


def test_designed_outcome_exits_zero_through_main(tmp_path: Path) -> None:
    path = _write(tmp_path, _report())
    exit_code = main(
        ["--report", str(path), "--promptfoo-exit-code", str(PROMPTFOO_EXIT_ASSERTIONS_FAILED)]
    )
    assert exit_code == 0


def test_report_without_prompt_metrics_still_passes(tmp_path: Path) -> None:
    # promptfoo omits per-prompt metrics in some modes; their absence must not be
    # treated as an inconsistency, only a disagreement must.
    path = _write(tmp_path, _report(include_prompt_metrics=False))
    assert verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


# -- wrong counts ------------------------------------------------------------


def test_wrong_counts_fail(tmp_path: Path) -> None:
    rows = [_row(label, 0, success=True) for label in (*PASSING_LABELS, FAILING_LABEL)]
    rows += [_row(label, 1, success=True) for label in (*PASSING_LABELS, FAILING_LABEL)]
    path = _write(tmp_path, _report(rows=rows))
    with pytest.raises(ReportCheckError, match="6 passed / 0 failed"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_too_few_rows_fail(tmp_path: Path) -> None:
    rows = [_row(FAILING_LABEL, 0, success=False), _row("identity-a", 0, success=True)]
    path = _write(tmp_path, _report(rows=rows))
    with pytest.raises(ReportCheckError, match="ran 2 .*rows, expected 6"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_right_counts_but_wrong_identity_fails(tmp_path: Path) -> None:
    # The sharpest case: totals still read 4/2, but identity-a is failing and
    # identity-c has stopped failing. Counting alone would call this green.
    rows = [
        _row("identity-a", 0, success=False),
        _row("identity-b", 0, success=True),
        _row(FAILING_LABEL, 0, success=True),
        _row("identity-a", 1, success=False),
        _row("identity-b", 1, success=True),
        _row(FAILING_LABEL, 1, success=True),
    ]
    path = _write(tmp_path, _report(rows=rows))
    with pytest.raises(ReportCheckError, match="wrong identities failed"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_execution_errors_fail(tmp_path: Path) -> None:
    rows = [
        _row(FAILING_LABEL, 0, success=False, failure_reason=2),
        _row(FAILING_LABEL, 1, success=False),
        *[_row(label, 0, success=True) for label in PASSING_LABELS],
        *[_row(label, 1, success=True) for label in PASSING_LABELS],
    ]
    path = _write(
        tmp_path,
        _report(
            rows=rows,
            successes=4,
            failures=1,
            errors=1,
            prompt_metrics=[
                {"testPassCount": 2, "testFailCount": 0, "testErrorCount": 0},
                {"testPassCount": 2, "testFailCount": 0, "testErrorCount": 0},
                {"testPassCount": 0, "testFailCount": 1, "testErrorCount": 1},
            ],
        ),
    )
    with pytest.raises(ReportCheckError, match="execution error"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


# -- missing, empty, malformed ----------------------------------------------


def test_missing_report_fails(tmp_path: Path) -> None:
    with pytest.raises(ReportCheckError, match="report not found"):
        verify(tmp_path / "nope.json", PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_missing_report_exits_nonzero_through_main(tmp_path: Path) -> None:
    exit_code = main(
        [
            "--report",
            str(tmp_path / "nope.json"),
            "--promptfoo-exit-code",
            str(PROMPTFOO_EXIT_ASSERTIONS_FAILED),
        ]
    )
    assert exit_code == 1


def test_empty_report_fails(tmp_path: Path) -> None:
    path = _write(tmp_path, "   \n")
    with pytest.raises(ReportCheckError, match="is empty"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_malformed_json_fails(tmp_path: Path) -> None:
    path = _write(tmp_path, '{"results": {"stats": {"successes": 4,')
    with pytest.raises(ReportCheckError, match="not parseable JSON"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_json_array_is_not_a_report(tmp_path: Path) -> None:
    path = _write(tmp_path, [1, 2, 3])
    with pytest.raises(ReportCheckError, match="not an object"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


# -- unrecognised schema -----------------------------------------------------


def test_missing_results_object_fails(tmp_path: Path) -> None:
    path = _write(tmp_path, {"evalId": "eval-x", "config": {}})
    with pytest.raises(ReportCheckError, match="no top-level 'results' object"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_unknown_results_version_fails(tmp_path: Path) -> None:
    path = _write(tmp_path, _report(version=SUPPORTED_RESULTS_VERSION + 1))
    with pytest.raises(ReportCheckError, match="results.version is 4"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_missing_stats_fails(tmp_path: Path) -> None:
    payload = _report()
    del payload["results"]["stats"]
    path = _write(tmp_path, payload)
    with pytest.raises(ReportCheckError, match="results.stats is missing"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_non_integer_stat_fails(tmp_path: Path) -> None:
    payload = _report()
    payload["results"]["stats"]["successes"] = "4"
    path = _write(tmp_path, payload)
    with pytest.raises(ReportCheckError, match="results.stats.successes is"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_missing_result_rows_fails(tmp_path: Path) -> None:
    payload = _report()
    del payload["results"]["results"]
    path = _write(tmp_path, payload)
    with pytest.raises(ReportCheckError, match="results.results is missing"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_zero_result_rows_fails(tmp_path: Path) -> None:
    path = _write(tmp_path, _report(rows=[], successes=0, failures=0))
    with pytest.raises(ReportCheckError, match="zero result rows"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_row_without_boolean_success_fails(tmp_path: Path) -> None:
    payload = _report()
    payload["results"]["results"][0]["success"] = "no"
    path = _write(tmp_path, payload)
    with pytest.raises(ReportCheckError, match=r"results\.results\[0\]\.success is"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_row_without_grading_result_fails(tmp_path: Path) -> None:
    payload = _report()
    del payload["results"]["results"][0]["gradingResult"]
    path = _write(tmp_path, payload)
    with pytest.raises(ReportCheckError, match="gradingResult"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


# -- internal inconsistency --------------------------------------------------


def test_stats_disagreeing_with_row_count_fails(tmp_path: Path) -> None:
    path = _write(tmp_path, _report(successes=4, failures=3))
    with pytest.raises(ReportCheckError, match="accounts for 7 outcomes"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_stats_disagreeing_with_row_flags_fails(tmp_path: Path) -> None:
    # Totals still add up to six rows, but the split is inverted relative to the
    # per-row flags -- exactly the case a naive stats-only reader would miss.
    path = _write(tmp_path, _report(successes=2, failures=4))
    with pytest.raises(ReportCheckError, match="per-result flags give"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_grading_result_disagreeing_with_success_fails(tmp_path: Path) -> None:
    payload = _report()
    payload["results"]["results"][0]["gradingResult"]["pass"] = True
    path = _write(tmp_path, payload)
    with pytest.raises(ReportCheckError, match="gradingResult.pass=True"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_failure_reason_disagreeing_with_success_fails(tmp_path: Path) -> None:
    payload = _report()
    for row in payload["results"]["results"]:
        if row["success"]:
            row["failureReason"] = 1
            break
    path = _write(tmp_path, payload)
    with pytest.raises(ReportCheckError, match="failureReason=1"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


def test_prompt_metrics_disagreeing_with_stats_fails(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        _report(
            prompt_metrics=[
                {"testPassCount": 2, "testFailCount": 0, "testErrorCount": 0},
                {"testPassCount": 2, "testFailCount": 0, "testErrorCount": 0},
                {"testPassCount": 2, "testFailCount": 0, "testErrorCount": 0},
            ]
        ),
    )
    with pytest.raises(ReportCheckError, match=r"results\.prompts\[\]\.metrics sum to"):
        verify(path, PROMPTFOO_EXIT_ASSERTIONS_FAILED)


# -- exit-code handling ------------------------------------------------------


def test_unexpected_exit_code_fails_before_reading_report(tmp_path: Path) -> None:
    # No report is written at all: the exit-code check must fire first and name
    # the crash rather than blaming the missing file.
    with pytest.raises(ReportCheckError, match="exited 1, which is neither"):
        verify(tmp_path / "absent.json", 1)


def test_all_passed_exit_code_fails(tmp_path: Path) -> None:
    path = _write(tmp_path, _report())
    with pytest.raises(ReportCheckError, match="everything passed"):
        verify(path, PROMPTFOO_EXIT_ALL_PASSED)
