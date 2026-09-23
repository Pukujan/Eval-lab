# Agent Operating Contract

This repository is designed to be usable by multiple independent agents without shared chat history.

## Read order

Before doing work, read only:

1. `PROJECT.md`
2. `checkpoints/CURRENT.md`
3. the assigned `tasks/TASK-*.md`
4. the minimum design document needed for the task:
   - product scope: `docs/PDD.md`
   - system design: `docs/SDD.md`
   - testing: `docs/TDD.md`
   - experiment rules: `docs/EXPERIMENT_PROTOCOL.md`
5. for README, marketing, UX writing, image-generation, or HTML-demo work, read the relevant `.content-system/` adapter files and the pinned helper version before producing output.

Do not scan unrelated historical files or experiments unless the task explicitly requires them.

## One canonical checkout; no clones or worktrees

The sole local Eval Lab checkout is `D:\claude\eval-lab`. Work on every task
inside that directory. Do not create another clone, linked worktree, task
directory, or sibling checkout. Tasks run sequentially in this one working
directory; a task branch is allowed, but it must reuse this checkout.

Branch format:

```
task/TASK-0001-short-name
```

Before switching task branches, finish a coherent checkpoint, commit it, push
it to GitHub, and confirm the working tree is clean. Do not stash work to make
parallel tasks appear safe. When idle on `main`, fetch and fast-forward this
checkout to `origin/main`; do not create a second directory to preserve an old
branch.

Never run `git worktree add` or `git clone` for Eval Lab. If GitHub or the
current checkout is unavailable, stop and report the blocker rather than
creating another local copy.

A task may modify only the files declared in its task file unless the task file is updated first.

## One canonical dependency environment

Use the one repository-root `.venv`, managed by the single `uv` executable
available on `PATH`. Resolve and synchronize from the root `pyproject.toml` and
`uv.lock` with `uv sync --extra dev`; run Python tools through
`.venv\Scripts\python.exe` on Windows. Do not make task-specific virtual
environments, install dependencies into a worktree, or copy `.venv`.

This project is Python-only. Do not create `node_modules` here. If a future,
approved change adds a Node package, its single `node_modules` must live at the
repository root and be managed from the root lockfile; never install per task.
Use package-manager caches for download reuse, not duplicate project installs.

Tasks are serialized because `.venv` is mutable. If a branch changes dependency
requirements, update the single lockfile and synchronize the same `.venv`
before running the task. Never create another environment as a workaround; if
the change cannot be handled safely in the canonical environment, stop and ask.

Run `python scripts/check_workspace_policy.py --canonical-root D:\claude\eval-lab`
before task work and after cleanup. The repository contract check also enforces
the one-worktree and one-environment rules.

## GitHub checkpoint policy

GitHub is the durable record for committed task progress; local folders are
working state, not backup. At each meaningful stopping point, validate, commit,
and push the coherent checkpoint to its task branch, then open or update its PR
to `main`. A completed checkpoint is not complete until its PR is merged after
all required CI checks pass. Do not switch to another task with a completed
checkpoint unmerged, or leave completed work or handoff state only on a local
branch. Interim work may remain in the same open PR while a task is active.
Before pushing, verify that no credentials, private benchmark material, or user
data are included. After a task is merged, fast-forward the same canonical
checkout to `origin/main`.

## Required checkpoint behavior

At every meaningful stopping point, update the task file with:

- status
- completed work
- exact files changed
- commands run
- test results
- decisions made
- unresolved questions
- next atomic action

If the task becomes blocked, write the blocker before stopping.

When the repository-wide next action changes, update `checkpoints/CURRENT.md`.

## Commit rule

A commit should represent one coherent checkpoint. Commit message:

```
TASK-0001: concise checkpoint description
```

Never leave important state only in a chat transcript.

## Experiment rule

Every experiment must have a directory under `experiments/` and follow `docs/EXPERIMENT_PROTOCOL.md`.

Never overwrite completed experiment results. Create a new experiment ID for a changed dataset, rubric, model, prompt, seed, calibration method, or evaluation protocol.

## Ground-truth rule

Model judgments are never promoted to objective gold merely because the model is strong.

Gold labels must identify their provenance:

- deterministic verifier
- benchmark answer key
- executable test
- human adjudication
- explicitly marked weak/model supervision

## Safety and secrets

Never commit API keys, tokens, private benchmark material, or user data. Use environment variables and local `.env` files ignored by Git.
