"""Confirm a merged PR, safely remove its clean worktree, and sync canonical main."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

TASK_DIRECTORY = re.compile(r"TASK-\d{4}(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?\Z", re.IGNORECASE)
REQUIRED_CHECKS = {"quality (Python 3.11)", "quality (Python 3.12)"}


def run(command: list[str], *, cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"command failed ({result.returncode}): {command!r}\n{detail}")
    return result.stdout.strip()


def normalize(path: Path) -> str:
    return str(path.resolve()).casefold()


def validate_worktree_path(root: Path, path: Path) -> Path:
    root = root.resolve()
    path = path.resolve()
    if path.parent != (root / "worktrees").resolve() or not TASK_DIRECTORY.fullmatch(path.name):
        raise ValueError(f"refusing to remove a path outside worktrees/<task-id>: {path}")
    return path


def passing_required_checks(pr: dict[str, object]) -> bool:
    rollup = pr.get("statusCheckRollup")
    if not isinstance(rollup, list):
        return False
    passing = {
        str(item.get("name") or item.get("context"))
        for item in rollup
        if isinstance(item, dict) and str(item.get("conclusion") or item.get("state")) == "SUCCESS"
    }
    return REQUIRED_CHECKS <= passing


def finalize(pr_number: int, issue_number: int, canonical_root: Path, worktree: Path | None) -> str:
    root = canonical_root.resolve()
    pr = json.loads(
        run(
            [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--json",
                "state,mergedAt,headRefName,headRefOid,baseRefName,mergeCommit,statusCheckRollup,body",
            ],
            cwd=root,
        )
    )
    if pr.get("state") != "MERGED" or not pr.get("mergedAt") or pr.get("baseRefName") != "main":
        raise ValueError(f"PR #{pr_number} is not confirmed merged into main")
    head_sha = pr.get("headRefOid")
    merge = pr.get("mergeCommit") or {}
    merge_sha = merge.get("oid") if isinstance(merge, dict) else None
    if not head_sha or not merge_sha or not passing_required_checks(pr):
        raise ValueError(
            "exact PR head, merge SHA, or required Python checks are missing/unsuccessful"
        )
    if not re.search(rf"(?im)^Task issue:\s*#{issue_number}\b", str(pr.get("body") or "")):
        raise ValueError(f"PR #{pr_number} does not link task issue #{issue_number}")

    # Validate the canonical checkout before any cleanup. A dirty canonical
    # root must never cause a worktree to be removed as a partial finalization.
    dirty = run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=root)
    if dirty:
        raise ValueError(
            f"canonical checkout has local changes; preserve them before syncing main:\n{dirty}"
        )

    if worktree is not None:
        path = validate_worktree_path(root, worktree)
        listed = run(["git", "worktree", "list", "--porcelain"], cwd=root)
        registered = {
            Path(line.removeprefix("worktree ")).resolve()
            for line in listed.splitlines()
            if line.startswith("worktree ")
        }
        if path not in registered:
            raise ValueError(f"path is not a registered linked worktree: {path}")
        branch = run(["git", "branch", "--show-current"], cwd=path)
        if branch != pr.get("headRefName"):
            raise ValueError(
                f"worktree branch {branch!r} does not match PR branch {pr.get('headRefName')!r}"
            )
        worktree_head = run(["git", "rev-parse", "HEAD"], cwd=path)
        if worktree_head != head_sha:
            raise ValueError(
                f"worktree HEAD {worktree_head} differs from merged PR head {head_sha}"
            )
        state = run(
            ["git", "status", "--porcelain=v1", "--ignored", "--untracked-files=all"], cwd=path
        )
        if state:
            raise ValueError(
                "worktree has tracked, untracked, or ignored state; preserve and reconcile it before removal:\n"
                + state
            )
        run(["git", "worktree", "remove", str(path)], cwd=root)
        listed_after = run(["git", "worktree", "list", "--porcelain"], cwd=root)
        remaining = {
            normalize(Path(line.removeprefix("worktree ")))
            for line in listed_after.splitlines()
            if line.startswith("worktree ")
        }
        if normalize(path) in remaining:
            raise RuntimeError(f"worktree remains registered after removal: {path}")
    else:
        local_head = run(["git", "rev-parse", f"refs/heads/{pr['headRefName']}"], cwd=root)
        if local_head != head_sha:
            raise ValueError("local task branch differs from the exact merged PR head")

    run(
        ["git", "fetch", "origin", "+refs/heads/main:refs/remotes/origin/main"],
        cwd=root,
    )
    branch = run(["git", "branch", "--show-current"], cwd=root)
    if branch != "main":
        run(["git", "switch", "main"], cwd=root)
    run(["git", "pull", "--ff-only", "origin", "main"], cwd=root)
    main_head = run(["git", "rev-parse", "HEAD"], cwd=root)
    remote = run(["git", "rev-parse", "origin/main"], cwd=root)
    if main_head != remote:
        raise RuntimeError("canonical main did not synchronize to origin/main")

    note = (
        f"TASK checkpoint finalized. PR #{pr_number} merged after required CI. "
        f"PR head: `{head_sha}`. Merge commit: `{merge_sha}`. "
        f"Temporary worktree: {'removed and verified clean' if worktree is not None else 'not used'}. "
        f"Canonical `main`: `{main_head}`."
    )
    run(["gh", "issue", "close", str(issue_number), "--comment", note], cwd=root)
    return f"PR #{pr_number} merged at {merge_sha}; issue #{issue_number} updated; canonical main is {main_head}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--canonical-root", type=Path, required=True)
    parser.add_argument(
        "--worktree", type=Path, help="merged task worktree under canonical-root/worktrees"
    )
    args = parser.parse_args()
    try:
        print(finalize(args.pr, args.issue, args.canonical_root, args.worktree))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Checkpoint finalization stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
