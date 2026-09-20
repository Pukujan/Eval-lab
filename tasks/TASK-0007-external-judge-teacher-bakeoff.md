# TASK-0007 — External Judge and Teacher Bakeoff

- Status: active
- Owner: Luna/local agent
- Priority: P0
- GitHub issue: #12
- Depends on: TASK-0006
- Branch: task/TASK-0007-external-bakeoff

## Goal

Fully exercise the user's available external/free/subscription model access on the same frozen objective records.

## Inputs

- frozen synthetic/ARC records
- TASK-0004 metrics
- TASK-0006 local predictions
- `docs/ACCESS_MODEL_MATRIX.md`

## Required resources

### YOLO-Auto Qwen3.8 Flash

- base URL `https://yolo-auto.com/v1`
- model `qwen3.8-flash`
- local credential variable `YOLO_AUTO_API_KEY`
- user reports the credential is already configured locally

This is a required automated arm unless account/connectivity state blocks it.

### SuperGrok

Use the existing subscription through supported OAuth/OpenCode integration. Discover and record the exact surfaced model id before running.

### OpenCode Zen free models

Enumerate current free models. Preferred representative arms:
- `nemotron-3.5-lightning-free`
- `mimo-v2.5-free`

Add at most two more named free models if useful.

### Jev

Reuse `jev-1.13-free` results.

### ChatGPT Luna/Sol

Create deterministic audit batches for subscription review. These are audit/teacher arms, not fabricated API arms.

## Outputs

- provider/model census
- normalized external predictions
- exact record-id coverage per model
- comparison report
- provider failure/rate-limit summary
- curated Luna/Sol audit batches

## Acceptance criteria

- [ ] YOLO-Auto Qwen3.8 Flash connectivity verified
- [ ] selected YOLO-Auto slice attempted
- [ ] SuperGrok subscription integration attempted and exact model recorded
- [ ] current OpenCode free-model list recorded
- [ ] at least two available free general models attempted
- [ ] identical record ids used for claimed comparisons
- [ ] failures separated from wrong labels
- [ ] Luna audit batch produced
- [ ] Sol hard-disagreement batch produced
- [ ] full local merge gate passes

## Validation

Use 10-20 record smoke runs before full slices. Verify YOLO-Auto model is exactly `qwen3.8-flash`.

## Stop conditions

Stop an arm if credentials/subscription integration is unavailable, model identity cannot be determined, or provider policy conflicts with the selected data.

## Checkpoint log

Append exact access results here.

### 2026-09-20 — TASK-0007 start and pre-registration

Created dedicated worktree `D:\\claude\\eval-lab-TASK-0007` on branch `task/TASK-0007-external-bakeoff` from accepted main `9aabaa1af64d9956db0d9b07650dd98e6ed70ebc`. Read `PROJECT.md`, `AGENTS.md`, `checkpoints/CURRENT.md`, this task file, `docs/EXPERIMENT_PROTOCOL.md`, `docs/SDD.md`, `docs/TDD.md`, and `docs/ACCESS_MODEL_MATRIX.md`.

Environment/access observations:
- Windows 11, Python `3.12.10`, OpenCode CLI `1.18.31`, Node `v24.14.1`.
- A task-scoped ignored `.env` was created from `C:\\Users\\pujan\\OneDrive\\Desktop\\configs\\.env`; only provider aliases needed by this task were copied. Secret values were not printed or committed.
- The source configuration exposes a Qwen-compatible URL/key pair. The task alias is `YOLO_AUTO_API_KEY` and the requested model is forced to the exact contract id `qwen3.8-flash`; the source's generic model value is not used.
- `opencode models` enumerated current provider models, including `opencode/nemotron-3.5-lightning-free`, `opencode/mimo-v2.5-free`, `opencode/grok-4.6`, `opencode/gpt-5.6-luna`, `opencode/gpt-5.6-sol`, and `yolo-auto/qwen3.8-flash`.

Pre-registration: `experiments/EXP-20260920-003-external-judge-bakeoff/README.md` and `experiment.yaml` freeze the hypothesis, 4,096-token cap, TASK-0006 record fingerprint, model arms, metrics, failure exclusions, and audit-batch policy before final predictions.

Next atomic action: implement the provider-neutral external runner and perform 10-record smoke runs for the required YOLO-Auto, two OpenCode free, and surfaced SuperGrok arms.

## Handoff

TASK-0008 uses the strongest/diverse successful resources revealed by this bakeoff.
