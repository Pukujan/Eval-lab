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

## One canonical checkout; temporary in-root task worktrees

The sole durable local Eval Lab checkout is `D:\claude\eval-lab`. Do not
create another clone, copied project directory, or task-named sibling
checkout. Work in the canonical folder by default. A temporary linked
worktree is allowed when a task genuinely needs isolation or parallel work;
create it only at `D:\claude\eval-lab\worktrees\<task-id>`. Keep worktrees
limited to active tasks and remove them after their work is durably checkpointed
and complete.

Branch format:

```
task/TASK-0001-short-name
```

Before switching task branches in the canonical checkout, finish a coherent
checkpoint, commit it, push it to GitHub, and confirm the working tree is clean.
Use a separate in-root worktree when parallel tasks need independent working
trees; do not stash work to make parallel tasks appear safe. Each task branch
uses the `task/TASK-0001-short-name` format. When idle on `main`, fetch and
fast-forward the canonical checkout to `origin/main`; do not create a second
directory to preserve an old branch.

Never run `git clone` for Eval Lab. Never create a linked worktree outside
`D:\claude\eval-lab\worktrees`. If GitHub or the current checkout is
unavailable, stop and report the blocker rather than creating another local
copy.

When a worktree task is complete, verify its branch and all tracked,
untracked, and ignored state. Push the checkpoint and open/update its PR; wait
for required CI and merge the PR before closing the task. Preserve any unique
state that is not in Git. Remove the clean worktree with a normal, non-forced
`git worktree remove`, then confirm it is absent from `git worktree list` and
the canonical checkout is synchronized with `origin/main`. Do not remove an
active task worktree merely because its branch has been pushed.

A task may modify only the files declared in its task file unless the task file is updated first.

## One canonical dependency environment

Use the one canonical repository-root `.venv`, managed by the single `uv`
executable available on `PATH`. Resolve and synchronize from the root
`pyproject.toml` and `uv.lock` with `uv sync --extra dev`; run Python tools
through `.venv\Scripts\python.exe` on Windows. A task worktree must reuse this
environment; do not make task-specific virtual environments or copy `.venv`.
Verify that tools import the worktree's source, not the canonical checkout's
source. If that cannot be done without another install, serialize the task in
the canonical checkout instead.

This project is Python-only. Do not create `node_modules` here. If a future,
approved change adds a Node package, its single `node_modules` must live at the
repository root and be managed from the root lockfile. A worktree may resolve
that root install, but must never install dependencies locally. If the task
changes dependency requirements incompatibly, serialize and synchronize the
canonical environment in place. Use package-manager caches for download reuse,
not duplicate project installs.

Tasks are serialized because `.venv` is mutable. If a branch changes dependency
requirements, update the single lockfile and synchronize the same `.venv`
before running the task. Never create another environment as a workaround; if
the change cannot be handled safely in the canonical environment, stop and ask.

### TASK-0053 remote model-runtime exception

For TASK-0053 only, an upstream model runtime that requires incompatible
dependencies may use an isolated runtime environment on the user's Apple
Silicon Mac. Keep that environment and downloaded weights outside every Eval
Lab checkout; do not clone or copy the repository to the Mac. Pin the runtime
and model revisions in the experiment artifacts, run one model at a time, and
retain or remove runtime state only as documented in the task checkpoint. This
exception is for model inference only and does not create another project
dependency environment.

Run `python scripts/check_workspace_policy.py --canonical-root D:\claude\eval-lab`
before task work and after cleanup. The repository contract check also enforces
the canonical path, in-root temporary-worktree placement, and one-environment
rules.

## GitHub issue and checkpoint policy

GitHub Issues are the authoritative change log. Create or update an issue
before implementation, and put its number in the task file. Use a GitHub
sub-issue only when a parent task has independently deliverable child tasks;
do not maintain a second issue register in the repository.

GitHub is the durable record for committed task progress; local folders are
working state, not backup. At each meaningful stopping point, update the task
file and, when the repository-wide next action changes, `checkpoints/CURRENT.md`.
Use `scripts/publish_checkpoint.py` with explicit paths to run local gates, make
the checkpoint commit, push only the task branch, create or update its PR, and
request GitHub auto-merge. The publisher returns while required CI runs; agents
may continue or hand off asynchronously. The PR must reference its issue;
close it only after finalization. A merged-PR workflow records the exact PR
head and merge SHA. Task PRs auto-merge after the required CI checks. Never
push directly to `main` or bypass a failed or missing required check.

A checkpoint is complete only after GitHub confirms its PR merged with required
CI successful. Do not leave completed work or handoff state only in chat or a
local branch. After merge, run
`scripts/finalize_checkpoint.py` to confirm the merge, audit tracked,
untracked, and ignored state, remove a clean linked worktree normally, and
fast-forward the canonical checkout to `origin/main`. Never force-remove a
worktree or discard unique state.

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
