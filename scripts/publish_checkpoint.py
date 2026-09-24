"""Commit and publish one explicit Eval Lab checkpoint, then request auto-merge."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_BRANCH = re.compile(r"task/(TASK-\d{4})-[a-z0-9]+(?:-[a-z0-9]+)*\Z", re.IGNORECASE)
COMMIT_SUBJECT = re.compile(r"TASK-\d{4}: .+\Z")
SECRET_PATH = re.compile(r"(?:^|/)(?:\.env(?:\..*)?|.*(?:credential|secret).*)$", re.IGNORECASE)
PRIVATE_PATH = re.compile(
    r"(?:^|/).*(?:private[-_ ]?benchmark|private[-_ ]?gold|holdout[-_ ]?private).*$", re.IGNORECASE
)
SECRET_VALUE = re.compile(
    r"(?i)\b(?:sk-[a-z0-9_-]{20,}|gh[pousr]_[a-z0-9_]{20,}|github_pat_[a-z0-9_]{20,}|AKIA[0-9A-Z]{16})\b"
)
SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|secret)"
    r"\s*[:=]\s*[\"']?[A-Za-z0-9/+_=.\-]{24,}"
)
REQUIRED_CHECKS = {"quality (Python 3.11)", "quality (Python 3.12)"}


def task_id_from_branch(branch: str) -> str:
    match = TASK_BRANCH.fullmatch(branch)
    if match is None:
        raise ValueError(f"expected a task branch like task/TASK-0001-short-name, got {branch!r}")
    return match.group(1).upper()


def normalize_repo_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"checkpoint paths must be repository-relative: {value}")
    normalized = path.as_posix().removeprefix("./")
    if not normalized or normalized == ".":
        raise ValueError("checkpoint paths must name files, not the repository root")
    return normalized


def checkpoint_pr_body(
    task_id: str, issue: int, commit_subject: str, paths: list[str], head_sha: str
) -> str:
    file_list = "\n".join(f"- `{path}`" for path in paths)
    return (
        f"Task issue: #{issue}\n\n"
        f"Task: {task_id}\n\n"
        f"Checkpoint: {commit_subject}\n"
        f"Exact head: `{head_sha}`\n\n"
        "Files in this checkpoint:\n"
        f"{file_list}\n\n"
        "GitHub Actions runs the required CI checks. Auto-merge is enabled and will "
        "merge only when branch protection requirements pass. The issue stays open until the "
        "finalizer verifies the exact head/merge SHA and cleans any linked worktree."
    )


def run(command: list[str], *, cwd: Path = ROOT) -> str:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"command failed ({result.returncode}): {command!r}\n{detail}")
    return result.stdout.strip()


def changed_paths(root: Path) -> tuple[set[str], set[str]]:
    staged = set(run(["git", "diff", "--cached", "--name-only", "-z"], cwd=root).split("\0")) - {""}
    unstaged = set(run(["git", "diff", "--name-only", "-z"], cwd=root).split("\0")) - {""}
    untracked = set(
        run(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=root).split("\0")
    ) - {""}
    return staged, unstaged | untracked


def run_local_gates(root: Path, changed_python: list[str]) -> None:
    commands = [
        ["uv", "lock", "--check"],
        ["uv", "sync", "--locked", "--extra", "dev"],
        ["uv", "run", "--locked", "python", "scripts/check_repo_contract.py"],
        [
            "uv",
            "run",
            "--locked",
            "python",
            "scripts/check_workspace_policy.py",
            "--canonical-root",
            str(root),
        ],
        ["uv", "run", "--locked", "ruff", "check", "."],
        ["uv", "run", "--locked", "mypy", "src/eval_lab"],
        ["uv", "run", "--locked", "python", "-m", "pytest", "-q"],
    ]
    if changed_python:
        commands.insert(5, ["uv", "run", "--locked", "ruff", "format", "--check", *changed_python])
    with tempfile.TemporaryDirectory(prefix="eval-lab-build-") as output_dir:
        commands.append(["uv", "build", "--out-dir", str(Path(output_dir) / "dist")])
        for command in commands:
            print(f"Running: {' '.join(command)}", flush=True)
            run(command, cwd=root)


def scan_staged_changes(root: Path, paths: set[str]) -> None:
    violations = sorted(
        path for path in paths if SECRET_PATH.search(path) or PRIVATE_PATH.search(path)
    )
    diff = run(["git", "diff", "--cached", "--no-ext-diff", "--unified=0"], cwd=root)
    added_lines = [
        line for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")
    ]
    if any(SECRET_VALUE.search(line) or SECRET_ASSIGNMENT.search(line) for line in added_lines):
        violations.append("staged content contains a credential-like value")
    if violations:
        # Do not echo matching content: it could itself be a secret or private record.
        raise ValueError(
            f"refusing to publish possible secret/private content: {sorted(set(violations))}"
        )


def verify_required_checks(root: Path) -> None:
    repo = json.loads(run(["gh", "repo", "view", "--json", "nameWithOwner"], cwd=root))[
        "nameWithOwner"
    ]
    protection = json.loads(
        run(
            ["gh", "api", f"repos/{repo}/branches/main/protection/required_status_checks"], cwd=root
        )
    )
    configured = set(protection.get("contexts", []))
    if not REQUIRED_CHECKS <= configured:
        raise ValueError(f"main is missing required checks: {sorted(REQUIRED_CHECKS - configured)}")


def open_or_merged_pr(branch: str, root: Path) -> list[dict[str, object]]:
    return json.loads(
        run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "all",
                "--head",
                branch,
                "--base",
                "main",
                "--json",
                "number,url,state",
            ],
            cwd=root,
        )
    )


def verify_open_issue(issue: int, root: Path) -> None:
    info = json.loads(run(["gh", "issue", "view", str(issue), "--json", "state"], cwd=root))
    if info.get("state") != "OPEN":
        raise ValueError(f"GitHub issue #{issue} is not open")


def publish(args: argparse.Namespace) -> str:
    root = Path(run(["git", "rev-parse", "--show-toplevel"])).resolve()
    branch = run(["git", "branch", "--show-current"], cwd=root)
    task_id = task_id_from_branch(branch)
    if not COMMIT_SUBJECT.fullmatch(args.commit_message) or not args.commit_message.startswith(
        f"{task_id}: "
    ):
        raise ValueError(f"commit message must start with '{task_id}: '")
    if args.issue <= 0:
        raise ValueError("issue number must be positive")

    selected = {normalize_repo_path(path) for path in args.path}
    task_files = sorted((root / "tasks").glob(f"{task_id}*.md"))
    if len(task_files) != 1:
        raise ValueError(f"expected exactly one task file for {task_id}, found {len(task_files)}")
    task_file = task_files[0].relative_to(root).as_posix()
    if task_file not in selected:
        raise ValueError(f"include the task file in --path: {task_file}")
    task_text = task_files[0].read_text(encoding="utf-8")
    if not re.search(rf"\bissue\s+#{args.issue}\b", task_text, re.IGNORECASE):
        raise ValueError(f"{task_file} must reference GitHub issue #{args.issue}")

    staged, dirty = changed_paths(root)
    if staged:
        raise ValueError(
            f"stage is already populated; review and unstage it before publishing: {sorted(staged)}"
        )
    if dirty:
        omitted = dirty - selected
        if omitted:
            raise ValueError(
                f"unstaged or untracked files were not selected with --path: {sorted(omitted)}"
            )
        verify_open_issue(args.issue, root)
        run(["git", "add", "--", *sorted(selected)], cwd=root)
        staged, _ = changed_paths(root)
        if staged != dirty or task_file not in staged:
            raise ValueError(f"staged checkpoint does not match reviewed changes: {sorted(staged)}")
        scan_staged_changes(root, staged)
        changed_python = sorted(path for path in staged if path.endswith(".py"))
        run_local_gates(root, changed_python)
        run(["git", "commit", "-m", args.commit_message], cwd=root)
        committed_paths = sorted(staged)
        commit_subject = args.commit_message
    else:
        # Resume after a partial publish, such as a successful push followed by
        # a timeout while GitHub was creating or updating the pull request.
        run(
            ["git", "fetch", "origin", "+refs/heads/main:refs/remotes/origin/main"],
            cwd=root,
        )
        committed_paths = sorted(
            set(
                run(["git", "diff", "--name-only", "-z", "origin/main...HEAD"], cwd=root).split(
                    "\0"
                )
            )
            - {""}
        )
        if not committed_paths:
            raise ValueError("there are no changed files to checkpoint or resume")
        if task_file not in committed_paths or not set(committed_paths).issubset(selected):
            raise ValueError(
                "resumed checkpoint paths must explicitly include every branch change and its task file: "
                f"{committed_paths}"
            )
        commit_subject = run(["git", "log", "-1", "--format=%s"], cwd=root)
        if not COMMIT_SUBJECT.fullmatch(commit_subject) or not commit_subject.startswith(
            f"{task_id}: "
        ):
            raise ValueError(f"latest checkpoint commit must start with '{task_id}: '")
        changed_python = [path for path in committed_paths if path.endswith(".py")]
        run_local_gates(root, changed_python)
        verify_open_issue(args.issue, root)

    run(
        ["git", "fetch", "origin", "+refs/heads/main:refs/remotes/origin/main"],
        cwd=root,
    )
    if (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", "origin/main", "HEAD"], cwd=root, check=False
        ).returncode
        != 0
    ):
        raise ValueError(
            "task branch is behind or diverged from origin/main; update it before publishing"
        )
    run(["git", "push", "--set-upstream", "origin", branch], cwd=root)
    head_sha = run(["git", "rev-parse", "HEAD"], cwd=root)
    verify_required_checks(root)

    body = checkpoint_pr_body(task_id, args.issue, commit_subject, committed_paths, head_sha)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as stream:
        stream.write(body)
        body_path = Path(stream.name)
    try:
        prs = open_or_merged_pr(branch, root)
        active = [pr for pr in prs if pr["state"] == "OPEN"]
        merged = [pr for pr in prs if pr["state"] == "MERGED"]
        closed = [pr for pr in prs if pr["state"] == "CLOSED"]
        if len(active) > 1 or len(merged) > 1 or (active and merged):
            raise ValueError(f"multiple non-closed PRs found for task branch {branch}")
        if merged:
            return f"Checkpoint PR already merged: {merged[0]['url']}"
        if closed:
            raise ValueError(
                f"existing PR #{closed[0]['number']} is closed without merge; review before retrying"
            )
        title = args.pr_title or commit_subject
        if active:
            number = str(active[0]["number"])
            run(
                ["gh", "pr", "edit", number, "--title", title, "--body-file", str(body_path)],
                cwd=root,
            )
        else:
            run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--base",
                    "main",
                    "--head",
                    branch,
                    "--title",
                    title,
                    "--body-file",
                    str(body_path),
                ],
                cwd=root,
            )
    finally:
        body_path.unlink(missing_ok=True)

    prs = [pr for pr in open_or_merged_pr(branch, root) if pr["state"] == "OPEN"]
    if len(prs) != 1:
        raise RuntimeError(f"expected one open PR after publication, found {len(prs)}")
    number = str(prs[0]["number"])
    details = json.loads(
        run(
            ["gh", "pr", "view", number, "--json", "isDraft,headRefName,baseRefName,headRefOid"],
            cwd=root,
        )
    )
    if (
        details.get("isDraft")
        or details.get("headRefName") != branch
        or details.get("baseRefName") != "main"
    ):
        raise ValueError("PR is draft or has an unexpected branch/base")
    if details.get("headRefOid") != head_sha:
        raise ValueError("PR head SHA differs from the published checkpoint")
    run(["gh", "pr", "merge", number, "--auto", "--squash"], cwd=root)
    return f"Published {task_id} for issue #{args.issue}: {prs[0]['url']} at {head_sha} (auto-merge requested)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--commit-message", required=True)
    parser.add_argument("--pr-title")
    parser.add_argument(
        "--path", action="append", required=True, help="explicit changed file; repeat per file"
    )
    args = parser.parse_args()
    try:
        print(publish(args))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Checkpoint publication stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
