# Eval Lab workspace and dependency policy

## Ownership

`D:\claude\eval-lab` is the sole local checkout for this project on the
owner's Windows machine. GitHub is the durable source of committed history;
this directory is the only local working copy. A branch is a Git reference,
not a reason to create another directory.

Do not create another Eval Lab clone or Git worktree, whether beside the
repository or under `.worktrees`. Do not make a task-specific project folder.
Work is sequential in the canonical checkout, with one task branch active at a
time. If the checkout or GitHub is unavailable, stop and report the blocker.

## Branch and checkpoint workflow

1. Confirm the repository root is the canonical path and run the workspace
   guard before editing.
2. Fetch `origin`; use the current `main` tip as the base for a new task branch
   in this same checkout.
3. Work on one task branch. At each meaningful stopping point, run relevant
   validation, commit a coherent checkpoint, and push that branch to GitHub.
   Open or update its PR to `main`; a completed checkpoint is not closed out
   until all required CI checks pass and the PR is merged.
4. Before switching tasks, confirm the checkpoint is pushed and the working
   tree is clean. Do not create a worktree or stash a second task to work in
   parallel.
5. `main` is protected by a required-PR rule and required Python 3.11/3.12 CI
   checks. Direct pushes and bypasses are disabled; no approval is required for
   the solo maintainer. After merge, fast-forward this checkout to `origin/main`.
   Preserve task branches remotely only when they contain useful review or
   handoff history; local branches do not require extra working folders.
6. Before any cleanup, inspect tracked changes, untracked and ignored files,
   branch-only commits, and artifacts. Preserve unique work before removing a
   directory. Never use forced cleanup to bypass that review.

Pushes are the normal durability boundary. Never push secrets, private
benchmark material, or user data. If a coherent checkpoint cannot safely be
pushed, record why and ask before switching tasks or cleaning its files.

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
