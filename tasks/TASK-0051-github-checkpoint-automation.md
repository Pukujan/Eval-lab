# TASK-0051 — GitHub checkpoint automation and issue tracking

## Status

Active — tracked by GitHub issue #40 on `task/TASK-0051-github-checkpoint-automation`. Implementation and local validation are complete; remote publication, CI, and merge are pending.

## Goal

Make GitHub the authoritative change log and automate the routine path from a completed agent checkpoint to an open PR with auto-merge enabled. GitHub CI and branch protection remain authoritative merge gates. Agents must confirm merge before closing the task or removing a temporary worktree.

## Decisions

- Use GitHub Issues as the project change register. Create or update an issue before implementation; reference its issue number in the task file, checkpoint, PR, and handoff. Use sub-issues only when a parent task has multiple independently deliverable child tasks.
- Keep this task as issue #40, a standalone task for now. No related umbrella issue currently exists.
- Commit and push only the current task branch. Open or update its PR and request GitHub auto-merge; never push directly to `main` or merge around required checks.
- Publish asynchronously: once the checkpoint is committed, pushed, and auto-merge requested, return the PR and monitoring state. Confirm the merged PR in a later step before marking complete or cleaning a linked worktree.
- Temporary linked worktrees live only in `D:\claude\eval-lab\worktrees\<task-id>` and are removed with normal Git operations after merge and a full state check.
- The default environment remains the canonical root `.venv`; a managed Gravebuster pnpm/uv runtime is a separate requirement whose exact host path and execution boundary are not yet confirmed. Do not install or migrate runtimes in this task.
- Preserve required Python 3.11/3.12 CI checks and main protection. Repository auto-merge is enabled; auto-merge may proceed only when required checks pass. No bypass permissions are added.
- `CODEOWNERS` identifies sensitive paths. GitHub currently has only the PR owner's account as a collaborator, so non-author code-owner approval cannot be enforced until an independent reviewer is added; routine PR auto-merge remains gated by the required CI checks.

## Files in scope

- `tasks/TASK-0051-github-checkpoint-automation.md`
- `checkpoints/CURRENT.md`
- `AGENTS.md`
- `scripts/check_workspace_policy.py`
- `tests/test_workspace_policy.py`
- `scripts/publish_checkpoint.py`
- `scripts/finalize_checkpoint.py`
- `tests/test_checkpoint_automation.py`
- `D:\claude\AGENTS.md`
- `D:\claude\PROJECT_ROOTS.md`
- `D:\claude\check-canonical-workspaces.ps1`
- `.github/ISSUE_TEMPLATE/task.yml`
- `.github/pull_request_template.md`
- `.github/CODEOWNERS`
- `.github/workflows/task-merged.yml`
- `docs/WORKSPACE_POLICY.md`
- `docs/CI_CD.md`

Update this list before editing any additional file.

## Acceptance criteria

- The repo and D: workspace policies consistently require GitHub issue tracking and use `D:\claude\eval-lab\worktrees` for temporary Eval Lab worktrees.
- An issue template captures objective, acceptance criteria, scope, risk, and validation. PRs link their issue without closing it; finalization closes the issue only after merge verification.
- A tested publisher commits explicitly selected checkpoint files, pushes only the active task branch, creates or updates its PR, and enables auto-merge without waiting for CI.
- Publishing stops on dirty/unselected state, wrong branch, missing task/issue context, failed validation, or unavailable GitHub authentication; it never bypasses main protection.
- A tested finalizer confirms the PR is merged, audits tracked, untracked, and ignored worktree state, removes only a clean temporary worktree normally, and synchronizes the canonical checkout with `origin/main`.
- Required Python 3.11 and 3.12 checks remain required; repo auto-merge is enabled and main protection remains intact.
- The task checkpoint and issue are updated with exact files, commands, checks, decisions, and next action.

## Handoff

The task remains active until its PR is merged and the GitHub issue reflects the final state. If publishing stops after a commit or push, rerun the publisher with the same explicit paths to resume; do not create a second checkpoint or PR.

## Checkpoint log

- 2026-09-23: Opened GitHub issue #40 before implementation. The issue list had no existing parent that fit, so #40 remains standalone; decompose into GitHub sub-issues only if the task splits into separately deliverable work.
- 2026-09-23: Repository is clean on `main` at `bc777271`, equal to `origin/main`; PR #39 merged and both required Python CI matrices passed. Main requires PRs and `quality (Python 3.11)` / `quality (Python 3.12)` checks. No active linked worktrees exist.
- 2026-09-23: Workspace policy guard passed before task work.
- 2026-09-23: Implemented the explicit-path publisher, async auto-merge request, exact-head/CI merge-record workflow, safe finalizer, issue/PR templates, CODEOWNERS map, and `D:\claude\eval-lab\worktrees` policy. Finalizer checks the canonical checkout before removing a linked worktree.
- 2026-09-23: Updated `D:\claude\AGENTS.md`, `D:\claude\PROJECT_ROOTS.md`, and `D:\claude\check-canonical-workspaces.ps1`. `D:\claude` has only this account as a repository collaborator; owner approval cannot be enforced until an independent reviewer is added. The CODEOWNERS review rule therefore remains disabled to avoid making sensitive PRs unmergeable.
- 2026-09-23: Local gates passed: `uv lock --check`; `uv sync --locked --extra dev`; repo contract; canonical workspace policy; `ruff check .`; changed-Python Ruff format check; `mypy src/eval_lab`; full pytest (`157 passed`); `uv build`; and `git diff --check`. One initial format check failed; the three files were formatted and the complete run passed.

## Exact files changed

- `.github/CODEOWNERS`
- `.github/ISSUE_TEMPLATE/task.yml`
- `.github/pull_request_template.md`
- `.github/workflows/task-merged.yml`
- `AGENTS.md`
- `checkpoints/CURRENT.md`
- `docs/CI_CD.md`
- `docs/WORKSPACE_POLICY.md`
- `scripts/check_workspace_policy.py`
- `scripts/finalize_checkpoint.py`
- `scripts/publish_checkpoint.py`
- `tasks/TASK-0051-github-checkpoint-automation.md`
- `tests/test_checkpoint_automation.py`
- `tests/test_workspace_policy.py`
- `D:\claude\AGENTS.md`
- `D:\claude\PROJECT_ROOTS.md`
- `D:\claude\check-canonical-workspaces.ps1`

## Next atomic action

Update issue #40 with the implemented lifecycle and verified results, publish this branch, then wait for GitHub CI and auto-merge before finalizing.


