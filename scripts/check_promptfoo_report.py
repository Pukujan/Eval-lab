"""Gate the promptfoo comparison run on its *designed* outcome, not on exit 0.

``promptfoo eval`` exits 100 whenever any assertion fails. In this repository
that is the intended result: ``evals/promptfoo/promptfooconfig.yaml`` runs three
blinded mock identities over the same two tasks, and identity-c
(``mock-minimalist``) proposes only two distinct ``mechanism_class`` values, so
it fails the mechanism-diversity assertion in both tasks. That failure is the
signal the whole comparison exists to produce — an all-green matrix would mean
the assertion no longer discriminates between identities.

The wrong fixes are the tempting ones: ``|| true``, ``continue-on-error``, or
relaxing the diversity assertion. Each of them makes the step green by making it
say nothing. The right fix is to assert the exact expected shape of the outcome,
so the step is green only when the run reproduced it and red for every other
reason — including the reasons a blanket suppression would have hidden, such as
promptfoo crashing before it wrote anything, or the mock provider silently
regressing until a *different* identity is the one that fails.

This script therefore treats "4 passed / 2 failed, and the two failures are
identity-c" as the claim under test, and cross-checks that claim against every
independent place the report states it. The report says the counts three times
over -- aggregate stats, per-result flags, and per-provider metrics -- and any
disagreement between them means the report cannot be trusted to say anything, so
it is a failure in its own right rather than a tie to be broken.

Schema notes, taken from a real 0.121.19 report rather than from the docs:

* ``results.version`` is ``3``;
* ``results.stats`` holds ``successes`` / ``failures`` / ``errors``;
* ``results.results[]`` is one row per (provider, test) with a ``success`` bool,
  a ``gradingResult.pass`` bool, and a ``failureReason`` enum
  (0 = none, 1 = assertion failed, 2 = provider/execution error);
* ``results.prompts[].metrics`` holds ``testPassCount`` / ``testFailCount`` /
  ``testErrorCount`` per provider.

Note that a row failing on an assertion still carries a non-null ``error``
string (it holds the failing assertion's reason), so ``error`` is *not* a signal
of an execution error here -- ``failureReason == 2`` is.

Usage::

    python scripts/check_promptfoo_report.py --report PATH --promptfoo-exit-code N
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# The expected outcome. These are not tuning knobs.
#
# 3 identities x 2 tasks = 6 (provider, test) rows. identity-a (mock-analyst)
# and identity-b (mock-skeptic) each return three distinct mechanism classes and
# pass all six assertions in both tasks: 4 passes. identity-c (mock-minimalist)
# returns only two distinct mechanism classes and therefore fails the
# mechanism-diversity assertion in both tasks: 2 failures.
#
# If you arrived here because CI is red, the number below is almost certainly
# not the thing that changed. Editing it converts a real regression into a green
# tick. Change the counts only alongside a deliberate change to the identities
# or the test matrix in evals/promptfoo/promptfooconfig.yaml, and say so in the
# commit message.
# ---------------------------------------------------------------------------
EXPECTED_PASSES = 4
EXPECTED_FAILURES = 2
EXPECTED_ERRORS = 0
EXPECTED_TOTAL = EXPECTED_PASSES + EXPECTED_FAILURES

# The only identity that is designed to fail. Counts alone are not enough: if
# identity-a regressed and identity-c were quietly loosened, the totals would
# still read 4/2 while meaning the opposite.
EXPECTED_FAILING_LABEL = "identity-c"

# Report envelope version observed in promptfoo 0.121.19. A bump means the paths
# below may have moved, so we stop rather than read a schema we have not looked at.
SUPPORTED_RESULTS_VERSION = 3

# promptfoo exits 0 when everything passed and 100 when at least one assertion
# failed. Any other code (crash, bad config, missing provider) is a real failure
# and must never be swallowed.
PROMPTFOO_EXIT_ALL_PASSED = 0
PROMPTFOO_EXIT_ASSERTIONS_FAILED = 100

# failureReason enum values used by promptfoo's result rows.
FAILURE_REASON_NONE = 0
FAILURE_REASON_ASSERT = 1
FAILURE_REASON_ERROR = 2


class ReportCheckError(Exception):
    """A specific, actionable reason the promptfoo run cannot be accepted."""


def check_exit_code(exit_code: int) -> None:
    """Reject exit codes that mean something other than 'the run completed'."""
    if exit_code not in (PROMPTFOO_EXIT_ALL_PASSED, PROMPTFOO_EXIT_ASSERTIONS_FAILED):
        raise ReportCheckError(
            f"promptfoo exited {exit_code}, which is neither success "
            f"({PROMPTFOO_EXIT_ALL_PASSED}) nor assertions-failed "
            f"({PROMPTFOO_EXIT_ASSERTIONS_FAILED}); the evaluation did not run to "
            "completion, so the report cannot be trusted"
        )
    # Exit 0 would mean nothing failed, which contradicts the designed outcome.
    # Caught here rather than later so the diagnostic names the real surprise.
    if exit_code == PROMPTFOO_EXIT_ALL_PASSED and EXPECTED_FAILURES > 0:
        raise ReportCheckError(
            f"promptfoo exited {PROMPTFOO_EXIT_ALL_PASSED} (everything passed) but "
            f"{EXPECTED_FAILURES} failures are expected by design: "
            f"{EXPECTED_FAILING_LABEL} must fail the mechanism-diversity assertion. "
            "Either an assertion was weakened or the mock identities changed"
        )


def load_report(path: Path) -> dict[str, Any]:
    """Read the report, distinguishing 'absent', 'empty' and 'not JSON'."""
    if not path.is_file():
        raise ReportCheckError(
            f"promptfoo report not found at {path}; the evaluation produced no "
            "output file, so there is nothing to verify"
        )
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        raise ReportCheckError(
            f"promptfoo report at {path} is empty (0 bytes of content); promptfoo "
            "started writing but produced no results"
        )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReportCheckError(
            f"promptfoo report at {path} is not parseable JSON "
            f"(line {exc.lineno}, column {exc.colno}: {exc.msg}); the run was most "
            "likely interrupted mid-write"
        ) from exc
    if not isinstance(parsed, dict):
        raise ReportCheckError(
            f"promptfoo report at {path} is a JSON {type(parsed).__name__}, not an "
            "object; this is not a promptfoo report"
        )
    return parsed


def extract_results(report: dict[str, Any]) -> dict[str, Any]:
    """Locate and shape-check the ``results`` envelope before reading counts."""
    results = report.get("results")
    if not isinstance(results, dict):
        raise ReportCheckError(
            "unrecognised report schema: no top-level 'results' object "
            f"(top-level keys: {sorted(report)})"
        )

    version = results.get("version")
    if version != SUPPORTED_RESULTS_VERSION:
        raise ReportCheckError(
            f"unrecognised report schema: results.version is {version!r}, expected "
            f"{SUPPORTED_RESULTS_VERSION}; the field paths this gate reads may have "
            "moved, so verify them against a real report before bumping this constant"
        )

    stats = results.get("stats")
    if not isinstance(stats, dict):
        raise ReportCheckError(
            "unrecognised report schema: results.stats is missing or not an object"
        )
    for key in ("successes", "failures", "errors"):
        if not isinstance(stats.get(key), int) or isinstance(stats.get(key), bool):
            raise ReportCheckError(
                f"unrecognised report schema: results.stats.{key} is "
                f"{stats.get(key)!r}, expected an integer"
            )

    rows = results.get("results")
    if not isinstance(rows, list):
        raise ReportCheckError(
            "unrecognised report schema: results.results is missing or not a list"
        )
    if not rows:
        raise ReportCheckError(
            "promptfoo report contains zero result rows; the evaluation matrix did not execute"
        )
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ReportCheckError(
                f"unrecognised report schema: results.results[{index}] is a "
                f"{type(row).__name__}, expected an object"
            )
        if not isinstance(row.get("success"), bool):
            raise ReportCheckError(
                f"unrecognised report schema: results.results[{index}].success is "
                f"{row.get('success')!r}, expected a boolean"
            )

    return results


def _row_label(row: dict[str, Any]) -> str:
    provider = row.get("provider")
    if isinstance(provider, dict):
        label = provider.get("label") or provider.get("id")
        if isinstance(label, str):
            return label
    if isinstance(provider, str):
        return provider
    return "<unlabelled provider>"


def check_internal_consistency(results: dict[str, Any]) -> None:
    """Cross-check every independent statement of the counts against the others.

    The report says the same thing three ways. If they disagree, no single one of
    them is authoritative, so the correct action is to refuse the report rather
    than pick a winner.
    """
    stats = results["stats"]
    rows = results["results"]

    stat_successes = int(stats["successes"])
    stat_failures = int(stats["failures"])
    stat_errors = int(stats["errors"])

    # 1. Aggregate stats must account for exactly the rows that exist.
    stats_total = stat_successes + stat_failures + stat_errors
    if stats_total != len(rows):
        raise ReportCheckError(
            f"internally inconsistent report: results.stats accounts for {stats_total} "
            f"outcomes (successes={stat_successes}, failures={stat_failures}, "
            f"errors={stat_errors}) but results.results holds {len(rows)} rows"
        )

    # 2. Per-row flags must reproduce the aggregate.
    row_successes = sum(1 for row in rows if row["success"])
    row_errors = sum(1 for row in rows if row.get("failureReason") == FAILURE_REASON_ERROR)
    row_failures = len(rows) - row_successes - row_errors
    if (row_successes, row_failures, row_errors) != (stat_successes, stat_failures, stat_errors):
        raise ReportCheckError(
            "internally inconsistent report: per-result flags give "
            f"successes={row_successes}, failures={row_failures}, errors={row_errors} "
            f"but results.stats gives successes={stat_successes}, "
            f"failures={stat_failures}, errors={stat_errors}"
        )

    # 3. Each row's own verdict must match its grading result.
    for index, row in enumerate(rows):
        grading = row.get("gradingResult")
        if not isinstance(grading, dict) or not isinstance(grading.get("pass"), bool):
            raise ReportCheckError(
                f"unrecognised report schema: results.results[{index}].gradingResult "
                "is missing a boolean 'pass'"
            )
        if grading["pass"] != row["success"]:
            raise ReportCheckError(
                f"internally inconsistent report: results.results[{index}] "
                f"({_row_label(row)}) reports success={row['success']} but "
                f"gradingResult.pass={grading['pass']}"
            )
        reason = row.get("failureReason")
        expected_reason_is_none = reason == FAILURE_REASON_NONE
        if row["success"] != expected_reason_is_none:
            raise ReportCheckError(
                f"internally inconsistent report: results.results[{index}] "
                f"({_row_label(row)}) reports success={row['success']} but "
                f"failureReason={reason!r} (expected "
                f"{FAILURE_REASON_NONE} for a pass, "
                f"{FAILURE_REASON_ASSERT}/{FAILURE_REASON_ERROR} for a failure)"
            )

    # 4. Per-provider metrics must sum back to the aggregate. Absent metrics are
    #    not an inconsistency -- promptfoo omits them when no assertions ran --
    #    but present ones must agree.
    prompts = results.get("prompts")
    if isinstance(prompts, list):
        metric_rows = [
            prompt.get("metrics")
            for prompt in prompts
            if isinstance(prompt, dict) and isinstance(prompt.get("metrics"), dict)
        ]
        if metric_rows:
            summed_pass = sum(int(m.get("testPassCount", 0)) for m in metric_rows)
            summed_fail = sum(int(m.get("testFailCount", 0)) for m in metric_rows)
            summed_error = sum(int(m.get("testErrorCount", 0)) for m in metric_rows)
            if (summed_pass, summed_fail, summed_error) != (
                stat_successes,
                stat_failures,
                stat_errors,
            ):
                raise ReportCheckError(
                    "internally inconsistent report: results.prompts[].metrics sum to "
                    f"pass={summed_pass}, fail={summed_fail}, error={summed_error} but "
                    f"results.stats gives successes={stat_successes}, "
                    f"failures={stat_failures}, errors={stat_errors}"
                )


def check_expected_outcome(results: dict[str, Any]) -> None:
    """Assert the run reproduced the designed 4-pass / 2-fail comparison."""
    stats = results["stats"]
    rows = results["results"]

    successes = int(stats["successes"])
    failures = int(stats["failures"])
    errors = int(stats["errors"])

    if errors != EXPECTED_ERRORS:
        raise ReportCheckError(
            f"promptfoo recorded {errors} execution error(s); the mock provider path "
            "must never error, so this is a broken harness rather than a failed "
            "assertion"
        )

    if len(rows) != EXPECTED_TOTAL:
        raise ReportCheckError(
            f"promptfoo ran {len(rows)} (provider, test) rows, expected "
            f"{EXPECTED_TOTAL} (3 identities x 2 tasks); the comparison matrix in "
            "promptfooconfig.yaml changed"
        )

    if (successes, failures) != (EXPECTED_PASSES, EXPECTED_FAILURES):
        raise ReportCheckError(
            f"promptfoo produced {successes} passed / {failures} failed, expected "
            f"{EXPECTED_PASSES} passed / {EXPECTED_FAILURES} failed. See the constants "
            "in this script for why those numbers are what they are -- do not edit "
            "them to make CI green"
        )

    failing_labels = sorted(_row_label(row) for row in rows if not row["success"])
    unexpected = sorted(set(failing_labels) - {EXPECTED_FAILING_LABEL})
    if unexpected:
        raise ReportCheckError(
            f"the wrong identities failed: {failing_labels}. Only "
            f"{EXPECTED_FAILING_LABEL!r} is designed to fail (mechanism diversity); a "
            "failure elsewhere means a mock identity or an assertion regressed, even "
            "though the totals still read "
            f"{EXPECTED_PASSES}/{EXPECTED_FAILURES}"
        )
    if len(failing_labels) != EXPECTED_FAILURES:
        raise ReportCheckError(
            f"expected {EXPECTED_FAILURES} failing rows, all from "
            f"{EXPECTED_FAILING_LABEL!r}, but found {len(failing_labels)}: "
            f"{failing_labels}"
        )


def verify(report_path: Path, promptfoo_exit_code: int) -> dict[str, Any]:
    """Run every check in order, cheapest and most-explanatory first."""
    check_exit_code(promptfoo_exit_code)
    report = load_report(report_path)
    results = extract_results(report)
    check_internal_consistency(results)
    check_expected_outcome(results)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help="path to the JSON report written by `promptfoo eval -o`",
    )
    parser.add_argument(
        "--promptfoo-exit-code",
        type=int,
        required=True,
        help="exit status of the promptfoo process (0 = all passed, 100 = assertions failed)",
    )
    args = parser.parse_args(argv)

    try:
        results = verify(args.report, args.promptfoo_exit_code)
    except ReportCheckError as exc:
        # The ::error:: prefix surfaces the reason in the GitHub Actions summary
        # as well as the raw log, so one line covers both readers.
        print(f"::error::promptfoo comparison gate FAILED: {exc}", file=sys.stderr)
        return 1

    stats = results["stats"]
    rows = results["results"]
    print("promptfoo comparison gate PASSED")
    print(f"  promptfoo exit code : {args.promptfoo_exit_code} (assertions-failed is expected)")
    print(f"  report              : {args.report}")
    print(f"  rows                : {len(rows)} (3 identities x 2 tasks)")
    print(f"  passed / failed     : {stats['successes']} / {stats['failures']}")
    for row in rows:
        verdict = "PASS" if row["success"] else "FAIL"
        print(f"    [{verdict}] {_row_label(row)} test #{row.get('testIdx')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
