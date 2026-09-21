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
  The execution runtime is bitsandbytes 4-bit NF4 double quantization with float16
  compute and a 2,048-token cap; the measured maximum frozen-pool prompt is 755
  input tokens, so the cap does not truncate this pool.
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

### 2026-09-21 — Qwen 4B feasibility smoke passed

Status: active; full public and blind local evaluation has not started.

Completed: downloaded the declared `Qwen/Qwen3-4B` checkpoint into the external
Hugging Face cache, restored CUDA-enabled PyTorch and Transformers in the managed
repository `.venv`, and ran the one-record public-selection smoke through the local
forced-choice runner. The initial system-Python attempt failed before model execution
because that interpreter had CPU-only PyTorch; it was retained as an environment
diagnostic, not as a model result. The managed runtime then passed.

Exact files changed: the smoke artifact under
`experiments/EXP-20260921-017-judge-calibration/runs/smoke-qwen4b-20260921/`, the
batched legal-label scoring path in `src/eval_lab/judges/qwen.py`, and its focused test.

Commands run: CUDA/PyTorch/Transformers verification; one-record local Qwen 4B smoke;
focused Ruff; focused Qwen tests; and `git diff --check`.

Test results: CUDA PyTorch `2.11.0+cu128`, CUDA `12.8`, RTX 4060 detected;
Transformers `5.17.0`; model revision `1cfa9a7208912126459214e8b04321603b3df60c`;
device `cuda:0`; dtype `torch.float16`; `1/1 ok`; valid probabilities; latency
`4714.69 ms`. Focused tests pass (`6 passed`) and Ruff is clean.

Decision: retain the full-precision Qwen 4B local arm. Batch legal-label scoring in one
forward pass per record to reduce the cost of the full pool. No quantized substitute,
OpenCode route, OpenRouter route, or provider fallback is authorized.

Unresolved questions: full-pool runtime and whether any records exceed the declared
4,096-token cap. The one-record temperature artifact is smoke-only and is not evidence
for calibration quality.

Next atomic action: commit this smoke/runner checkpoint, then run the frozen public
calibration partition with the managed CUDA environment before touching the blind
holdout.

### 2026-09-21 — resumable local runner checkpoint

Status: active; public calibration run has not started.

Completed: added per-record JSONL checkpointing, progress metadata, and explicit
`--resume` support to the local Qwen calibration runner. Existing normalized records
are validated by record ID and reused only when resuming the same unfinished output;
finalized outputs cannot be overwritten or resumed.

Exact files changed: `scripts/run_local_qwen_calibration.py`.

Commands run: focused Ruff, focused Qwen tests, and `git diff --check`.

Test results: Ruff clean; `6 passed` for the focused Qwen suite; diff check clean.

Decision: launch public calibration only after this checkpoint is committed. Use the
managed CUDA environment, one local model process, and immediate per-record progress
checkpoints; do not parallelize duplicate 4B model copies on the 8 GiB GPU.

Unresolved questions: full-pool throughput and any runtime failures after the model
has been warmed on more than one record.

Next atomic action: commit the resumable runner, then start the frozen
`public_selection` calibration run.

### 2026-09-21 — memory-safe Qwen runtime amendment

Status: active; the prior full-precision smoke is retained as feasibility evidence,
but no public or blind calibration labels were produced under that runtime.

Completed: paused the local process while it was loading the unquantized Qwen 4B
weights after the user reported excessive GPU memory use. Confirmed the model is
`Qwen/Qwen3-4B` with a model maximum of 40,960 tokens, while the experiment prompt
cap was 4,096 and the frozen pool's measured maximum input was only 755 tokens.
The runtime is amended before final evaluation to use bitsandbytes NF4 double
quantization with float16 compute and a 2,048-token cap. This should reduce the
roughly 8 GiB unquantized weight footprint enough for the 8 GiB RTX 4060 while
retaining the same forced-choice score semantics.

Exact files changed: the Qwen runtime adapter and runner, EXP-017 manifest, and
focused Qwen runtime tests. The external bitsandbytes and accelerate packages are
installed only in the local ignored environment; no weights or credentials enter
Git.

Validation still required: one-record 4-bit smoke must record actual VRAM/runtime
metadata and pass the existing focused tests before public scaling resumes.

Next atomic action: run the bounded 4-bit Qwen smoke with the 2,048-token cap and
inspect GPU memory before deciding whether to resume public calibration.

### 2026-09-21 — memory-safe 4-bit smoke passed

Status: active; public calibration remains paused pending this optimization gate.

Completed: installed the local-only `bitsandbytes` and `accelerate` runtime
packages, then ran the one-record Qwen 4B smoke with NF4 double quantization,
float16 compute, a 2,048-token cap, and an 0.8 per-process CUDA memory fraction.
The run returned `1/1 ok`, valid probabilities, `cuda:0`, model revision
`1cfa9a7208912126459214e8b04321603b3df60c`, and retained a complete normalized
smoke artifact. During loading, external GPU monitoring observed approximately
2.8–2.9 GiB used on the 8 GiB RTX 4060; after exit, usage returned to about
0.26 GiB. This is materially below the prior unquantized roughly 8 GiB weight
footprint.

Exact files changed: the Qwen runtime adapter, local runner, EXP-017 manifest,
focused Qwen tests, and the 4-bit smoke artifact under
`experiments/EXP-20260921-017-judge-calibration/runs/smoke-qwen4b-4bit-20260921/`.

Validation: Ruff clean; focused Qwen tests now pass (`8 passed`); `git diff --check`
clean. No public or blind labels were produced under the old full-precision
runtime, and no provider route was invoked.

Decision: resume only with the 4-bit runtime, one model process, 2,048-token cap,
and 0.8 CUDA memory fraction. Do not launch duplicate Qwen copies.

Next atomic action: commit this optimization checkpoint, then start the frozen
public-selection calibration run with the memory-safe settings.

### 2026-09-21 — public run paused for allocator control

Status: active; optimized public run is paused at `560/648` successful records.

Completed: the 4-bit public run loaded successfully and reached `560/648` with
all statuses `ok`. External GPU monitoring saw memory rise from roughly 5.0 GiB
to 6.96 GiB as the CUDA allocator retained blocks across varying prompt sizes.
The process was stopped before the physical 8 GiB limit; all 560 predictions are
preserved in the resumable output directory
`runs/public-qwen4b-4bit-20260921/`.

Decision: add an explicit `empty_cache_every` control, defaulting to every record
for this 8 GiB run, so unused CUDA allocator blocks are released after each
checkpoint. The existing partial output must be resumed with the same 4-bit
configuration after this code checkpoint; it must not be mixed with the paused
FP16 output.

Unresolved: confirm that cache release keeps resumed memory below the safety target
while completing the remaining 88 public records.

Next atomic action: commit the allocator-control change, resume the existing
4-bit public output, and monitor VRAM until finalization.

### 2026-09-21 — optimized public calibration complete

Status: active; public selection is complete, blind holdout has not started.

Completed: resumed the exact 4-bit public output and finished all `648/648`
records with `648 ok`, no context failures, and one normalized probability map
per record. Calibration fit used the public split only: 180 single records and
468 pairwise records. Raw accuracy was `0.3950617284`; calibrated accuracy was
unchanged, while Brier improved from `0.7729421451` to `0.5416915679`, NLL from
`1.2955413327` to `0.8011710412`, and ECE from `0.3718967481` to `0.0991645340`.

Exact files changed: finalized output under
`experiments/EXP-20260921-017-judge-calibration/runs/public-qwen4b-4bit-20260921/`.

Runtime evidence: `Qwen/Qwen3-4B`, revision
`1cfa9a7208912126459214e8b04321603b3df60c`, `cuda:0`, float16 compute, 4-bit
NF4 double quantization, 2,048-token cap, 0.8 CUDA memory fraction, and
per-record cache release. External monitoring peaked around 6.96 GiB before the
cache-release amendment; the resumed completion finalized without OOM and returned
to about 0.38 GiB after exit. No intermediate peak was recorded during the final
28-record resume, so the artifact's runtime configuration is the authoritative
evidence for that segment.

Validation: optimized output checksums were generated; Ruff, focused Qwen tests
(`8 passed`), repository contract, and diff check passed. The earlier 182-record
FP16 checkpoint remains separate and is not included in this result.

Next atomic action: review the public artifact, then run the blind holdout with
the same memory-safe runtime and no calibration fit on blind labels.
