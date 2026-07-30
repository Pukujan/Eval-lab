"""Build and test a patched working copy.

Everything here returns a fact a machine read off a process: an exit code, a count,
a path set. No judgement is formed at this layer — that is the gates' job
(ADR-0009), and keeping the two apart is what makes the gates unit-testable
without ever running a subprocess.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from app.activities.probes import concurrent_delivery_probe, scrubbed_environment
from app.config import FIXTURE_ROOT
from app.domain.schemas import VerificationResult

BUILD_TIMEOUT_SECONDS = 120
TEST_TIMEOUT_SECONDS = 300


class InfrastructureFailure(RuntimeError):
    """The harness broke — distinct from the patch being wrong.

    Reporting a broken harness as a failed patch is how an evaluation lab
    manufactures false negatives, so this is a separate exception type carried all
    the way to a separate terminal state.
    """


@dataclass(frozen=True)
class CommandOutcome:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


def _run(command: list[str], cwd: Path, timeout: int) -> CommandOutcome:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            env=scrubbed_environment(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise InfrastructureFailure(f"executable not found: {command[0]}") from exc
    except subprocess.TimeoutExpired:
        return CommandOutcome(124, "", f"timed out after {timeout}s", timed_out=True)
    return CommandOutcome(completed.returncode, completed.stdout, completed.stderr)


def run_build(working_copy: Path) -> CommandOutcome:
    """ "Build" a Python package: byte-compile every source file.

    Cheap, and it genuinely catches what a build catches here — syntax errors and
    imports that cannot resolve. A patch that does not parse fails at this gate
    rather than producing a confusing test failure later.
    """
    return _run(
        [sys.executable, "-m", "compileall", "-q", "src"], working_copy, BUILD_TIMEOUT_SECONDS
    )


def _parse_junit_passes(report_path: Path) -> tuple[str, ...]:
    """Node ids of tests that passed, read from a JUnit XML report.

    Parsing the machine-readable report rather than scraping stdout: the summary
    line tells you *how many* passed, and regression detection needs to know
    *which*.
    """
    if not report_path.is_file():
        return ()

    # S314: the input is a JUnit report this process just asked pytest to write
    # into its own working copy — not untrusted third-party XML. Adding
    # defusedxml would be a dependency bought for a threat that is not present.
    import xml.etree.ElementTree as ElementTree  # noqa: S405

    try:
        tree = ElementTree.parse(report_path)  # noqa: S314
    except ElementTree.ParseError:
        return ()

    passing: list[str] = []
    for case in tree.iter("testcase"):
        failed = any(child.tag in {"failure", "error", "skipped"} for child in case)
        if not failed:
            passing.append(f"{case.get('classname', '')}::{case.get('name', '')}")
    return tuple(sorted(passing))


def run_visible_tests(working_copy: Path) -> tuple[CommandOutcome, tuple[str, ...]]:
    """Run the visible suite and report which tests passed."""
    report = working_copy / ".junit-visible.xml"
    report.unlink(missing_ok=True)
    outcome = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests_visible",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--junit-xml={report.name}",
        ],
        working_copy,
        TEST_TIMEOUT_SECONDS,
    )
    return outcome, _parse_junit_passes(report)


def run_hidden_tests(working_copy: Path) -> CommandOutcome:
    """Run the hidden acceptance suite.

    The hidden tests are copied in **here**, after the patch has been applied, so
    they were never present in a tree the patch could have touched.
    """
    hidden_source = FIXTURE_ROOT / "tests_hidden"
    if not hidden_source.is_dir():
        raise InfrastructureFailure("hidden test suite is missing from the fixture")

    hidden_target = working_copy / "tests_hidden"
    shutil.rmtree(hidden_target, ignore_errors=True)
    shutil.copytree(hidden_source, hidden_target)

    try:
        return _run(
            [sys.executable, "-m", "pytest", "tests_hidden", "-q", "-p", "no:cacheprovider"],
            working_copy,
            TEST_TIMEOUT_SECONDS,
        )
    finally:
        # Remove them again so no later step can observe them in the tree.
        shutil.rmtree(hidden_target, ignore_errors=True)


_PROPERTY_SCRIPT = """
import json, sys
sys.path.insert(0, ".")
from hypothesis import HealthCheck, given, settings, strategies as st
from src import sync
from src.effects import effect_count
from src.processor import Job
from src.store import ResultStore
from src.worker import deliver_concurrently

failures = []

@settings(
    max_examples=12,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    workers=st.integers(min_value=2, max_value=4),
    suffix=st.integers(min_value=0, max_value=999),
)
def property_at_most_one_commit(workers, suffix):
    database = "property-%d-%d.db" % (workers, suffix)
    ResultStore.initialise(database)
    job_id = "job-prop-%d-%d" % (workers, suffix)
    sync.set_coordinator(sync.BarrierCoordinator("after-duplicate-check", workers))
    try:
        deliver_concurrently(database, Job(job_id, "p"), worker_count=workers)
    finally:
        sync.set_coordinator(None)
    store = ResultStore(database)
    try:
        rows = [r for r in store.raw_result_rows() if r[0] == job_id]
    finally:
        store.close()
    effects = effect_count(database, job_id)
    if len(rows) > 1 or effects > 1:
        failures.append({"workers": workers, "rows": len(rows), "effects": effects})

try:
    property_at_most_one_commit()
except Exception as exc:
    failures.append({"error": str(exc)[:300]})

print(json.dumps({"passed": not failures, "failures": failures[:5]}, sort_keys=True))
"""


def run_property_tests(working_copy: Path) -> CommandOutcome:
    """Hypothesis property: at most one commit and one effect per job id.

    Generated over worker counts, so a repair that merely narrows the race window
    (rather than establishing exclusivity) fails on some example.
    """
    return _run([sys.executable, "-c", _PROPERTY_SCRIPT], working_copy, TEST_TIMEOUT_SECONDS)


def baseline_visible_passes(working_copy: Path) -> tuple[str, ...]:
    """Which visible tests pass on the *unpatched* tree.

    Captured before any patch is applied; it is the baseline the regression gate
    compares against.
    """
    _, passing = run_visible_tests(working_copy)
    return passing


def verify_candidate(
    working_copy: Path,
    *,
    candidate_id: str,
    patch_id: str,
    visible_tests_passing_before: tuple[str, ...] = (),
    prohibited_paths_touched: tuple[str, ...] = (),
) -> VerificationResult:
    """Build, test, and probe a patched working copy."""
    started = time.monotonic()

    visible_passing_after: tuple[str, ...] = ()
    build = run_build(working_copy)
    if build.succeeded:
        visible, visible_passing_after = run_visible_tests(working_copy)
        hidden = run_hidden_tests(working_copy)
        properties = run_property_tests(working_copy)
        probe = concurrent_delivery_probe(working_copy)
    else:
        # Nothing downstream is meaningful when the tree does not compile.
        visible = hidden = properties = CommandOutcome(1, "", "build failed")
        probe = None

    observations = probe.observations if probe is not None else {}

    def _count(key: str) -> int:
        """Read a numeric observation defensively.

        Probe output is parsed JSON, so a malformed probe could put anything
        here. A crash at this point would be reported as an infrastructure
        failure and mask the real result, so an unreadable count degrades to 0
        and the gates see a value they can reject on.
        """
        raw = observations.get(key, 0)
        if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
            return 0
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0

    effect_count = _count("effect_count")
    raw_rows = _count("raw_result_rows")

    property_payload: dict[str, object] = {}
    if properties.stdout.strip():
        try:
            property_payload = json.loads(properties.stdout)
        except ValueError:
            property_payload = {}

    return VerificationResult(
        candidate_id=candidate_id,
        patch_id=patch_id,
        build_succeeded=build.succeeded,
        visible_tests_passed=visible.succeeded,
        visible_tests_passing_before=visible_tests_passing_before,
        visible_tests_passing_after=visible_passing_after,
        hidden_tests_passed=hidden.succeeded,
        property_tests_passed=bool(property_payload.get("passed", False)),
        invariant_holds=bool(observations.get("invariant_holds", False)),
        effect_invocation_count=effect_count,
        committed_result_count=raw_rows,
        prohibited_paths_touched=prohibited_paths_touched,
        build_output_sha256=None,
        duration_seconds=round(time.monotonic() - started, 3),
    )
