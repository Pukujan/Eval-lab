"""Activity tests: path confinement, working-copy isolation, environment scrubbing."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.activities.patching import (
    PatchApplicationError,
    apply_patch,
    create_working_copy,
    materialise_candidate_patch,
)
from app.activities.probes import scrubbed_environment
from app.activities.repository import inspect_repository
from app.domain.schemas import FileChange, PatchArtifact


@pytest.fixture
def working_copy(tmp_path: Path):
    copy = create_working_copy(destination_root=tmp_path)
    yield copy
    copy.cleanup()


def _patch(path: str, content: str = "x = 1") -> PatchArtifact:
    return PatchArtifact(
        patch_id="p-1",
        candidate_id="c-1",
        changes=(FileChange(path=path, new_content=content),),
    )


def test_working_copy_is_isolated_from_the_pristine_fixture(working_copy) -> None:
    from app.config import FIXTURE_ROOT

    original = (FIXTURE_ROOT / "src" / "processor.py").read_text(encoding="utf-8")
    apply_patch(working_copy, _patch("src/processor.py", "# overwritten"))

    assert (working_copy.path / "src" / "processor.py").read_text(
        encoding="utf-8"
    ) == "# overwritten"
    assert (FIXTURE_ROOT / "src" / "processor.py").read_text(encoding="utf-8") == original


def test_two_working_copies_do_not_interfere(tmp_path: Path) -> None:
    first = create_working_copy(destination_root=tmp_path)
    second = create_working_copy(destination_root=tmp_path)
    try:
        apply_patch(first, _patch("src/processor.py", "# first"))
        assert (second.path / "src" / "processor.py").read_text(encoding="utf-8") != "# first"
        assert first.path != second.path
    finally:
        first.cleanup()
        second.cleanup()


@pytest.mark.parametrize(
    "escape",
    [
        "../../../etc/passwd",
        "../outside.py",
        "src/../../escape.py",
        "/etc/passwd",
        "/tmp/absolute.py",
    ],
)
def test_paths_escaping_the_working_copy_are_refused(working_copy, escape: str) -> None:
    with pytest.raises(PatchApplicationError):
        apply_patch(working_copy, _patch(escape))


def test_symlink_escape_is_refused(working_copy) -> None:
    """Confinement is checked after realpath, which is what catches this."""
    outside = working_copy.path.parent / "outside"
    outside.mkdir(exist_ok=True)
    link = working_copy.path / "src" / "escape-link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this platform")

    with pytest.raises(PatchApplicationError):
        apply_patch(working_copy, _patch("src/escape-link/evil.py"))


@pytest.mark.parametrize(
    "prohibited",
    [
        "tests_visible/test_processing.py",
        "tests_hidden/test_no_duplicate_processing.py",
        "reference/processor.py",
        "probe.py",
        "INVARIANTS.md",
    ],
)
def test_prohibited_paths_are_refused_at_application_time(working_copy, prohibited: str) -> None:
    """Refused before the write lands, so the later gate is a second line."""
    with pytest.raises(PatchApplicationError, match="prohibited"):
        apply_patch(working_copy, _patch(prohibited))


def test_legitimate_source_paths_are_accepted(working_copy) -> None:
    written = apply_patch(working_copy, _patch("src/store.py", "# patched"))
    assert written == ("src/store.py",)


def test_materialised_patches_target_the_expected_files() -> None:
    good = materialise_candidate_patch("C-claim", "reference")
    assert good.touched_paths == ("src/processor.py",)
    assert "try_claim" in good.changes[0].new_content
    assert good.source_label == "reference"

    ducttape = materialise_candidate_patch("C-dedupe-read", "ducttape")
    assert ducttape.touched_paths == ("src/store.py",)
    assert "GROUP BY job_id" in ducttape.changes[0].new_content


def test_unknown_patch_source_is_refused() -> None:
    with pytest.raises(PatchApplicationError, match="unknown patch source"):
        materialise_candidate_patch("C-x", "handwritten")


def test_subprocess_environment_is_an_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provider credentials must be structurally absent from child processes."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-propagate")
    monkeypatch.setenv("SOME_INTERNAL_TOKEN", "secret")

    env = scrubbed_environment()
    assert "OPENAI_API_KEY" not in env
    assert "SOME_INTERNAL_TOKEN" not in env
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    if "PATH" in os.environ:
        assert "PATH" in env


def test_repository_inspection_reads_the_declared_contract() -> None:
    inspection = inspect_repository()
    assert inspection.delivery_model == "at-least-once"
    assert any("at most one committed" in s for s in inspection.declared_invariants)
    assert inspection.visible_files
    assert len(inspection.content_digest) == 64
