from __future__ import annotations

import os
from pathlib import Path

from scripts.check_workspace_policy import workspace_violations


def test_single_canonical_checkout_and_root_environment_pass(tmp_path: Path) -> None:
    root = tmp_path / "eval-lab"
    root.mkdir()
    venv = root / ".venv"
    bin_dir = "Scripts" if os.name == "nt" else "bin"
    executable = "python.exe" if os.name == "nt" else "python"
    (venv / bin_dir).mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = python\n", encoding="utf-8")
    (venv / bin_dir / executable).touch()

    assert (
        workspace_violations(
            root,
            canonical_root=root,
            worktrees=[root],
        )
        == []
    )


def test_worktree_outside_canonical_worktrees_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "eval-lab"
    extra = tmp_path / "eval-lab-task"
    root.mkdir()
    extra.mkdir()

    violations = workspace_violations(
        root,
        canonical_root=root,
        worktrees=[root, extra],
    )

    assert any("direct children of the canonical .worktrees directory" in item for item in violations)


def test_active_in_root_temporary_worktree_is_allowed(tmp_path: Path) -> None:
    root = tmp_path / "eval-lab"
    temporary = root / ".worktrees" / "TASK-0050-temporary-worktree-lifecycle"
    temporary.mkdir(parents=True)

    assert (
        workspace_violations(
            root,
            canonical_root=root,
            worktrees=[root, temporary],
        )
        == []
    )


def test_temporary_worktree_name_must_contain_task_id(tmp_path: Path) -> None:
    root = tmp_path / "eval-lab"
    temporary = root / ".worktrees" / "scratch"
    temporary.mkdir(parents=True)

    violations = workspace_violations(
        root,
        worktrees=[root, temporary],
    )

    assert any("repository task ID format" in item for item in violations)


def test_nested_temporary_worktree_location_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "eval-lab"
    nested = root / ".worktrees" / "TASK-0050" / "nested"
    nested.mkdir(parents=True)

    violations = workspace_violations(
        root,
        worktrees=[root, nested],
    )

    assert any("direct children of the canonical .worktrees directory" in item for item in violations)


def test_missing_registered_worktree_path_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "eval-lab"
    root.mkdir()
    missing = root / ".worktrees" / "TASK-0050"

    violations = workspace_violations(
        root,
        worktrees=[root, missing],
    )

    assert any("registered temporary worktree path is missing" in item for item in violations)


def test_missing_canonical_checkout_registration_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "eval-lab"
    root.mkdir()
    another = root / ".worktrees" / "TASK-0050"
    another.mkdir(parents=True)

    violations = workspace_violations(
        root,
        worktrees=[another],
    )

    assert any("canonical checkout is missing" in item for item in violations)


def test_duplicate_worktree_registration_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "eval-lab"
    root.mkdir()

    violations = workspace_violations(
        root,
        worktrees=[root, root],
    )

    assert any("duplicate Git worktree registration" in item for item in violations)


def test_noncanonical_checkout_path_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "second-copy"
    canonical = tmp_path / "eval-lab"
    root.mkdir()

    violations = workspace_violations(
        root,
        canonical_root=canonical,
        worktrees=[root],
    )

    assert any("expected canonical root" in item for item in violations)


def test_nested_virtual_environment_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "eval-lab"
    nested_venv = root / ".worktrees" / "task" / ".venv"
    nested_venv.mkdir(parents=True)

    violations = workspace_violations(root, worktrees=[root])

    assert any("nested dependency directory" in item for item in violations)


def test_root_node_modules_requires_manifest_and_lockfile(tmp_path: Path) -> None:
    root = tmp_path / "eval-lab"
    (root / "node_modules").mkdir(parents=True)

    violations = workspace_violations(root, worktrees=[root])

    assert any("requires a root package.json" in item for item in violations)

    (root / "package.json").write_text("{}\n", encoding="utf-8")
    (root / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")

    assert workspace_violations(root, worktrees=[root]) == []


def test_nested_node_modules_is_rejected_even_with_root_lockfile(tmp_path: Path) -> None:
    root = tmp_path / "eval-lab"
    root.mkdir()
    (root / "package.json").write_text("{}\n", encoding="utf-8")
    (root / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    (root / "node_modules").mkdir()
    (root / "tools" / "example" / "node_modules").mkdir(parents=True)

    violations = workspace_violations(root, worktrees=[root])

    assert any("nested dependency directory" in item for item in violations)
