from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT_DIRS = {".venv", "node_modules"}
NODE_LOCKFILES = ("pnpm-lock.yaml", "package-lock.json", "yarn.lock", "bun.lock", "bun.lockb")
TASK_WORKTREE_NAME = re.compile(r"TASK-\d{4}(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?\Z", re.IGNORECASE)


def _normalized(path: Path) -> str:
    return os.path.normcase(str(path.expanduser().resolve()))


def _read_worktrees(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=root,
        capture_output=True,
        check=True,
        text=True,
    )
    return [
        Path(line.removeprefix("worktree "))
        for line in result.stdout.splitlines()
        if line.startswith("worktree ")
    ]


def _check_worktrees(
    root: Path,
    worktrees: Iterable[Path],
    canonical_root: Path | None,
) -> list[str]:
    root_key = _normalized(root)
    paths = list(worktrees)
    violations: list[str] = []

    if canonical_root is not None and root_key != _normalized(canonical_root):
        violations.append(
            f"checkout root is {_normalized(root)}, expected canonical root {_normalized(canonical_root)}"
        )

    worktree_keys = [_normalized(path) for path in paths]
    if root_key not in worktree_keys:
        violations.append(
            f"canonical checkout is missing from its Git worktree list: {root.resolve()}"
        )

    worktrees_root = (root / ".worktrees").resolve()
    seen: set[str] = set()
    for path in paths:
        path_key = _normalized(path)
        if path_key in seen:
            violations.append(f"duplicate Git worktree registration: {path.resolve()}")
            continue
        seen.add(path_key)
        if path_key == root_key:
            continue

        resolved = path.resolve()
        if resolved.parent != worktrees_root:
            violations.append(
                "temporary worktrees must be direct children of the canonical "
                f".worktrees directory: {resolved}"
            )
        if not TASK_WORKTREE_NAME.fullmatch(resolved.name):
            violations.append(
                "temporary worktree directory must use the repository task ID "
                f"format TASK-####[-short-name]: {resolved}"
            )
        if not resolved.is_dir():
            violations.append(f"registered temporary worktree path is missing: {resolved}")
    return violations


def _check_dependency_directories(root: Path) -> list[str]:
    root = root.resolve()
    violations: list[str] = []

    for current, directory_names, _ in os.walk(root):
        current_path = Path(current)
        if current_path == root:
            directory_names[:] = [name for name in directory_names if name != ".git"]
        else:
            directory_names[:] = [name for name in directory_names if name not in {".git"}]

        for name in tuple(directory_names):
            if name not in ENVIRONMENT_DIRS:
                continue

            candidate = current_path / name
            is_root_environment = candidate.parent == root
            if not is_root_environment:
                violations.append(f"nested dependency directory is forbidden: {candidate}")
            elif name == "node_modules":
                has_manifest = (root / "package.json").is_file()
                has_lockfile = any((root / lockfile).is_file() for lockfile in NODE_LOCKFILES)
                if not (has_manifest and has_lockfile):
                    violations.append(
                        "root node_modules requires a root package.json and a package-manager lockfile"
                    )
            elif name == ".venv":
                interpreter = (
                    candidate / "Scripts" / "python.exe"
                    if os.name == "nt"
                    else candidate / "bin" / "python"
                )
                if not (candidate / "pyvenv.cfg").is_file() or not interpreter.is_file():
                    violations.append(f"root .venv is incomplete: {candidate}")

            # Do not descend into dependency installations.
            directory_names.remove(name)

    return violations


def workspace_violations(
    root: Path,
    *,
    canonical_root: Path | None = None,
    worktrees: Iterable[Path] | None = None,
) -> list[str]:
    root = root.resolve()
    if worktrees is None:
        try:
            worktrees = _read_worktrees(root)
        except (OSError, subprocess.CalledProcessError) as exc:
            return [f"could not inspect registered Git worktrees: {exc}"]

    return [
        *_check_worktrees(root, worktrees, canonical_root),
        *_check_dependency_directories(root),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check Eval Lab's canonical checkout, temporary worktree, and environment policy."
    )
    parser.add_argument(
        "--canonical-root",
        type=Path,
        required=True,
        help="the one authorized local Eval Lab checkout",
    )
    args = parser.parse_args()

    failures = workspace_violations(ROOT, canonical_root=args.canonical_root)
    if failures:
        print("Workspace policy FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(
        "Workspace policy OK: canonical checkout, in-root temporary worktrees, "
        "and one dependency environment"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
