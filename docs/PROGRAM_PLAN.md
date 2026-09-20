# V0 Program Plan — TASK-0002 through TASK-0006

## Purpose

This document is the execution map for the next five tasks. Each task has its own authoritative task file. This file defines ordering, gates, and what may proceed when external services are unavailable.

## Dependency graph

~~~
TASK-0001 complete
      |
      v
TASK-0002 canonical schema + fixtures
      |
      +-------------------+
      |                   |
      v                   v
TASK-0003 Jev         TASK-0004 metrics/calibration
      |                   |
      +---------+---------+
                |
                v
TASK-0005 ARC-Challenge adapter
                |
                v
TASK-0006 lightweight local judge
~~~

Operationally Luna should execute 0002 -> 0003 -> 0004 -> 0005 -> 0006.

If Jev is still rate-limited, TASK-0003 may close as implementation-complete/provider-blocked after all mocked and local contract tests pass. TASK-0004 continues using deterministic fixture predictions.

## Program-level invariants

- Objective gold is never derived solely from an LLM judgment.
- Variants sharing a source_problem_id never cross split boundaries.
- Calibration fit never consumes test labels.
- A/B order perturbation must invert A/B gold and preserve TIE.
- Provider failure is not scored as a wrong answer.
- Every prediction identifies model/provider/prompt version and execution status.
- Every public dataset run records source revision, license, and fingerprint.
- Every local-model run records exact model revision when available, runtime, device, dtype/quantization, and context cap.
- Completed experiment directories are immutable.

## TASK-0002 — Canonical schema and deterministic fixtures

Outcome: the lab has a stable internal language for source problems, rubrics, candidates, gold labels, predictions, and split provenance.

Required artifacts:
- `src/eval_lab/schema.py`
- `src/eval_lab/datasets/synthetic.py`
- `src/eval_lab/verifiers/`
- deterministic fixture export command
- tests for schema and scientific invariants

No network/provider calls.

## TASK-0003 — Jev objective baseline runner

Outcome: Jev can consume canonical judge records and return normalized single/pairwise predictions with probabilities and execution status.

Required protocol versions:
- `jev-direct-v1`: direct single or pairwise classification
- `jev-atomic-v1`: criterion-level typed questions with deterministic aggregation

A 429/Retry-After response is recorded as rate_limited and does not become a prediction.

## TASK-0004 — Metrics and calibration

Outcome: frozen predictions can be evaluated and calibrated using separate calibration/test splits.

Required metrics:
- accuracy
- balanced accuracy
- macro F1
- Brier
- NLL
- ECE
- A/B swap consistency
- risk/coverage
- coverage at target error rates
- latency summary

Required calibration:
- scalar temperature scaling for multiclass score/probability vectors
- binary Platt/logistic scaling where applicable
- isotonic regression as optional non-parametric method when sample size is sufficient

## TASK-0005 — First public benchmark

Selected v0 benchmark: `allenai/ai2_arc`, config `ARC-Challenge`.

Reason:
- objective answer keys
- short contexts
- multiple-choice format maps cleanly to judge records
- manageable local size
- published dataset license is CC BY-SA 4.0

The adapter must record the exact resolved source revision and a deterministic fingerprint. Do not silently rely on whatever "latest" happens to be in a future run.

## TASK-0006 — Lightweight local judge

Required baseline ladder:

1. Qwen/Qwen3-0.6B — required first feasibility target.
2. Qwen/Qwen3-1.7B — preferred additional baseline if the machine is comfortable.
3. Qwen/Qwen3-4B — optional stretch only.

Do not fail TASK-0006 merely because 4B is too large.

The judge should use forced-choice scoring where practical:
- PASS vs FAIL for binary tasks
- A vs B vs TIE for pairwise tasks

Normalize exact-label continuation log-likelihoods with softmax to obtain probabilities. If a runtime cannot expose scores, record probability support as unavailable rather than inventing confidence.

## End-of-program output

The first v0 comparison report should contain at minimum:

| system | dataset | accuracy | Brier | ECE | swap consistency | coverage @ <=2% error | latency |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Jev direct | synthetic/ARC | ... | ... | ... | ... | ... | ... |
| Jev atomic | synthetic/ARC | ... | ... | ... | ... | ... | ... |
| local Qwen | synthetic/ARC | ... | ... | ... | ... | ... | ... |

Unavailable values must be marked unavailable, not filled with guessed numbers.
