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


def test_additional_registered_worktree_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "eval-lab"
    extra = tmp_path / "eval-lab-task"
    root.mkdir()
    extra.mkdir()

    violations = workspace_violations(
        root,
        canonical_root=root,
        worktrees=[root, extra],
    )

    assert any("exactly one registered worktree" in item for item in violations)


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
