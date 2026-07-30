"""Run the fixture's own visible and hidden suites from the main test suite.

Both are required deliverables. They are executed against working copies with the
known-good repair applied, which is the configuration in which both suites are
supposed to be green — and the assertion that they are is what proves the fixture
is solvable at all.

A fixture whose hidden tests cannot pass even with the reference patch would make
every rejection meaningless.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from app.activities.patching import create_working_copy
from app.config import FIXTURE_ROOT


def _pytest_in(directory: Path, target: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", target, "-q", "-p", "no:cacheprovider"],
        cwd=str(directory),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


@pytest.fixture
def repaired_copy(tmp_path: Path):
    copy = create_working_copy(destination_root=tmp_path, include_hidden_tests=True)
    shutil.copyfile(FIXTURE_ROOT / "reference" / "processor.py", copy.path / "src" / "processor.py")
    yield copy.path
    copy.cleanup()


@pytest.fixture
def ducttape_copy(tmp_path: Path):
    copy = create_working_copy(destination_root=tmp_path, include_hidden_tests=True)
    shutil.copyfile(FIXTURE_ROOT / "patches" / "ducttape_store.py", copy.path / "src" / "store.py")
    yield copy.path
    copy.cleanup()


def test_fixture_visible_tests_pass_with_the_reference_repair(repaired_copy: Path) -> None:
    result = _pytest_in(repaired_copy, "tests_visible")
    assert result.returncode == 0, result.stdout[-2000:]


def test_fixture_hidden_tests_pass_with_the_reference_repair(repaired_copy: Path) -> None:
    """The fixture is solvable: the correct patch satisfies the hidden suite."""
    result = _pytest_in(repaired_copy, "tests_hidden")
    assert result.returncode == 0, result.stdout[-2000:]


def test_ducttape_passes_visible_but_fails_hidden(ducttape_copy: Path) -> None:
    """The exact asymmetry the walking skeleton exists to detect."""
    visible = _pytest_in(ducttape_copy, "tests_visible")
    hidden = _pytest_in(ducttape_copy, "tests_hidden")

    assert visible.returncode == 0, (
        "the duct-tape patch should satisfy the visible suite — otherwise it is "
        f"not tempting:\n{visible.stdout[-1500:]}"
    )
    assert hidden.returncode != 0, "the hidden suite failed to catch the duct-tape patch"
    assert "test_external_effect_executes_at_most_once" in hidden.stdout


def test_hidden_suite_is_not_reachable_from_a_solver_copy(tmp_path: Path) -> None:
    copy = create_working_copy(destination_root=tmp_path)
    try:
        assert not (copy.path / "tests_hidden").exists()
    finally:
        copy.cleanup()
