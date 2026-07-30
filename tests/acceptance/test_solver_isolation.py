"""Solver roles must not reach the answer key or the hidden tests (T-1)."""

from __future__ import annotations

from pathlib import Path

from app.activities.patching import create_working_copy
from app.activities.repository import inspect_repository
from app.config import FIXTURE_ROOT
from app.domain.fixtures import (
    PROHIBITED_PATHS,
    SOLVER_FORBIDDEN_DIRECTORIES,
    is_prohibited,
    solver_visible_paths,
)

SECRET_DIRECTORIES = ("reference", "tests_hidden")


def test_secret_directories_actually_exist() -> None:
    """Otherwise this whole file would pass vacuously."""
    for directory in SECRET_DIRECTORIES:
        assert (FIXTURE_ROOT / directory).is_dir(), f"{directory} is missing from the fixture"


def test_solver_visible_paths_exclude_the_answer_key_and_hidden_tests() -> None:
    visible = solver_visible_paths()
    assert visible, "the solver must be able to see something"
    for path in visible:
        parts = path.relative_to(FIXTURE_ROOT).parts
        for forbidden in SOLVER_FORBIDDEN_DIRECTORIES:
            assert forbidden not in parts, f"{path} exposes {forbidden}"


def test_reference_implementation_content_is_not_reachable() -> None:
    """Compare on content, not just on paths: a copy under another name still leaks."""
    reference_body = (FIXTURE_ROOT / "reference" / "processor.py").read_text(encoding="utf-8")
    marker = "if not self.store.try_claim(job.job_id):"
    assert marker in reference_body, "test marker drifted from the reference implementation"

    for path in solver_visible_paths():
        assert marker not in path.read_text(encoding="utf-8"), f"{path} contains the answer key"


def test_hidden_test_content_is_not_reachable() -> None:
    hidden = (FIXTURE_ROOT / "tests_hidden" / "test_no_duplicate_processing.py").read_text(
        encoding="utf-8"
    )
    marker = "test_external_effect_executes_at_most_once"
    assert marker in hidden

    for path in solver_visible_paths():
        assert marker not in path.read_text(encoding="utf-8"), f"{path} exposes a hidden test"


def test_repository_inspection_withholds_the_secret_directories() -> None:
    inspection = inspect_repository()
    assert set(inspection.withheld_directories) >= set(SECRET_DIRECTORIES)
    for name in inspection.visible_files:
        for forbidden in SOLVER_FORBIDDEN_DIRECTORIES:
            assert not name.startswith(f"{forbidden}/")


def test_solver_working_copy_omits_the_answer_key(tmp_path: Path) -> None:
    working_copy = create_working_copy(destination_root=tmp_path)
    try:
        for directory in (*SECRET_DIRECTORIES, "patches"):
            assert not (working_copy.path / directory).exists(), (
                f"{directory} was copied into a solver-visible working copy"
            )
        assert (working_copy.path / "src").is_dir()
        assert (working_copy.path / "tests_visible").is_dir()
    finally:
        working_copy.cleanup()


def test_prohibited_paths_cover_every_secret() -> None:
    for directory in (*SECRET_DIRECTORIES, "tests_visible", "patches"):
        assert directory in PROHIBITED_PATHS
        assert is_prohibited(f"{directory}/anything.py")
    assert is_prohibited("probe.py")
    assert is_prohibited("INVARIANTS.md")
    assert not is_prohibited("src/processor.py")


def test_visibility_is_an_allowlist_not_a_denylist(tmp_path: Path) -> None:
    """A newly added secret file must be invisible by default.

    A denylist fails open: the file nobody remembered to exclude leaks silently.
    """
    fake_fixture = tmp_path / "fixture"
    (fake_fixture / "src").mkdir(parents=True)
    (fake_fixture / "src" / "module.py").write_text("x = 1", encoding="utf-8")

    (fake_fixture / "brand_new_secret").mkdir()
    (fake_fixture / "brand_new_secret" / "answer.py").write_text("SECRET", encoding="utf-8")
    (fake_fixture / "solutions.py").write_text("SECRET", encoding="utf-8")

    visible = solver_visible_paths(fake_fixture)
    names = {str(p.relative_to(fake_fixture)) for p in visible}
    assert names == {"src/module.py"}
