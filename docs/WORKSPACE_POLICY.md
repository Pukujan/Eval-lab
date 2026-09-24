# Eval Lab workspace and dependency policy

## Ownership

`D:\claude\eval-lab` is the sole local checkout for this project on the
owner's Windows machine. GitHub is the durable source of committed history;
this directory is the only local working copy. A branch is a Git reference,
not a reason to create another directory.

Do not create another Eval Lab clone or task-specific project folder. Work in
the canonical checkout by default. A temporary linked worktree is allowed
only when genuine isolation or parallel work requires it, and only at
`D:\claude\eval-lab\worktrees\<task-id>`. Keep one active task per worktree;
if the checkout or GitHub is unavailable, stop and report the blocker.

## Branch and checkpoint workflow

1. Create or update a GitHub issue with the requested change and acceptance
   criteria before implementation. Record the issue number in its task file.
   Use sub-issues only to split independently deliverable work.
2. Confirm the repository root is canonical and run the workspace guard.
   Fetch `origin`; use current `main` as the task branch base.
3. At a checkpoint, update the task file and `checkpoints/CURRENT.md` when the
   repository-wide next action changes. Use `scripts/publish_checkpoint.py`
   with explicit paths to run the same lock, contract, workspace, lint,
   formatting, type, test, and build gates as CI; it scans staged paths/content
   for likely secrets/private benchmark data, commits, pushes the task branch,
   upserts the PR, and requests auto-merge. It returns while GitHub CI runs.
4. The PR states `Task issue: #<number>`. Keep the issue open until the
   finalizer verifies the exact PR head, merge SHA, required CI checks, and any
   worktree cleanup; then it records the outcome and closes the issue.
5. `main` requires a PR, up-to-date branch, and the Python 3.11/3.12 checks.
   `CODEOWNERS` identifies sensitive benchmark methodology/data, paid-run
   scripts, credentials, workflow permissions, dependencies, and releases.
   GitHub currently has no independent code owner who can review this account's
   PRs; add an independent reviewer before requiring code-owner approvals.
   Routine reversible changes can auto-merge after CI.
6. Before switching tasks, ensure the task branch is pushed and the working
   tree is clean. Use `D:\claude\eval-lab\worktrees\<task-id>` for genuine
   parallel work. Before cleanup, inspect tracked, untracked, and ignored state;
   preserve unique work. Never use forced cleanup.

Pushes are the normal durability boundary. Never push secrets, private
benchmark material, or user data. If a checkpoint scanner flags content or a
coherent checkpoint cannot safely be pushed, record why and stop before
switching tasks or cleaning files.

## One dependency environment

- Install `uv` once as a machine-level tool; do not install a separate copy per
  task or checkout.
- Keep one project environment at `D:\claude\eval-lab\.venv`, created and
  synchronized from the root `pyproject.toml` and committed `uv.lock`.
- Use `uv sync --extra dev` to synchronize the canonical environment and
  `.venv\Scripts\python.exe` to run Python checks on Windows.
- Never create or copy `.venv` under a task directory, branch, or worktree.
  This repository is Python-only; do not create `node_modules`. If an approved
  change adds a Node package, keep exactly one root `node_modules` and manage
  it from the root lockfile.
- Reuse uv's machine-level package cache for downloads. Do not copy installed
  packages between folders to simulate sharing.
- Because the one environment is mutable, synchronize dependencies
  sequentially. If a task needs different versions or optional packages, update
  the canonical lock and environment in place, run that task, then restore the
  declared project environment. Do not create a second environment to support
  parallel branches; stop and ask if in-place synchronization would risk
  important work.

## Enforcement and incident handling

Run `python scripts/check_workspace_policy.py --canonical-root
D:\claude\eval-lab` before work and after cleanup. `scripts/check_repo_contract.py`
also rejects additional registered worktrees and dependency directories below
the root. The explicit canonical-root argument additionally catches running
from a second independent clone. The guard is read-only; it reports violations
and never deletes files.

If duplicate directories are discovered, record their exact paths, Git branch
and commit state, tracked/untracked/ignored files, environment identity, and
size in the active task log. Preserve or push unique work before removing only
the redundant checkout/environment. Cleanup is a separate deliberate action,
never a side effect of validation.
