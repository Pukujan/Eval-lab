# TASK-0050 — D:\claude single-workspace policy and reconciliation

## Status

Active — the cross-project `D:\claude\AGENTS.md` now prohibits task clones,
copies, and Git worktrees and requires one canonical root dependency
environment per project. `D:\claude\PROJECT_ROOTS.md` and the read-only
`D:\claude\check-canonical-workspaces.ps1` guard are updated. Physical
consolidation is not complete: current same-project paths still contain active,
unique, ignored, inaccessible, or malformed state. TASK-0049 merged as PR #36
at `c80207b`; this task's root-policy record merged as PR #37 at `6dd2674`.
This follow-up preserves TASK-0048 and TASK-0049 history.

## Goal

Make one registered canonical folder per repository identity the only local
working checkout anywhere under `D:\claude`. Prohibit task clones and all Git
worktrees, require serial work in canonical folders, and add a read-only local
guard that detects unregistered repository copies and registered worktrees.
Reconcile existing copies only after unique commits, tracked changes,
untracked/ignored files, runtime references, and task ownership are accounted
for. Preserve distinct repositories, declared submodules, and named data
stores.

## Decisions

- `D:\claude\eval-lab` is the only Eval Lab checkout; use a task branch in that
  existing directory and do not create another worktree.
- One canonical folder per remote does not mean sharing mutable dependencies
  between different repositories. Each project follows its own manifest and
  lockfile in its canonical folder.
- No task worktrees are allowed, including under `.worktrees` or legacy
  `D:\claude\worktrees`. Existing active worktrees remain protected until
  their owners checkpoint and release them.
- A duplicate path is not disposable merely because it shares a remote or
  commit. Do not remove, move, or overwrite any path with unique, inaccessible,
  dirty, ignored, referenced, or unverified state.
- The root policy guard is read-only. It reports blockers and never performs
  cleanup.
- Treat a bounded or access-limited scan as incomplete; do not report a clean
  inventory unless the guard finishes without depth, directory-limit, or ACL
  findings. No project or environment folder is removed before its unique
  state and live references are checked.
- GitHub remains the durable record: checkpoint commits are pushed, validated
  through required CI, and merged by PR before a task is closed or its local
  state is released.

## Files in scope

- `tasks/TASK-0050-d-claude-single-workspace.md`
- `tasks/TASK-0049-single-workspace-policy.md` (status/handoff closeout only;
  preserve its incident log, decisions, and checkpoint history)
- `checkpoints/CURRENT.md` (add this follow-up without deleting prior handoffs)
- `D:\claude\AGENTS.md`
- `D:\claude\PROJECT_ROOTS.md`
- `D:\claude\check-canonical-workspaces.ps1` (new, read-only)
- `D:\claude\archive\workspace-consolidation\CLEANUP_LOG.md`

Update this list before editing any additional file.

## Required work

1. Replace cross-project permission for task worktrees with a clear serial,
   canonical-folder-only policy. Document how to work on multiple tasks by
   checkpointing, pushing, switching branches in place, and returning to the
   canonical main branch.
2. Implement a local read-only guard using `PROJECT_ROOTS.md`. Verify each
   registered canonical path and origin remote, detect repeated normalized
   remotes, report any additional Git roots beneath the managed tree, and fail
   when any canonical repository registers a linked worktree. Preserve
   explicitly registered nested dependency repositories.
3. Re-audit known same-project paths from the cleanup log using current Git and
   filesystem state. Separate verified-safe stale copies from active or
   protected state, and request owner checkpoint/release through the existing
   task when needed. Do not use forced or alternate-shell deletion if the
   supported Windows operation is denied.
4. Record exact findings, commands, validation, completed releases, and
   blockers in the cleanup log and this task file. Keep the earlier TASK-0049
   incident evidence intact.
5. Commit and push coherent checkpoints on this task branch, pass required
   Eval Lab CI, merge through a PR, then fast-forward this same checkout.

## Acceptance criteria

- `D:\claude\AGENTS.md` and `PROJECT_ROOTS.md` unambiguously prohibit clones,
  copies, and Git worktrees for task isolation; task branches run in the single
  canonical folder.
- The root guard validates registered remotes and canonical paths, detects
  unregistered repository roots and any linked worktree, exits nonzero on
  violations, and does not mutate data.
- Distinct projects, the declared Fossil Core submodule, and named data stores
  are not misclassified as duplicates.
- Every known duplicate has a current disposition: safely released after full
  verification, or preserved with an exact blocker and owner action. No unique
  task state or user data is lost.
- TASK-0048's GLEIF handoff and the original TASK-0049 checkpoint/history remain
  intact and discoverable.
- The checkpoint is pushed and merged only after all required CI checks pass.

## Checkpoint log

- 2026-09-23: Confirmed PR #36 is merged at `c80207b`; GitHub `main` and the
  canonical local checkout match. Main requires PRs and the exact Python 3.11
  and Python 3.12 quality checks, with administrator enforcement and no force
  pushes or deletions.
- 2026-09-23: Updated the root policy and `PROJECT_ROOTS.md` to require one
  canonical checkout per repository, serial task branches, no clones or
  worktrees anywhere, and one root dependency environment per project. Added a
  read-only root guard; it does not move or delete files.
- 2026-09-23: `& D:\claude\check-canonical-workspaces.ps1 -MaximumDepth 10`
  scanned 4,509 directories and found 48 Git roots against 32 registered paths.
  It reported 180 findings, including linked worktrees, unregistered roots,
  access-denied paths, and depth limits. The environment pass reached its
  6,000-directory cap (6,001 including the over-limit check), found three
  Python environments and six `node_modules` directories, then marked its
  inventory incomplete. The command exited nonzero as required; this is not a
  clean inventory.
- 2026-09-23: Two independent read-only Luna audits found no current duplicate
  project path safe to release. Hades/Hades Product, Fossil ingest, Research
  Assurance, Lean, and metadata-only/malformed leftovers remain protected by
  task ownership, unique or ignored state, unresolved references, or Windows
  access restrictions. The exact dispositions are appended to
  `D:\claude\archive\workspace-consolidation\CLEANUP_LOG.md`.
- 2026-09-23: A separate shallow environment audit reported 83 environment
  directories, including 74 `node_modules` folders below HOS
  `.controller-runs`. Their contents and references are not yet fully audited;
  the HOS task was asked to checkpoint its existing dirty work before aligning
  project instructions and reviewing these installs. The Hades task was also
  asked to checkpoint and reconcile in its canonical folder. No folders were
  deleted or moved.
- 2026-09-23: Confirmed PCM PR #21 (`76fe43b`) made single-checkout the default
  but retained an explicit linked-worktree opt-in. The D-drive root policy
  prohibits that option locally. HOS's project-level instructions still
  contain a D-resident worktree exception; its existing task was notified to
  correct it after checkpointing current work.
- 2026-09-23: TASK-0049's status and handoff were closed out without changing
  its incident log; PR #36 and required Python 3.11/3.12 CI checks are merged.
  The Eval Lab workspace contract passes and `D:\claude\eval-lab\.venv` is its
  only project environment.
- 2026-09-23: Required local gates pass after correcting the task-record
  headings: `python scripts/check_repo_contract.py`, `ruff check .`, and
  `python -m pytest -q` (136 passed). The Eval Lab workspace guard also passes
  for `D:\claude\eval-lab`.
- 2026-09-23: PR #37 passed both required Python 3.11/3.12 checks, merged at
  `6dd26748613e619b71084c72d1ed308aecb8ce44`, and the existing canonical
  checkout fast-forwarded to clean `main`.
- 2026-09-23: Verified and removed 74 empty HOS controller-run
  `node_modules` placeholders plus the matching root placeholder (75 total).
  Each contained only a generated lock stub and five empty folders; no run
  references were found. Controller-run records, results, and parent manifests
  remain untouched. No populated dependency install was removed.
- 2026-09-23: PCM-0013 removed the upstream worktree opt-in. PR #22 merged at
  `368273a`; its append-only checkpoint PR #23 merged at `057f3d4`. New
  projects have no workspace-mode choice; legacy opt-in configs are rejected
  without automatic edits. Required PCM tests and CI passed.
- 2026-09-23: Project Assurance Modules still has two populated installs with
  different packages (Playwright 1.61.1 at root, OpenCode plugin 1.18.15 under
  `.opencode`) and inconsistent pnpm/npm lock metadata. It is unsafe to remove
  either before a one-manager, one-root-lock migration and OpenCode runtime
  verification.
- 2026-09-23: Stupidly Simple Cortex still has separate Python 3.11 and 3.12
  environments with distinct packages and manifests. Its canonical checkout
  contains extensive pre-existing dirty and untracked user state; no files or
  environments were changed. A single-root uv migration requires a declared
  SQLFluff workflow and Python target before it is safe.
- 2026-09-23: HOS still has a project-level D:-worktree exception; its current
  Issue 23 edits were preserved and the owner task was asked to checkpoint
  before updating `AGENTS.md`. Hades' existing task was likewise asked to
  checkpoint before releasing its active paths. No acknowledgement or safe
  release is recorded yet.

## Handoff

Commit and push this follow-up from the existing canonical checkout; open the
required PR, wait for CI, and merge. Then continue owner-led cleanup of Hades,
HOS, and other active paths, and resolve Project Assurance/SQLFluff into one
declared environment only after their owners' runtime requirements are known.
