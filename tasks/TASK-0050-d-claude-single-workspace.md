# TASK-0050 — D:\claude single-workspace policy and reconciliation

## Status

Active — one canonical checkout per repository remains the rule, with temporary
linked worktrees allowed only inside that checkout's `.worktrees\<task-id>`
when parallel isolation is genuinely needed. Completed, clean worktrees must be
removed after the checkpoint is pushed and the required PR/CI/merge gate is
complete. No sibling clones or persistent copies are allowed. Each repository
uses one canonical dependency environment; declared nested repositories own
their own environment. Physical consolidation is incomplete: some duplicate
paths still contain active, unique, ignored, inaccessible, or malformed state.
TASK-0049 merged as PR #36 at `c80207b`; the earlier TASK-0050 policy records
merged as PRs #37 and #38. This follow-up preserves TASK-0048 and TASK-0049
history.

## Goal

Make one registered canonical folder per repository identity the durable local
project root anywhere under `D:\claude`. Prohibit task clones, sibling copies,
and persistent duplicate checkouts. Permit temporary Git linked worktrees only
under that project's `.worktrees\<task-id>` directory when needed for
parallelism or isolation, and remove them after durable checkpoint/PR/CI/merge
and preservation of any user state. Add a read-only guard that detects
unregistered roots, out-of-root or missing worktrees, duplicate dependency
installs per repository, and incomplete scans. Reconcile existing
copies only after unique commits, tracked changes, untracked/ignored files,
runtime references, and task ownership are accounted for. Preserve distinct
repositories, declared submodules, and named data stores.

## Decisions

- `D:\claude\eval-lab` is the only durable Eval Lab checkout. A temporary
  linked worktree may be used only when parallel isolation is genuinely needed
  and must be placed under `D:\claude\eval-lab\.worktrees\<task-id>`.
- One canonical folder per remote does not mean sharing mutable dependencies
  between different repositories. Each project follows its own manifest and
  lockfile in its canonical folder.
- Do not create task clones or worktrees outside a registered canonical
  checkout. Temporary worktrees under that checkout's `.worktrees\<task-id>`
  are allowed for active isolated/parallel tasks. Reuse the canonical
  dependency environment; do not create per-worktree `.venv` or `node_modules`.
  After checkpoint push and required PR/CI/merge, preserve any unique or ignored
  state and remove a clean completed worktree through normal Git operations.
  Existing active worktrees remain protected until their owners checkpoint and
  release them.
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
- `D:\claude\check-canonical-workspaces.ps1` (read-only)
- `AGENTS.md` (Eval Lab task/worktree/environment contract)
- `scripts/check_workspace_policy.py`
- `tests/test_workspace_policy.py`
- `D:\claude\archive\workspace-consolidation\CLEANUP_LOG.md`

Update this list before editing any additional file.

## Required work

1. Replace the blanket worktree ban with a clear one-canonical-root policy:
   temporary worktrees may be used for active parallel/isolation tasks only
   under `<canonical-root>\.worktrees\<task-id>`. Document checkpoint,
   push, required PR/CI/merge, clean removal, and canonical-main return steps.
2. Implement a local read-only guard using `PROJECT_ROOTS.md`. Verify each
   registered canonical path and origin remote, detect repeated normalized
   remotes, report any additional Git roots beneath the managed tree, and fail
   on worktrees outside a registered root's `.worktrees` or missing registered
   paths. Preserve explicitly registered nested dependency repositories and
   do not count their environments against the parent repository.
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

- `D:\claude\AGENTS.md`, `PROJECT_ROOTS.md`, and Eval Lab `AGENTS.md` prohibit
  clones and sibling copies, allow only temporary worktrees under the
  canonical checkout's `.worktrees\<task-id>`, and require post-merge cleanup.
- The root guard validates registered remotes and canonical paths, detects
  unregistered roots and out-of-root/missing worktrees, permits active in-root
  task worktrees, exits nonzero on violations or incomplete scans, and does not
  mutate data.
- Distinct projects, the declared Fossil Core submodule, and named data stores
  are not misclassified as duplicates.
- Every known duplicate has a current disposition: safely released after full
  verification, or preserved with an exact blocker and owner action. No unique
  task state or user data is lost.
- TASK-0048's GLEIF handoff and the original TASK-0049 checkpoint/history remain
  intact and discoverable.
- The checkpoint is pushed and merged only after all required CI checks pass.

## Checkpoint log

- 2026-09-23: User clarified the intended worktree lifecycle: temporary linked
  worktrees are allowed for real isolation/parallelism, but only inside the
  canonical repository's `.worktrees\<task-id>`; after durable checkpoint,
  required PR/CI/merge, and preservation of unique state, remove the clean
  worktree. The previous blanket ban is superseded. Four prior subagents were
  confirmed completed but still occupied the concurrency limit until closed;
  they were closed before three read-only audits were run.
- 2026-09-23: Updated the cross-project D: policy and Eval Lab contract to allow
  temporary in-root linked worktrees while prohibiting sibling clones and
  worktree-local dependency installs. Eval Lab's workspace guard and tests now
  accept only direct children of the canonical .worktrees directory and reject
  outside, nested, duplicate, or missing worktree paths. The D: guard now
  exposes environment scan bounds, supports active in-root worktrees, and
  attributes environments to the deepest registered repository so declared
  nested repositories do not count against the parent.
- 2026-09-23: Read-only D: scan command:
  `& D:\claude\check-canonical-workspaces.ps1 -MaximumDepth 12 -MaximumEnvironmentDirectories 50000 -MaximumEnvironmentDepth 24`.
  PowerShell parsing passed. It inspected 5,121 repository-scan directories
  (48 Git roots, 33 registry paths) and 31,168 dependency-scan directories
  (below the 50,000 bound; no dependency-depth or directory-cap truncation).
  The environment inventory found 3 Python environments and 5 node_modules
  directories. The overall run still failed with 65 findings, including
  out-of-root linked worktrees, unregistered Git roots, root-scan depth limits,
  two access-denied paths, and Project Assurance's two populated installs.
  This is not a clean or complete repository-root inventory.
- 2026-09-23: Registered Cortex's SQLFluff gitlink as a nested repository for
  environment accounting: parent external/sqlfluff is index mode 160000,
  pinned at 2a9e943, with origin sqlfluff/sqlfluff. The audited parent lacks a
  .gitmodules mapping and both parent and submodule are dirty; the registry
  entry preserves their separate repository identity but does not fix that
  owner-controlled integration defect. No environment or project state was
  deleted.
- 2026-09-23: Eval Lab validation passed: PowerShell parser; Ruff on the
  workspace-policy implementation/tests; repository contract; workspace
  policy guard; and full pytest (139 passed). Changed Eval Lab files:
  AGENTS.md, scripts/check_workspace_policy.py, tests/test_workspace_policy.py,
  this task file, and checkpoints/CURRENT.md. Cross-project local files changed:
  D:\claude\AGENTS.md, D:\claude\PROJECT_ROOTS.md,
  D:\claude\check-canonical-workspaces.ps1, and the workspace-consolidation
  cleanup log.
- 2026-09-23: Remaining owners/blockers: HOS canonical checkout still has
  uncommitted Issue 23/user state and its project instructions need the revised
  lifecycle; HADES has a large staged checkpoint and two active in-root
  worktrees, all preserved for its owner. Project Assurance's populated
  installs need owner-led manifest/runtime reconciliation. Stupidly Simple
  Cortex and its SQLFluff gitlink both remain dirty and need parent/submodule
  metadata repair. The root repository scan has depth/ACL gaps and 65 findings.
  Next atomic action: complete this Eval Lab PR/CI/merge checkpoint, then
  continue owner-checkpointed consolidation and a fresh full scan.

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
- 2026-09-23: Fresh scan enumerated all eight dependency locations: Eval Lab's
  canonical `.venv`; Cortex `venv` and the separately declared SQLFluff
  `.venv`; `node_modules` in Inference Recommendation Engine, InferHub,
  Design Bakery, and two Project Assurance Modules locations. No install was
  removed. Design Bakery's sibling TASK-0048 checkout remains inaccessible at
  its nested content Git metadata and is preserved pending owner access. The
  full scan found 65 policy violations and remains incomplete due repository
  scan depth/ACL findings.
- 2026-09-23: Luna read-only review caught that the Eval Lab guard accepted
  arbitrary direct-child directory names under `.worktrees`. It now requires
  `TASK-####[-short-name]`; new tests cover invalid task names, absent
  canonical registration, and duplicate registration. Targeted Ruff and
  workspace tests pass (12 tests), and the canonical-root policy guard passes.
  The review agent was closed after completion; a subsequent successful spawn
  confirmed the concurrency pool had reopened, and that reviewer was also
  closed immediately.
- 2026-09-23: Final local gates pass after the review-driven refinement:
  `scripts/check_repo_contract.py`, `ruff check .`, full pytest (142 passed),
  `scripts/check_workspace_policy.py --canonical-root D:\claude\eval-lab`,
  and `git diff --check`. No dependency synchronization was needed because
  manifests and lockfiles were unchanged. The D: root scan remains non-clean;
  its violations are documented in the cleanup log.
- 2026-09-23: Commit `7cd02fa` was pushed and PR #39 opened. The first remote CI
  run failed both Python-version jobs at `ruff format --check` on two long test
  assertions; repository contract, workspace policy, and Ruff lint passed.
  Applied Ruff formatting to both changed Python files; formatter check, lint,
  and the focused 12-test suite now pass locally. Next atomic action: commit/
  push the formatting correction, then rerun and require both full CI jobs
  before merging PR #39.

## Handoff

Commit and push this follow-up from the existing canonical checkout; open the
required PR, wait for CI, and merge. Then continue owner-led cleanup of Hades,
HOS, and other active paths, and resolve Project Assurance/SQLFluff into one
declared environment only after their owners' runtime requirements are known.
