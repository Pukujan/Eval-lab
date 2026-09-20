# TASK-0007 — External Judge and Teacher Bakeoff

- Status: completed — local acceptance criteria met; PR #22 merged
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

- [x] YOLO-Auto Qwen3.8 Flash connectivity verified
- [x] selected YOLO-Auto slice attempted
- [x] SuperGrok subscription integration attempted and exact model recorded
- [x] current OpenCode free-model list recorded
- [x] at least two available free general models attempted
- [x] identical record ids used for claimed comparisons
- [x] failures separated from wrong labels
- [x] Luna audit batch produced
- [x] Sol hard-disagreement batch produced
- [x] full local merge gate passes

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

### 2026-09-20 — TASK-0007 smoke and final frozen slice

Environment:
- Windows 11, Python `3.12.10`, OpenCode CLI `1.18.31`, Node `v24.14.1`, worktree `D:\\claude\\eval-lab-TASK-0007`, branch `task/TASK-0007-external-bakeoff`.
- The ignored `.env` contains task-scoped aliases only. Its Qwen-compatible endpoint returned HTTP `200` from `/models` and exposed the exact required `qwen3.8-flash` id. No credential value was printed or committed.

Commands and results:
- `opencode models` -> current catalog recorded in `provider_census.json`; both `opencode/nemotron-3.5-lightning-free` and `opencode/mimo-v2.5-free` were present; surfaced SuperGrok model recorded as `opencode/grok-4.6`.
- `D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_external_bakeoff.py --limit 10 --timeout 30 --models yolo-auto/qwen3.8-flash --output-dir .task7-smoke-yolo10-v2` -> 9 `ok`, 1 provider `parse_error` before final request settings were frozen; the exact model identity was confirmed.
- `D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_external_bakeoff.py --limit 1 --timeout 10 --models opencode/mimo-v2.5-free --output-dir .task7-smoke-mimo` -> provider timeout; arm stopped cleanly.
- Equivalent bounded probes for `opencode/nemotron-3.5-lightning-free` and `opencode/grok-4.6` -> provider timeout; exact model ids recorded and arms stopped without fabricated labels.
- `D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_external_bakeoff.py --limit 20 --timeout 10 --output-dir experiments/EXP-20260920-003-external-judge-bakeoff` -> YOLO-Auto `20/20 ok`, accuracy `0.60`; each OpenCode free/Grok arm recorded one timeout and 19 skipped records; all four arms share the same 20 record IDs.
- Final Luna audit batch contains 10 deterministic uncertainty-ranked records; final Sol batch contains 10 deterministic disagreement-ranked records. Gold labels are excluded from both batches.

Files changed:
- `scripts/run_external_bakeoff.py`, `tests/test_external_bakeoff.py`.
- `experiments/EXP-20260920-003-external-judge-bakeoff/` provider census, normalized predictions, manifest, results, report, and Luna/Sol audit batches.
- This task log.

Decisions:
- Keep YOLO-Auto model identity exact as `qwen3.8-flash`; the source configuration's generic Qwen model value was not substituted.
- Keep provider timeouts, parse errors, and skipped records outside wrong-label metrics. Text-only external arms expose no calibrated probabilities, so probability metrics remain unavailable for them.
- Treat Luna and Sol artifacts as reproducible review inputs, not fabricated subscription predictions or objective gold.
- Jev remains `jev-1.13-free` with no reusable successful predictions because the TASK-0003 live call was rate-limited.

Blockers: OpenCode free and SuperGrok subscription calls timed out through the local CLI wrapper; this is an access/integration blocker for those arms, not a model label. GitHub Actions remains blocked by the known account budget/no-runner condition. YOLO-Auto and the local validation environment are usable.

Next atomic action: run the full repository contract, Ruff, and pytest gates, commit the completed TASK-0007 artifacts and checkpoint, push the branch, and open the review PR.

## Handoff

TASK-0008 uses the strongest/diverse successful resources revealed by this bakeoff.


### 2026-09-20 — TASK-0007 review handoff

TASK-0007 is pushed in PR #22 at commit f1f4c1cfa3c866d6e04f271d4c3339ad5dbb7b35; the implementation and experiment commits are included in the branch.

Next atomic action: merge PR #22 after the local merge gate, update local main, and only then create the TASK-0008 worktree.


### 2026-09-20 — TASK-0007 merge checkpoint

PR #22 merged TASK-0007 into main at 1ecd5be35c2315ec927b35301c10aa48b8669371. The Actions budget prevented the 3.11 job from starting; the 3.12 job was cancelled before any workflow step. Local validation is authoritative and green.

Next atomic action: update local main to the merge commit, then create the dedicated TASK-0008 worktree.
