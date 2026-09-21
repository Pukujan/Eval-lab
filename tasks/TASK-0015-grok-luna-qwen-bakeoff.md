# TASK-0015 — Grok Build, Luna, and Qwen Flash Matched Bakeoff

- Status: active
- Owner: Codex/research execution agent
- Priority: P1
- Branch: task/TASK-0015-grok-luna-qwen-bakeoff
- Depends on: TASK-0012 independent benchmark completion

## Goal

Run a fresh, preregistered matched comparison of Grok Build through the authenticated
xAI/OpenCode subscription route, Luna through the authenticated ChatGPT/OpenCode route,
and YOLO-Auto `qwen3.8-flash`. Keep the completed TASK-0012 experiment immutable.

## Scope and frozen inputs

- Experiment: `EXP-20260921-015-grok-luna-qwen-bakeoff`.
- Source pool: the exact 1,408-record pool frozen by EXP-014, with 648
  `public_selection` and 760 `blind_holdout` records.
- Source fingerprint: `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`.
- Typed packet: `eval-lab-system-one` v0.1.0, fingerprint
  `0d07bd8b8b60bd7f0b5b7a5f5819b7d329ea121f686b240e465695b6f6eca1e4`.
- Core arms: requested `opencode/grok-build-0.1`, `opencode/gpt-5.6-luna`, and
  YOLO-Auto `qwen3.8-flash`; each route records the exact surfaced model identity.
- Optional arm: `opencode/gpt-5.6-sol`, enabled only when explicitly requested.
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
- `.venv\\Scripts\\python.exe scripts/run_grok_luna_qwen_bakeoff.py --partition public_selection --limit 1 --output experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/runs/smoke`
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
OpenCode subscription routes for Grok/Luna and YOLO-Auto for Qwen; do not substitute
OpenRouter or another provider.

The first `opencode/grok-4.6` call was exploratory only. The OpenCode catalog exposed
the requested Grok Build model as `opencode/grok-build-0.1`, so the final core arm was
corrected before any blind-holdout labels; the exploratory artifact is retained and
not pooled with the Grok Build arm.

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

Completed: the initial one-record preflight attempted `opencode/grok-4.6` and ended
as an explicit provider error. A read-only `opencode models` audit exposed the exact
Grok Build catalog entry `opencode/grok-build-0.1`; the core arm and manifest were
corrected before any blind-holdout labels. The prior Grok 4.6 preflight remains
separate evidence and is not pooled with the Grok Build arm. Luna and Qwen smoke
evidence remains separately recorded; Qwen returned one valid label.

Exact files changed: the Grok model entry in the runner, freeze metadata, plan,
manifest, README, pool manifest/checksums, CURRENT checkpoint, and this task log.

Commands run: `opencode auth --help`; `opencode auth list`; `opencode models` with
catalog filtering; smoke validation for `runs/smoke`.

Test results: the smoke validator passed; the Qwen arm was `ok: 1`; the exploratory
Grok 4.6 and Luna attempts were `provider_error: 1` each with no labels.

Decision: freeze `opencode/grok-build-0.1` as the only primary Grok arm. Do not use
the failed Grok 4.6 attempt as a substitute or silently reinterpret it.

Unresolved questions: the Grok Build route and Luna route still need independent
one-record smoke results with their exact surfaced IDs before bulk execution.

Next atomic action: commit this model-identity correction, then smoke-test
`opencode/grok-build-0.1` and the Luna route in a fresh output directory.
