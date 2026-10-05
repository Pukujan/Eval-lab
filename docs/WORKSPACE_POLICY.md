# Eval Lab workspace and dependency policy

## Ownership

`D:\development\eval-lab` is the sole local checkout for this project on the
owner's Windows machine. GitHub is the durable source of committed history;
this directory is the only local working copy. A branch is a Git reference,
not a reason to create another directory.

`D:\development` holds only the main checkout of each repository. Do not
create a Git worktree, another Eval Lab clone, or a task-specific project folder
under `D:\development`. Scratch files, helper-repository clones and temporary
output live outside `D:\development` (for example `C:\work` or `%TEMP%`).
Tasks are serialized in the one checkout. If the checkout or GitHub is
unavailable, stop and report the blocker.

## Branch and checkpoint workflow

1. Create or update a GitHub issue with the requested change and acceptance
   criteria before implementation. Record the issue number in its task file.
   Use sub-issues only to split independently deliverable work.
2. Confirm the repository root is canonical and run the workspace guard.
   Fetch `origin`; use current `main` as the task branch base.
3. At a checkpoint, update the task file and `checkpoints/CURRENT.md` when the
   repository-wide next action changes. Use `scripts/publish_checkpoint.py`
   with explicit paths to run the same lock, contract, workspace, lint,
   formatting, type, test, and build gates as CI, commits, pushes the task
   branch, upserts the PR, and requests auto-merge. It returns while GitHub CI
   runs.
4. The PR states `Task issue: #<number>`. Keep the issue open until the
   finalizer verifies the exact PR head, merge SHA, and required CI checks;
   then it records the outcome and closes the issue.
5. `main` requires a PR, an up-to-date branch, the Python 3.11/3.12 `quality`
   checks (branch protection) and the aggregate `gates` check (ruleset `main
   protection`); force-pushes and deletion are blocked. Task PRs auto-merge only
   when all required checks pass.
6. Before switching tasks, ensure the task branch is pushed and the working
   tree is clean. Before cleanup, inspect tracked, untracked, and ignored state;
   preserve unique work. Never use forced cleanup.

Pushes are the normal durability boundary.

## One dependency environment

- Install `uv` once as a machine-level tool; do not install a separate copy per
  task or checkout.
- Keep one project environment at `D:\development\eval-lab\.venv`, created and
  synchronized from the root `pyproject.toml` and committed `uv.lock`.
- Use `uv sync --extra dev` to synchronize the canonical environment and
  `.venv\Scripts\python.exe` to run Python checks on Windows.
- Never create or copy `.venv` under a task directory or branch.
  This repository is Python-only; do not create `node_modules`. If an approved
  change adds a Node package, keep exactly one root `node_modules` and manage
  it from the root lockfile.
- `D:` is NTFS (it was exFAT before October 2026). No copy-mode, hoisted-linker,
  or virtual-store workarounds are needed or allowed in package-manager config.
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
D:\development\eval-lab` before work and after cleanup. `scripts/check_repo_contract.py`
also rejects any registered linked worktree and nested dependency directories
below the root. The explicit canonical-root argument additionally catches running
from a second independent clone. The guard is read-only; it reports violations
and never deletes files.

If duplicate directories are discovered, record their exact paths, Git branch
and commit state, tracked/untracked/ignored files, environment identity, and
size in the active task log. Preserve or push unique work before removing only
the redundant checkout/environment. Cleanup is a separate deliberate action,
never a side effect of validation.
