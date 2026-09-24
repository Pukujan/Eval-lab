from __future__ import annotations

from pathlib import Path

import pytest

from scripts import finalize_checkpoint
from scripts.finalize_checkpoint import (
    TASK_DIRECTORY,
    passing_required_checks,
    validate_worktree_path,
)
from scripts.publish_checkpoint import (
    checkpoint_pr_body,
    normalize_repo_path,
    scan_staged_changes,
    task_id_from_branch,
)


def test_task_branch_produces_task_id() -> None:
    assert task_id_from_branch("task/TASK-0051-github-checkpoint-automation") == "TASK-0051"


@pytest.mark.parametrize("branch", ["main", "TASK-0051-topic", "task/TASK-51-topic"])
def test_non_task_branch_is_rejected(branch: str) -> None:
    with pytest.raises(ValueError, match="expected a task branch"):
        task_id_from_branch(branch)


def test_checkpoint_paths_are_repository_relative() -> None:
    assert normalize_repo_path("./scripts/publish_checkpoint.py") == "scripts/publish_checkpoint.py"
    with pytest.raises(ValueError, match="repository-relative"):
        normalize_repo_path("../outside.txt")


def test_pr_body_links_issue_without_closing_before_finalization() -> None:
    body = checkpoint_pr_body(
        "TASK-0051",
        40,
        "TASK-0051: add checkpoint automation",
        ["AGENTS.md", "tasks/TASK-0051.md"],
        "abc123",
    )
    assert "Task issue: #40" in body
    assert "Closes #40" not in body
    assert "TASK-0051" in body
    assert "`AGENTS.md`" in body
    assert "required CI" in body


@pytest.mark.parametrize("path", [".env", "config/.env.production", "data/private-benchmark.json"])
def test_publisher_rejects_secret_or_private_paths(
    path: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import publish_checkpoint

    monkeypatch.setattr(publish_checkpoint, "run", lambda *_args, **_kwargs: "")
    with pytest.raises(ValueError, match="possible secret/private content"):
        scan_staged_changes(tmp_path, {path})


@pytest.mark.parametrize(
    "line",
    [
        "+GH_TOKEN=github_pat" + "_123456789012345678901234567890",
        '+api_key = "sk' + '-123456789012345678901234567890"',
    ],
)
def test_publisher_rejects_credential_like_staged_content(
    line: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import publish_checkpoint

    monkeypatch.setattr(publish_checkpoint, "run", lambda *_args, **_kwargs: line)
    with pytest.raises(ValueError, match="possible secret/private content"):
        scan_staged_changes(tmp_path, {"safe.txt"})


def test_task_worktree_names_are_validated() -> None:
    assert TASK_DIRECTORY.fullmatch("TASK-0051-github-checkpoint-automation")
    assert not TASK_DIRECTORY.fullmatch("scratch")


def test_finalizer_path_must_be_canonical_worktrees_child(tmp_path: Path) -> None:
    root = tmp_path / "eval-lab"
    valid = root / "worktrees" / "TASK-0051"
    invalid = root / ".worktrees" / "TASK-0051"
    valid.parent.mkdir(parents=True)
    invalid.parent.mkdir()
    assert validate_worktree_path(root, valid) == valid.resolve()
    with pytest.raises(ValueError, match="outside worktrees"):
        validate_worktree_path(root, invalid)


def test_finalizer_requires_both_ci_matrix_checks() -> None:
    passing = {
        "statusCheckRollup": [
            {"name": "quality (Python 3.11)", "conclusion": "SUCCESS"},
            {"name": "quality (Python 3.12)", "conclusion": "SUCCESS"},
        ]
    }
    failing = {"statusCheckRollup": [{"name": "quality (Python 3.11)", "conclusion": "SUCCESS"}]}
    assert passing_required_checks(passing)
    assert not passing_required_checks(failing)


def test_finalizer_preserves_worktree_when_canonical_checkout_is_dirty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path) -> str:
        calls.append(command)
        if command[:3] == ["gh", "pr", "view"]:
            return (
                '{"state":"MERGED","mergedAt":"2026-09-23T00:00:00Z",'
                '"headRefName":"task/TASK-0051-github-checkpoint-automation",'
                '"headRefOid":"abc123","baseRefName":"main",'
                '"mergeCommit":{"oid":"def456"},'
                '"statusCheckRollup":['
                '{"name":"quality (Python 3.11)","conclusion":"SUCCESS"},'
                '{"name":"quality (Python 3.12)","conclusion":"SUCCESS"}],'
                '"body":"Task issue: #40"}'
            )
        if command[:3] == ["git", "worktree", "list"]:
            return f"worktree {root}\nworktree {root / 'worktrees' / 'TASK-0051'}"
        if command == ["git", "branch", "--show-current"]:
            return "task/TASK-0051-github-checkpoint-automation"
        if command == ["git", "rev-parse", "HEAD"]:
            return "abc123"
        if command[:3] == ["git", "status", "--porcelain=v1"]:
            return "?? keep-me.txt"
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(finalize_checkpoint, "run", fake_run)
    root = tmp_path / "eval-lab"
    with pytest.raises(ValueError, match="canonical checkout has local changes"):
        finalize_checkpoint.finalize(42, 40, root, root / "worktrees" / "TASK-0051")

    assert not any(command[:3] == ["git", "worktree", "remove"] for command in calls)


def test_finalizer_updates_remote_tracking_ref_before_comparing_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []
    task_branch = "task/TASK-0051-finalizer-ref-sync"

    def fake_run(command: list[str], *, cwd: Path) -> str:
        calls.append(command)
        if command[:3] == ["gh", "pr", "view"]:
            return (
                '{"state":"MERGED","mergedAt":"2026-09-24T00:00:00Z",'
                f'"headRefName":"{task_branch}","headRefOid":"abc123",'
                '"baseRefName":"main","mergeCommit":{"oid":"def456"},'
                '"statusCheckRollup":['
                '{"name":"quality (Python 3.11)","conclusion":"SUCCESS"},'
                '{"name":"quality (Python 3.12)","conclusion":"SUCCESS"}],'
                '"body":"Task issue: #40"}'
            )
        if command == ["git", "status", "--porcelain=v1", "--untracked-files=all"]:
            return ""
        if command == ["git", "rev-parse", f"refs/heads/{task_branch}"]:
            return "abc123"
        if command == ["git", "branch", "--show-current"]:
            return task_branch
        if command == ["git", "rev-parse", "HEAD"]:
            return "def456"
        if command == ["git", "rev-parse", "origin/main"]:
            return "def456"
        if command == ["git", "fetch", "origin", "+refs/heads/main:refs/remotes/origin/main"]:
            return ""
        if command[:2] in (["git", "switch"], ["git", "pull"]) or command[:3] == [
            "gh",
            "issue",
            "close",
        ]:
            return ""
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(finalize_checkpoint, "run", fake_run)
    result = finalize_checkpoint.finalize(42, 40, tmp_path / "eval-lab", None)

    assert "issue #40 updated" in result
    assert ["git", "fetch", "origin", "+refs/heads/main:refs/remotes/origin/main"] in calls
