# Luna Local Program Handoff — TASK-0002 through TASK-0006

## Mission

Complete the authorized v0 program from TASK-0002 through TASK-0006 while using Git as the shared memory between agents.

Do not use old repository history as context. Do not redesign the research question unless a separate design-change task is created.

## Read order at the start of each task

1. `PROJECT.md`
2. `AGENTS.md`
3. `checkpoints/CURRENT.md`
4. active `tasks/TASK-XXXX-*.md`
5. only the linked design docs required by that task

## Sequence

Execute:
- TASK-0002
- TASK-0003
- TASK-0004
- TASK-0005
- TASK-0006

Each task gets a new branch/worktree from the latest accepted main. Do not pile all implementation into one worktree.

## Windows worktree pattern

From the main checkout:

~~~powershell
git fetch --all --prune
git switch main
git pull --ff-only
git worktree add ..\eval-lab-TASK-0002 -b task/TASK-0002-canonical-schema-fixtures origin/main
~~~

For later tasks, substitute the correct task branch after the preceding task is merged.

If the planning PR is not yet merged, do not start implementation from stale main. Use the accepted planning commit/branch only when explicitly instructed by the repository checkpoint.

## Per-task loop

1. Read task.
2. Record starting commit/worktree in its checkpoint.
3. Implement only allowed scope.
4. Run the task-specific tests.
5. Run the full local merge gate:
   - repository contract
   - Ruff
   - pytest
6. Update task checkpoint with exact results.
7. Update `checkpoints/CURRENT.md`.
8. Commit with `TASK-XXXX: <checkpoint>`.
9. Push branch.
10. Open/update PR.
11. Do not start the dependent task until the previous task is accepted/merged, except TASK-0004 may continue after TASK-0003 is implementation-complete but provider-blocked.

## CI condition

GitHub-hosted CI is currently known to dispatch jobs without assigning a runner. Local validated evidence is authoritative until that account/runner issue is fixed.

Do not weaken tests to turn a red no-runner CI badge green.

## Jev condition

The last live Jev attempt reached OpenCode but returned 429 FreeUsageLimitError.

TASK-0003 must implement and test correct 429 handling.

Do not wait for hours inside a task. If quota remains unavailable:
- mock-test the full provider contract;
- record rate_limited;
- close TASK-0003 as implementation-complete/provider-blocked;
- proceed to TASK-0004.

## Public benchmark condition

TASK-0005 uses ARC-Challenge first. Record the exact upstream revision and dataset fingerprint used locally.

Do not commit large caches or downloaded model files.

## Local model condition

TASK-0006 starts with Qwen3-0.6B.

Run a 20-record feasibility probe before the full evaluation slice.

Only attempt Qwen3-1.7B after 0.6B works and resources are acceptable. Qwen3-4B is optional.

If 0.6B cannot run, checkpoint the concrete failure before selecting any fallback.

## No silent scope expansion

The following require a new task, not opportunistic implementation:
- model fine-tuning
- teacher-data generation using Luna/Sol/Grok
- new subjective benchmark domains
- long-context evaluation
- distributed/remote training
- production deployment

## End state after TASK-0006

The repository should have enough evidence to decide the next research branch:
- train a lightweight judge;
- improve rubric decomposition;
- add harder objective benchmarks;
- test selective escalation;
- compare Jev vs local judge at matched confidence/coverage.
