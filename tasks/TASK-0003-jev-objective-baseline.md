# TASK-0003 — Jev Free Objective Baseline Runner

- Status: queued
- Owner: Luna/local agent
- Priority: P0
- GitHub issue: #7
- Depends on: TASK-0002
- Branch: task/TASK-0003-jev-objective-baseline

## Goal

Evaluate OpenCode Jev Free as a structured classification judge using canonical fixture records.

## Model contract

Required model id: `jev-1.13-free`.

Never automatically fall back to `jev-1.13` or another paid route.

If free Jev is quota-limited, emit `rate_limited` and checkpoint it.

## Inputs

- TASK-0002 schemas/fixtures
- existing Jev client
- relevant SDD/TDD sections
- `docs/ACCESS_MODEL_MATRIX.md`

## Outputs

- normalized Jev adapter
- `jev-direct-v1`
- `jev-atomic-v1`
- deterministic runner
- mocked response tests
- normalized prediction JSONL
- optional live run

## Acceptance criteria

- [ ] outgoing default model asserted as `jev-1.13-free`
- [ ] test proves no paid fallback
- [ ] direct single/pairwise normalized
- [ ] atomic normalized
- [ ] probabilities retained
- [ ] 429 -> rate_limited
- [ ] no fabricated labels on provider errors
- [ ] no secret leakage
- [ ] full local merge gate passes

## Validation

Intercept the outgoing request in tests and assert `model == "jev-1.13-free"`.

## Stop conditions

Stop if provider semantics cannot be mapped reliably or secret persistence would be required.

## Checkpoint log

Append evidence here.

## Handoff

TASK-0004 consumes normalized predictions. TASK-0007 later revisits Jev in the external-model bakeoff.
