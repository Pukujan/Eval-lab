# TASK-0003 — Jev Objective Baseline Runner

- Status: queued
- Owner: Luna/local agent
- Priority: P0
- GitHub issue: #7
- Depends on: TASK-0002
- Branch: task/TASK-0003-jev-objective-baseline

## Goal

Evaluate Jev as a structured classification judge using the canonical fixture records and normalize all provider outcomes into JudgePrediction.

## Why

Jev is specifically optimized for typed classification/decision tasks and may be a strong cheap judge baseline. The claim must be tested against objective labels.

## Inputs

- TASK-0002 schemas/fixtures
- existing OpenCode/Jev client
- `docs/SDD.md` section 7
- `docs/TDD.md` section 6

## Outputs

- provider adapter under `src/eval_lab/judges/`
- protocol definitions for `jev-direct-v1` and `jev-atomic-v1`
- deterministic runner/CLI
- mocked provider tests
- normalized prediction JSONL capability
- optional live smoke/fixture run if quota permits
- checkpointed provider state

## Required implementation

Direct protocol:
- PASS/FAIL for single candidate
- A/B/TIE for pairwise

Atomic protocol:
- typed criterion-level questions
- deterministic repository-side aggregation
- retain criterion probabilities/results

Execution handling:
- 200 -> ok
- 429 -> rate_limited + Retry-After metadata
- 5xx/network -> provider_error
- malformed -> parse_error

Never serialize API keys.

No automatic waiting beyond a short retry explicitly bounded in code/config.

## Allowed files

- `src/eval_lab/judges/`
- existing `src/eval_lab/jev.py` as needed
- runner scripts/modules
- `tests/`
- experiment stub/output metadata if a live run succeeds or is provider-blocked
- this task file
- `checkpoints/CURRENT.md`

## Acceptance criteria

- [ ] direct single classification normalized
- [ ] direct pairwise classification normalized
- [ ] atomic criterion classification normalized
- [ ] returned probabilities retained
- [ ] 429 handled as rate_limited, not wrong answer
- [ ] provider errors do not fabricate labels
- [ ] secret leakage tests pass
- [ ] fixture runner can resume/re-run deterministically
- [ ] all mocked tests and full local merge gate pass
- [ ] live result recorded if provider available, otherwise provider-block explicitly checkpointed

## Validation

See `docs/TDD.md` section 6.

Do not require a successful live provider call to validate local provider-contract logic when external quota is unavailable.

## Stop conditions

Stop and checkpoint if:
- provider API semantics contradict the normalized schema;
- provider response lacks enough information to map typed decisions reliably;
- implementation would need storing secrets/raw sensitive headers.

## Checkpoint log

Append execution evidence here.

## Handoff

TASK-0004 consumes canonical predictions. If live Jev remains quota-blocked, provide mocked/synthetic prediction fixtures so metrics/calibration work can continue.
