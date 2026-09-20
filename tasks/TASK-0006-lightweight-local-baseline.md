# TASK-0006 — Lightweight Local Judge Baseline

- Status: queued
- Owner: Luna/local agent
- Priority: P0
- GitHub issue: #10
- Depends on: TASK-0002, TASK-0004, TASK-0005
- TASK-0003 predictions optional for direct Jev comparison when provider quota allows
- Branch: task/TASK-0006-lightweight-local-baseline

## Goal

Run at least one lightweight local Qwen judge over the same canonical synthetic and ARC evaluation records and produce the first v0 comparison report.

## Why

The core research question requires measuring how far a cheap/local judge can go before escalation to a stronger/provider judge is needed.

## Baseline ladder

Required first target:
- `Qwen/Qwen3-0.6B`

Preferred if feasible:
- `Qwen/Qwen3-1.7B`

Optional stretch:
- `Qwen/Qwen3-4B`

Do not make 4B a completion requirement.

## Feasibility gate

Before full evaluation:
1. load model/runtime;
2. run 20 canonical records;
3. record RAM/VRAM observations if available;
4. record median/p95 latency;
5. confirm context cap;
6. checkpoint before attempting a larger model.

## Scoring contract

Prefer forced-choice label sequence scoring rather than sampled prose.

For each legal label:
- compute conditional sequence log-likelihood;
- retain raw log-score;
- softmax across legal labels;
- emit normalized JudgePrediction.

Legal classes:
- PASS/FAIL
- A/B/TIE

If the chosen runtime cannot expose scores, label-only evaluation is allowed but probability/calibration metrics are marked unavailable.

## Inputs

- TASK-0005 canonical ARC record IDs
- synthetic fixtures
- TASK-0004 metrics/reporting
- `docs/SDD.md` section 10
- `docs/TDD.md` section 9

## Outputs

- local Qwen judge adapter
- model/runtime configuration
- 20-record feasibility report
- full chosen evaluation-slice predictions
- aggregate/per-domain metrics
- calibration results when probabilities are available
- first v0 comparison report
- checkpoint recommending next research task

## Allowed files

- `src/eval_lab/judges/qwen.py`
- local runtime/config helpers
- `tests/`
- `pyproject.toml` local extra if needed
- experiment/report artifacts allowed by experiment protocol
- this task file
- `checkpoints/CURRENT.md`

Do not commit model weights/caches.

## Acceptance criteria

- [ ] Qwen3-0.6B feasibility attempted first
- [ ] at least one local model completes selected evaluation slice
- [ ] exact model id/revision/runtime/device/dtype recorded
- [ ] context cap recorded and enforced
- [ ] identical canonical record IDs used for comparisons
- [ ] probabilities/raw scores emitted when runtime supports them
- [ ] metrics/report generated
- [ ] Jev comparison included if successful Jev predictions exist; otherwise marked unavailable/provider-blocked
- [ ] next research recommendation based on evidence recorded
- [ ] full local merge gate passes

## Validation

See `docs/TDD.md` section 9.

## Stop conditions

Stop before scaling model size if:
- 0.6B already causes unacceptable memory pressure;
- record IDs differ from reference evaluation slice;
- runtime truncates context silently;
- probability computation uses incomparable class score semantics.

## Checkpoint log

Append execution evidence here.

## Handoff

After TASK-0006, do not automatically start fine-tuning. Use the report to define the next task: judge training/distillation, harder benchmarks, rubric decomposition, or selective escalation.
