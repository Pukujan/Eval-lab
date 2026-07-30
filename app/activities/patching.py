"""Working copies and patch application, with path confinement.

Two responsibilities, deliberately together because they must never be separated:
a patch is only ever applied to a fresh copy, and only ever to a path that
provably stays inside that copy.

Confinement is checked after ``realpath``, before any write. Checking the string
before resolution misses the symlink case, which is the one an attacker uses.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.config import FIXTURE_ROOT
from app.domain.fixtures import is_prohibited
from app.domain.schemas import FileChange, PatchArtifact

#: Directories never copied into a working copy: the answer key and the hidden
#: acceptance tests are materialised separately, by the verifier, never by the
#: patching path.
_EXCLUDED_FROM_SOLVER_COPY = ("reference", "tests_hidden", "patches", "__pycache__")


class PatchApplicationError(RuntimeError):
    """Raised when a patch is refused."""


@dataclass(frozen=True)
class WorkingCopy:
    """An isolated copy of the fixture that a patch may be applied to."""

    path: Path
    includes_hidden_tests: bool

    def cleanup(self) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


def create_working_copy(
    source: str | Path | None = None,
    *,
    destination_root: str | Path | None = None,
    include_hidden_tests: bool = False,
) -> WorkingCopy:
    """Copy the fixture into a fresh directory.

    ``include_hidden_tests`` is False for anything a solver role touches. The
    verifier sets it True *after* the patch has been applied, so hidden tests are
    never present in a tree the patch could have modified.
    """
    origin = Path(source or FIXTURE_ROOT).resolve()
    if destination_root is not None:
        Path(destination_root).mkdir(parents=True, exist_ok=True)
    target = Path(tempfile.mkdtemp(prefix="working-copy-", dir=destination_root))

    def _ignore(directory: str, names: list[str]) -> set[str]:
        del directory
        excluded = {n for n in names if n in _EXCLUDED_FROM_SOLVER_COPY}
        if not include_hidden_tests:
            return excluded
        return excluded - {"tests_hidden"}

    shutil.copytree(origin, target, dirs_exist_ok=True, ignore=_ignore)
    return WorkingCopy(path=target, includes_hidden_tests=include_hidden_tests)


def _confined_target(working_copy: Path, relative_path: str) -> Path:
    """Resolve ``relative_path`` inside ``working_copy`` or refuse."""
    if Path(relative_path).is_absolute():
        raise PatchApplicationError(f"absolute paths are not permitted: {relative_path}")

    root = working_copy.resolve()
    candidate = (root / relative_path).resolve()

    # Compare resolved paths: this is what catches `..` traversal and symlinks
    # that point outside the copy.
    if not candidate.is_relative_to(root):
        raise PatchApplicationError(
            f"path escapes the working copy: {relative_path} -> {candidate}"
        )
    return candidate


def apply_patch(working_copy: WorkingCopy, patch: PatchArtifact) -> tuple[str, ...]:
    """Apply ``patch`` to ``working_copy``; return the paths written.

    Prohibited paths are refused here as well as gated later. Refusing at the
    point of application means a prohibited write never lands on disk, so the
    later gate is a second line rather than the only one.
    """
    written: list[str] = []
    for change in patch.changes:
        if is_prohibited(change.path):
            raise PatchApplicationError(f"patch targets a prohibited path: {change.path}")
        target = _confined_target(working_copy.path, change.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(change.new_content, encoding="utf-8")
        written.append(change.path)
    return tuple(written)


def materialise_candidate_patch(candidate_id: str, patch_source: str) -> PatchArtifact:
    """Turn a named repair strategy into concrete file content.

    **Honest scope note.** In this walking skeleton the patch *bodies* come from
    the fixture's own candidate library rather than from a model. The mock models
    choose a strategy and describe it; the harness materialises the corresponding
    file content. Generating real patch text is a Task 2 concern.

    This does not weaken the experiment, because the experiment is about the
    **gate**: whether an incorrect patch is deterministically rejected. The gate
    reads observable behaviour and neither knows nor cares where the bytes came
    from — ``source_label`` is recorded but never consulted by a gate (ADR-0009).

    It does mean nothing here demonstrates a model's ability to author a fix, and
    that limitation is stated in `docs/limitations.md` rather than left implicit.
    """
    if patch_source == "reference":
        content = (FIXTURE_ROOT / "reference" / "processor.py").read_text(encoding="utf-8")
        target = "src/processor.py"
    elif patch_source == "ducttape":
        content = (FIXTURE_ROOT / "patches" / "ducttape_store.py").read_text(encoding="utf-8")
        target = "src/store.py"
    else:
        raise PatchApplicationError(f"unknown patch source '{patch_source}'")

    return PatchArtifact(
        patch_id=f"patch-{candidate_id}",
        candidate_id=candidate_id,
        changes=(FileChange(path=target, new_content=content),),
        source_label=patch_source,
    )
