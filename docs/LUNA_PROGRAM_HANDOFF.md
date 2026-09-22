# Luna Local Program Handoff — TASK-0002 through TASK-0009

## Mission

Complete the Eval Lab program while fully utilizing the user's existing subscription/free model access where each task calls for it. Git is authoritative state.

## Read order

1. `PROJECT.md`
2. `AGENTS.md`
3. `checkpoints/CURRENT.md`
4. active task file
5. `docs/ACCESS_MODEL_MATRIX.md`
6. only the design sections linked by the active task

## Sequence

Execute and merge sequentially:

- TASK-0002
- TASK-0003
- TASK-0004
- TASK-0005
- TASK-0006
- TASK-0007
- TASK-0008
- TASK-0009

TASK-0004 may proceed after TASK-0003 is implementation-complete even if live Jev is externally rate-limited.

## Existing resource assumptions

### YOLO-Auto

The user states the API credential is already configured locally.

Authoritative Qwen3.8 Flash route:
- base URL `https://yolo-auto.com/v1`
- model `qwen3.8-flash`
- environment variable `YOLO_AUTO_API_KEY`

Do not redirect this work to Alibaba or OpenCode Zen by default.

### SuperGrok

Actively use the user's SuperGrok subscription through supported OAuth/OpenCode integration in TASK-0007 and TASK-0008. Discover and record the exact surfaced model id rather than assuming a version.

### ChatGPT

Use Luna and Sol actively in TASK-0007/TASK-0008 through reproducible audit-batch handoffs.

Do not model ChatGPT subscription access as an OpenAI API.

### Jev

TASK-0003 uses exactly `jev-1.13-free`.

No silent fallback to `jev-1.13`.

### OpenCode free models

Enumerate live free-model availability in TASK-0007 and run a bounded representative subset.

## Per-task loop

1. Update accepted main.
2. Create one task branch/worktree.
3. Record starting SHA/worktree.
4. Implement only task scope.
5. Run task-specific tests.
6. Run full local merge gate.
7. Update active task checkpoint and CURRENT.
8. Commit/push/open PR.
9. Merge before dependent work.

## Subscription utilization rule

Subscription-covered resources named by the active task should be exercised rather than left idle.

Never:
- expose credentials;
- send private/unapproved data to free-trial endpoints;
- silently replace a subscription/free route with a separately metered API route;
- hide provider failures.

## CI condition

Until GitHub runners are restored, exact local validation remains authoritative merge evidence.

## End state

After TASK-0009 the repo should contain:
- objective benchmark substrate
- Jev Free baseline
- local lightweight baseline
- YOLO-Auto Qwen3.8 Flash results
- OpenCode free-model results
- SuperGrok subscription results where accessible
- Luna/Sol audit artifacts
- verified teacher-generated hard negatives
- small-judge training ablations
- calibrated held-out comparison report

## TASK-0010 continuation

TASK-0001 through TASK-0009 are complete.

Next read:
- `tasks/TASK-0010-selective-escalation.md`
- `docs/TASK-0010-METAMORPHIC-DIFFERENTIAL.md`
- `docs/RESEARCH_ARTIFACT_STANDARD.md`

TASK-0010 must preserve the frozen TASK-0009 student for its primary policy experiment and finish with a reproducible benchmark/paper research release.
