# TASK-0015 — Grok Build, Luna, and Qwen Flash Matched Bakeoff

- Status: active
- Owner: Codex/research execution agent
- Priority: P1
- Branch: task/TASK-0015-grok-luna-qwen-bakeoff
- Depends on: TASK-0012 independent benchmark completion

## Goal

Run a fresh, preregistered matched comparison of Grok Build through the direct
authenticated xAI `grok` CLI, Luna through the direct authenticated Codex/ChatGPT route,
and YOLO-Auto `qwen3.8-flash`. Keep the completed TASK-0012 experiment immutable.

## Scope and frozen inputs

- Experiment: `EXP-20260921-015-grok-luna-qwen-bakeoff`.
- Source pool: the exact 1,408-record pool frozen by EXP-014, with 648
  `public_selection` and 760 `blind_holdout` records.
- Source fingerprint: `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`.
- Typed packet: `eval-lab-system-one` v0.1.0, fingerprint
  `0d07bd8b8b60bd7f0b5b7a5f5819b7d329ea121f686b240e465695b6f6eca1e4`.
- Core arms: direct `grok` CLI using its authenticated xAI subscription (`grok-4.6`),
  direct Codex CLI using `gpt-5.6-luna`, and
  YOLO-Auto `qwen3.8-flash`; each route records the exact surfaced model identity.
- Optional arm: direct Codex CLI `gpt-5.6-sol`, enabled only when explicitly requested.
- Primary comparison: blind-holdout accuracy, balanced accuracy, macro-F1, resolved
  coverage, Wilson 95% uncertainty, latency, and same-record agreement.

Provider failures, rate limits, parse errors, and skipped records remain explicit
execution states and never receive fallback labels. Provider output never selects
records, prompts, models, thresholds, or gold labels.

## Outputs

- `tasks/TASK-0015-grok-luna-qwen-bakeoff.md`
- `scripts/freeze_grok_luna_qwen_pool.py`
- `scripts/run_grok_luna_qwen_bakeoff.py`
- `scripts/validate_grok_luna_qwen_bakeoff.py`
- `tests/test_grok_luna_qwen_bakeoff.py`
- `experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/`
- `checkpoints/CURRENT.md`

## Acceptance criteria

- [ ] Preregistration and the exact pool/typed prompt are committed before final
  blind-holdout labels are requested.
- [ ] One-record smoke tests attempt every core route and retain surfaced model IDs.
- [ ] The matched pool is attempted with separate normalized output files per arm.
- [ ] Accuracy, coverage, Wilson uncertainty, latency, native-confidence availability,
  same-record agreement, and provider-status reports are present and validated.
- [ ] No provider failure is counted as an ordinary wrong label.
- [ ] Local contract, Ruff, tests, diff check, and experiment checksums pass.

## Commands

- `.venv\\Scripts\\python.exe scripts/freeze_grok_luna_qwen_pool.py`
- `.venv\\Scripts\\python.exe scripts/run_grok_luna_qwen_bakeoff.py --partition public_selection --limit 1 --models grok,luna,qwen_flash --output experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/runs/smoke-direct-20260921`
- `.venv\\Scripts\\python.exe scripts/run_grok_luna_qwen_bakeoff.py --partition blind_holdout --output experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/runs/blind`
- `.venv\\Scripts\\python.exe scripts/validate_grok_luna_qwen_bakeoff.py --experiment ...`
- `.venv\\Scripts\\python.exe scripts/check_repo_contract.py`
- `.venv\\Scripts\\ruff.exe check .`
- `.venv\\Scripts\\python.exe -m pytest -q`
- `git diff --check`

## Checkpoint log

### 2026-09-21 — new experiment opened

Status: active. Created a dedicated TASK-0015 worktree from the completed TASK-0012
independent benchmark commit. The new experiment is intentionally separate from
EXP-010 and EXP-011 so their provider failures and incomplete Qwen arm remain intact.

Completed: selected the exact EXP-014 source pool and typed System-One packet as the
matched input; defined core and optional arms, metrics, missingness, and stop rules;
added the preregistration and route-aware runner/validator scaffolding.

Exact files changed: this task file, `experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/`
planning files, and the new freeze/runner/validator/test scripts.

Commands run: `git worktree add D:\\claude\\eval-lab-TASK-0015-bakeoff -b
task/TASK-0015-grok-luna-qwen-bakeoff HEAD`.

Test results: live provider smoke and repository gates are pending until the
preregistration commit.

Decision: use the full EXP-014 matched pool, with the blind partition as the primary
score and the public partition as a separately labeled descriptive execution. Use
the direct Grok Build CLI for Grok, the direct Codex CLI for Luna, and YOLO-Auto
for Qwen; do not use OpenCode or OpenRouter for any arm.

The first non-primary preflight artifacts are historical only and are not part of the
final comparison. The final Grok implementation invokes the direct `grok` executable,
and the Luna/Sol implementations invoke the direct Codex CLI; OpenCode and OpenRouter
are excluded from this task.

Unresolved questions: provider availability and subscription quotas must be observed
by smoke tests; no result is assumed in advance.

Next atomic action: commit the preregistration and offline runner/validator, then run
the three core route smoke tests and record their exact surfaced model identities.

## Handoff

Read, in order:

1. `PROJECT.md`
2. `checkpoints/CURRENT.md`
3. this task
4. `docs/EXPERIMENT_PROTOCOL.md`

The integration worktree is `D:/claude/eval-lab-TASK-0015-bakeoff` on branch
`task/TASK-0015-grok-luna-qwen-bakeoff`. Keep EXP-014 immutable. After the
preregistration checkpoint, run the route smoke tests before any bulk partition.

### 2026-09-21 — model identity correction before final evaluation

Status: active; final evaluation has not started.

Completed: the initial non-primary preflights ended as explicit provider errors and
are not part of the final arms. The direct xAI CLI was installed and authenticated via
`grok login --device-auth`; `grok models` reports the direct session and default
`grok-4.6`. A direct headless JSON probe returned a valid label and surfaced
`grok-4.6-build` usage metadata. Luna and Qwen smoke evidence remains separately
recorded; Qwen returned one valid label.

Exact files changed: the Grok model entry in the runner, freeze metadata, plan,
manifest, README, pool manifest/checksums, CURRENT checkpoint, and this task log.

Commands run: direct xAI CLI installation/login/model inspection; Codex CLI health
inspection; smoke validation for `runs/smoke`.

Test results: the smoke validator passed; the Qwen arm was `ok: 1`; the exploratory
Grok 4.6 and Luna attempts were `provider_error: 1` each with no labels.

Decision: freeze the direct `grok` CLI with requested model `grok-4.6` as the only
primary Grok arm and use direct Codex CLI models for Luna/Sol. Do not use the
historical preflight attempts as substitutes or silently reinterpret them.

Unresolved questions: the direct Grok Build route and direct Codex Luna route still
need independent one-record smoke results before bulk execution.

Next atomic action: commit the direct-CLI route correction, then run the Grok Build
direct-CLI smoke and the Luna route in separate fresh output files.

### 2026-09-21 — direct-only route correction

Status: active; no final evaluation labels have been requested.

Completed: removed all active OpenCode and OpenRouter routes from TASK-0015. The
runner and frozen metadata now use the direct authenticated xAI `grok` Build CLI for
Grok, the direct authenticated Codex CLI subscription for Luna/Sol, and YOLO-Auto for
Qwen Flash. The earlier `runs/smoke` output remains historical and is not reused or
overwritten; the next artifact is a new `runs/smoke-direct-20260921` directory.

Exact files changed: `scripts/run_grok_luna_qwen_bakeoff.py`,
`scripts/freeze_grok_luna_qwen_pool.py`, the EXP-015 plan/README/manifests/checksums,
`checkpoints/CURRENT.md`, and this task log.

Commands run: `grok models`; `codex doctor`; direct headless Grok JSON probe; direct
headless Codex Luna JSON probe; `python scripts/check_repo_contract.py`; `ruff check .`;
`$env:PYTHONPATH='src'; python -m pytest -q`; and `git diff --check`.

Test results: repository contract `OK`; Ruff clean; `98 passed in 6.27s`; diff check
clean. The direct probes returned valid labels; the Grok probe surfaced
`grok-4.6-build`, and Codex used the requested `gpt-5.6-luna` subscription route.

Decision: only direct Grok Build CLI and direct Codex subscription CLI calls are
permitted for the Grok/Luna/Sol arms. No OpenCode or OpenRouter fallback is allowed.

Next atomic action: commit this route correction, then run and validate the fresh
direct-only smoke for Grok, Luna, and Qwen Flash.

### 2026-09-21 — direct-only smoke validated

The first direct Grok smoke reached xAI but ended as a parse error because the Build
CLI's default agent behavior used multiple workspace-inspection turns. No other Grok
route was attempted. The direct runner was hardened with the Grok CLI's native JSON
schema constraint, verbatim prompt mode, disabled web search, and a one-turn cap.

Exact fresh smoke command: `$env:PYTHONPATH='src'; python
scripts/run_grok_luna_qwen_bakeoff.py --partition public_selection --limit 1
--models grok,luna,qwen_flash --output
experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/runs/smoke-direct-tight-20260921
--timeout 120 --env-file C:\Users\pujan\OneDrive\Desktop\configs\.env`.

Result: Grok direct xAI Build `ok: 1` with surfaced `grok-4.6-build`; direct Codex
Luna `ok: 1` using requested `gpt-5.6-luna`; and YOLO-Auto Qwen Flash `ok: 1`.
`validate_grok_luna_qwen_bakeoff.py` passed. The normalized smoke artifact is
`runs/smoke-direct-tight-20260921/`; the earlier direct parse-error artifact is also
retained separately for append-only route evidence.

Exact files changed: `scripts/run_grok_luna_qwen_bakeoff.py`,
`runs/smoke-direct-20260921/`, `runs/smoke-direct-tight-20260921/`, this task log,
and `checkpoints/CURRENT.md`.

Decision: the direct-only core smoke is valid. Proceed only with direct Grok Build,
direct Codex Luna/Sol, and YOLO-Auto Qwen Flash; no OpenCode or OpenRouter fallback.

Next atomic action: commit the hardened runner and smoke artifacts, then run the
matched public partition and preserve separate arm outputs.

### 2026-09-21 — public execution in progress

Status: active; public provider execution is running and the blind holdout remains
untouched.

Exact command: `$env:PYTHONPATH='src'; python
scripts/run_grok_luna_qwen_bakeoff.py --partition public_selection --models
grok,luna,qwen_flash --workers 4 --timeout 120 --env-file
C:\Users\pujan\OneDrive\Desktop\configs\.env --output
experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/runs/public-direct-20260921`.

The direct authenticated Grok Build CLI is the first arm and is cycling records under
the per-record timeout. No OpenCode or OpenRouter command is used. The normalized
public artifact is not yet complete; after termination, validate checksums, provider
statuses, metrics, and differential output before any blind request.

### 2026-09-21 — parallel streaming runner checkpoint

Status: active; the prior sequential non-streaming public attempt was terminated
before any normalized public predictions were written. Its output directory remains
empty and no blind-holdout request was made.

Completed: changed the runner to use multiple isolated direct CLI sessions. Grok now
uses `--output-format streaming-json` with the native JSON schema and a unique
`--leader-socket` per session; Luna/Sol consume the direct `codex exec --json` event
stream; Qwen Flash consumes OpenAI-compatible SSE with `stream: true`. All three
arms run through the shared worker pool and checkpoint one normalized prediction and
one progress JSON after each record. The normalized results remain ordered by the
frozen pool even when completion order is parallel.

Exact files changed: `scripts/run_grok_luna_qwen_bakeoff.py`,
`tests/test_grok_luna_qwen_bakeoff.py`, this task log, and the fresh streaming smoke
artifacts under `runs/smoke-stream-grok2-20260921/` and
`runs/smoke-stream-all-20260921/`.

Commands run: direct CLI streaming probe; focused Ruff; focused pytest; fresh
streaming Grok smoke; fresh combined Grok/Luna/Qwen smoke; and the run validator.

Test results: focused bakeoff tests `6 passed`; Ruff clean; combined streaming smoke
validated with Grok `ok: 1` and surfaced `grok-4.6-build`, Luna `ok: 1` through
`gpt-5.6-luna`, and Qwen `ok: 1` through `qwen3.8-flash`. The smoke metadata records
`grok-streaming-json`, `codex-jsonl`, and `openai-sse` event counts.

Decision: use parallel independent sessions, not Grok-spawned subagents, for the
matched run. This keeps every record an independently attributable direct provider
request while reducing wall-clock time. OpenCode and OpenRouter remain excluded.

Unresolved questions: provider concurrency limits and the final full-pool timeout/
rate-limit mix must be observed during the new public execution.

Next atomic action: commit this streaming runner checkpoint, then launch a fresh
parallel public-selection run with `--workers 4`; monitor its per-arm progress files
and validate the completed artifact before any blind-holdout request.

### 2026-09-21 — fresh parallel public execution in progress

Status: active. The prior non-streaming attempt is stopped; the new run is the only
active TASK-0015 provider execution and the blind holdout remains untouched.

Exact command: `$env:PYTHONPATH='src'; python
scripts/run_grok_luna_qwen_bakeoff.py --partition public_selection --models
grok,luna,qwen_flash --workers 4 --timeout 120 --env-file
C:\Users\pujan\OneDrive\Desktop\configs\.env --output
experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/runs/public-stream-parallel-20260921`.

Observed checkpoint: the Grok arm has four concurrent direct xAI CLI sessions and
has completed `11/648` records, all `ok`, with `streaming: true` and route
`direct_grok_build_cli_subscription`. Luna and Qwen will start only after the Grok
arm boundary; each will also use four concurrent streaming workers. The process is
live and no final output artifact exists yet.

Next atomic action: continue monitoring `runs/public-stream-parallel-20260921/progress/`,
then validate the completed public artifact and record provider statuses before any
blind-holdout execution.

### 2026-09-21 — user-requested pause for worktree organization

Status: paused for relocation, with the provider process stopped safely. The partial
public run is preserved rather than discarded: Grok is `648/648` (`643 ok`, `5
provider_error`), Luna is `532/648` (`532 ok`), and Qwen has not started. The run has
no final `results.json`; its per-arm JSONL and progress checkpoints are the resume
source of truth.

Completed: added explicit `--resume` support that validates existing normalized
checkpoints, skips completed records, and appends only missing records. The active
worktree is ready to move from `D:\claude\eval-lab-TASK-0015-bakeoff` to the organized
location `D:\claude\eval-lab\.worktrees\TASK-0015-bakeoff`.

Next atomic action: move the registered Git worktree, verify its branch and partial
artifacts at the new path, then resume the same public run with `--resume` from the
organized location. Keep the blind holdout untouched.

### 2026-09-21 — worktree consolidation complete; resume ready

Status: active again from the organized worktree. All 18 registered Eval Lab
worktrees now live under `D:\claude\eval-lab\.worktrees`; no `eval-lab-*` sibling
directories remain directly under `D:\claude`. The TASK-0014 worktree was repaired
after a native move and its stale empty source shell was removed.

The TASK-0015 partial public run remains at
`D:\claude\eval-lab\.worktrees\TASK-0015-bakeoff\experiments\EXP-20260921-015-grok-luna-qwen-bakeoff\runs\public-stream-parallel-20260921`.
Grok remains `648/648` (`643 ok`, `5 provider_error`); Luna remains `532/648`
(`532 ok`); Qwen remains unstarted. The branch and worktree identity are preserved.

Next atomic action: resume from the organized path with `--resume --workers 4`,
continue the missing Luna records, then run Qwen Flash and finalize/validate the
public artifact before any blind-holdout request.

### 2026-09-21 — resumed from organized worktree

Status: active. Resume was confirmed from
`D:\claude\eval-lab\.worktrees\TASK-0015-bakeoff`; Grok’s complete checkpoint was
skipped, Luna’s 532 existing records were reused, and the runner has continued with
four direct streamed Codex sessions. Live Luna progress is `539/648`, all `ok`.

Exact resume command: `$env:PYTHONPATH='src'; python
scripts/run_grok_luna_qwen_bakeoff.py --partition public_selection --models
grok,luna,qwen_flash --workers 4 --timeout 120 --env-file
C:\Users\pujan\OneDrive\Desktop\configs\.env --output
experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/runs/public-stream-parallel-20260921
--resume`.

Next atomic action: finish the missing Luna records, run Qwen Flash, finalize and
validate the public artifact, then checkpoint before any blind-holdout request.

### 2026-09-21 — public matched run complete after organized resume

Status: public selection complete; the task remains active only for the separately
authorized blind-holdout decision. The run was resumed from the organized worktree
`D:\\claude\\eval-lab\\.worktrees\\TASK-0015-bakeoff` with `--resume`, so completed
Grok and Luna records were reused rather than rerun. The blind holdout remains
untouched.

Final public artifact: `experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/runs/public-stream-parallel-20260921/`, with `648` frozen matched records per arm.

Provider outcomes:

- Grok Build: direct authenticated xAI CLI route only; requested `grok-4.6`, surfaced
  `grok-4.6-build`, streaming enabled, `643 ok` and `5 provider_error` (`3 process_exit`,
  `2 timeout`), resolved accuracy `0.3716951788`.
- Luna: direct Codex ChatGPT subscription route only; requested `gpt-5.6-luna`,
  streaming enabled, `648 ok`, resolved accuracy `0.9722222222`.
- Qwen Flash: YOLO-Auto route only; requested and surfaced `qwen3.8-flash`, streaming
  enabled, `647 ok` and `1 parse_error`, resolved accuracy `0.9706336940`.

Exact files added: the finalized public run directory containing `results.json`,
`differential.json`, `provider-status.json`, `report.md`, `checksums.sha256`, and the
per-arm prediction/progress/checkpoint files. No OpenCode or OpenRouter route was used.

Validation results: the experiment validator passed; repository contract passed; Ruff
passed; the full test suite passed (`100 passed`); and `git diff --check` was clean.

Decision: preserve the five Grok provider failures and one Qwen parse error as explicit
unresolved outcomes with no fallback labels. Do not tune, relabel, or substitute a
provider from public results. The blind holdout must remain separate and untouched.

Next atomic action: review this committed public artifact and explicitly decide whether
to launch the blind holdout with the same frozen pool, typed prompt, direct-only routes,
streaming, and separate output files.
