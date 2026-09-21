# TASK-0017 — Judge calibration study

- Status: active
- Owner: Codex/research execution agent
- Priority: P1
- Branch: task/TASK-0017-calibration-study
- Depends on: TASK-0015 and TASK-0016 completion; EXP-015 remains immutable

## Goal

Measure whether a controllable local Qwen 4B judge can produce useful raw
probabilities and whether split-safe temperature scaling improves held-out
probability quality. Keep the direct Grok Build, Luna, remote Qwen Flash, and
pinned Jev results as explicit comparison/reference arms without making label-only
outputs look calibrated.

## Inputs

- The exact 1,408-record pool and typed System-One packet frozen by EXP-015.
- EXP-015 direct-only Grok Build, Luna, and YOLO-Auto Qwen Flash outputs, reused
  read-only for label/coverage comparison.
- EXP-014 pinned Jev blind outputs, reused read-only as a label-only reference.
- Local `Qwen/Qwen3-4B` when available through the repository's forced-choice
  Transformers runtime; weights and caches remain outside Git.
- Calibration fit labels from `public_selection` only; blind-holdout labels remain
  evaluation-only.

## Scope and rules

- Core local arm: `Qwen/Qwen3-4B` forced-choice conditional log-likelihoods over
  `pass/fail` and `A/B/TIE`, with raw scores and normalized probabilities retained.
- Calibration is fit separately by judgment mode on successful local predictions from
  `public_selection`, then applied without reading blind labels.
- Primary comparison: local raw versus local temperature-calibrated probabilities
  on the untouched `blind_holdout`.
- Reference comparisons: EXP-015 Grok Build, Luna, and remote Qwen Flash plus the
  EXP-014 pinned Jev outputs contribute accuracy, coverage, agreement, and provider
  status only unless they contain validated probabilities.
- The rolling Jev canary is descriptive and is not part of the primary score.
- Grok calls, if any new smoke is required, use only the direct authenticated xAI
  `grok` CLI. Luna/Sol calls use only the direct authenticated Codex subscription
  CLI. Qwen Flash uses only YOLO-Auto. No OpenCode or OpenRouter calls are allowed.
- No provider output is used as gold. No model weights, credentials, or caches are
  committed.

## Outputs

- `tasks/TASK-0017-judge-calibration-study.md`
- `experiments/EXP-20260921-017-judge-calibration/`
- `scripts/run_local_qwen_calibration.py`
- `scripts/report_judge_calibration.py`
- `src/eval_lab/judges/qwen.py` prompt/runtime extensions as needed
- focused tests for the new prompt and report behavior
- `checkpoints/CURRENT.md`

## Acceptance criteria

- [ ] Preregistration and exact source fingerprints are committed before blind local
  evaluation.
- [ ] Local Qwen 4B feasibility smoke records model identity, revision, context cap,
  runtime, device, dtype, latency, and probability availability.
- [ ] Public calibration predictions are complete or explicitly marked unavailable;
  calibration fit uses only the public calibration split.
- [ ] Blind local predictions are complete or preserve explicit execution failures;
  raw and calibrated metrics are computed without blind-label leakage.
- [ ] Direct-provider and pinned-Jev references remain immutable and are only reused
  offline.
- [ ] Report includes accuracy, Brier, NLL, ECE, risk/coverage, calibration artifact,
  coverage, latency, and provider/reference status limitations.
- [ ] Repository contract, Ruff, tests, diff check, and experiment checksums pass.

## Validation

- Run a one-record or bounded local Qwen 4B smoke before scaling.
- Validate that every prediction preserves a frozen record ID and that context overflow
  is an explicit status rather than silent truncation.
- Fit temperature only on `public_selection` records with successful probabilities.
- Recompute raw and calibrated blind metrics from committed predictions and labels.
- Run the repository contract, Ruff, full pytest, and `git diff --check`.

## Stop conditions

- Stop local scaling if the 4B model cannot load safely on the available hardware,
  if required weights are not locally available without an explicit download decision,
  or if the runtime cannot expose comparable forced-choice scores.
- Stop blind evaluation if the prompt, pool fingerprint, model ID, runtime semantics,
  or calibration rule changes after preregistration; create a new experiment ID.
- Stop and preserve explicit missingness if provider/runtime failures occur. Do not
  substitute OpenCode, OpenRouter, another model, or fabricated labels.

## Checkpoint log

### 2026-09-21 — calibration study opened

Status: active; no TASK-0017 provider or local blind labels requested.

Completed: created an isolated worktree from the completed TASK-0016 commit; defined
the local Qwen 4B raw-versus-calibrated primary comparison; assigned EXP-015 direct
arms and EXP-014 pinned Jev to immutable label-only reference roles; preserved the
direct-only route restrictions.

Exact files changed: this task file, the EXP-017 preregistration files, the Qwen
prompt/runtime extension, and the repository checkpoint after this checkpoint is
committed.

Commands run: worktree creation and read-only runtime/artifact inspection.

Test results: no code or provider test has run yet. The local machine has PyTorch and
Transformers, an RTX 4060 Laptop GPU, and cached Qwen 0.6B but no cached Qwen 4B;
Qwen 4B feasibility is therefore an explicit next gate.

Decision: use local Qwen 4B as the only new calibration-producing arm. Reuse existing
Grok/Luna/Qwen Flash/Jev labels offline rather than rerunning direct providers merely
to obtain confidence they did not previously expose.

Unresolved questions: exact Qwen 4B checkpoint availability, quantization/runtime
choice on the 8 GiB GPU, and whether the local model can complete the frozen pool
within the declared context cap.

Next atomic action: commit the preregistration and prompt/runtime scaffolding, then
run a bounded local Qwen 4B feasibility smoke without touching EXP-015 or EXP-014.

## Handoff

Read in order:

1. `PROJECT.md`
2. `checkpoints/CURRENT.md`
3. this task
4. `docs/EXPERIMENT_PROTOCOL.md`

Active worktree: `D:/claude/eval-lab/.worktrees/TASK-0017-calibration` on branch
`task/TASK-0017-calibration-study`.

## Next atomic action

Commit this preregistration before any blind local labels, then run the declared
bounded Qwen 4B feasibility smoke. Keep all completed EXP-015 and EXP-014 artifacts
byte-immutable.
