# Eval Lab Project Contract

## Main goal

Build a reproducible laboratory for evaluating and calibrating lightweight AI judge systems across multiple domains, with objective benchmarks and deterministic verifiers used as the primary source of truth wherever possible.

The project is not primarily about making a small model imitate a frontier model. It is about measuring whether lightweight judges can become reliable, calibrated decision systems under explicit rubrics.

## Initial systems under test

- Jev 1.13 Free / Jev 1.13 as a structured classification judge
- Qwen3-0.6B as the minimum-footprint local generative judge baseline
- Qwen3-1.7B as the preferred stronger local baseline when feasible
- Qwen3-4B as an optional stretch baseline when hardware permits
- a compact encoder classifier as a later alternative if decoder models are not competitive
- stronger chat models such as Luna, Sol, or Grok only as optional critics, rubric designers, adversaries, and disagreement analysts

## Research question

When independent judges, from small local models to frontier APIs, receive identical typed decisions with objective gold labels, how do their accuracy and coverage differ, and what does accuracy-only reporting hide?

The canonical answer is [`paper/paper.md`](paper/paper.md), built on the offline analysis [EXP-029](experiments/EXP-20260924-029-consolidated-judge-analysis/) (TASK-0056).

The original question (can a lightweight judge reach useful multi-domain accuracy and calibrated confidence, and can selective escalation make it operationally reliable?) is narrowed to the above. Selective escalation, routing, confidence calibration and domain pilots are future work; see Section 7 of the paper and [`paper/archive/`](paper/archive/).

## Primary metrics

- accuracy and balanced accuracy
- macro F1 where applicable
- Brier score
- negative log likelihood
- expected calibration error
- position-swap consistency
- rubric-paraphrase consistency
- risk/coverage and coverage at target error rates
- latency and cost per 1,000 decisions

## Non-goals for v0

- subjective creative-writing quality
- long-context judging beyond the local hardware budget
- replacing expert human review in ambiguous domains
- treating any teacher model as infallible ground truth
- training or fine-tuning a local judge before baseline measurement is trustworthy

## Context contract for v0

All judge inputs should fit a common short-context envelope, initially 4,096 tokens or less. Experiments may use a lower cap when local hardware requires it, but every comparison must record the cap and compare systems on the same slice.

## Program plan

TASK-0001 established local reproducibility.

The authorized v0 implementation sequence is:

1. TASK-0002 — canonical schema + deterministic objective fixtures.
2. TASK-0003 — Jev objective baseline runner.
3. TASK-0004 — metrics + statistical calibration + selective-risk analysis.
4. TASK-0005 — first public objective benchmark adapter using ARC-Challenge.
5. TASK-0006 — lightweight local judge baseline on the same canonical records.

A provider outage or Jev quota limit may block a live TASK-0003 run, but must not block TASK-0004 through TASK-0006. Provider failures are execution states, not incorrect predictions.

## Phase gates

### Gate A — measurement substrate

TASK-0002 is complete only when schemas, deterministic fixtures, split discipline, provenance, serialization, and perturbation invariants are enforced by tests.

### Gate B — provider judge

TASK-0003 is complete when the Jev runner is reproducible and mock/contract tested. A live successful call is recorded when provider quota permits; a provider 429 does not invalidate the implementation.

### Gate C — measurement validity

TASK-0004 is complete only when calibration cannot fit on test labels, known-value metric tests pass, and risk/coverage output is reproducible.

### Gate D — real public data

TASK-0005 is complete only when the source revision/license/fingerprint and deterministic split mapping are recorded and the adapter produces canonical records reproducibly.

### Gate E — local baseline

TASK-0006 is complete when at least one local model that fits the machine produces normalized predictions on the same evaluation slice and a comparison report is generated.

## Definition of success for v0

v0 is successful when another agent can clone the repo and:

1. reproduce the synthetic objective fixture suite;
2. run the Jev adapter when quota is available or reproduce its mocked provider contract otherwise;
3. compute raw and calibrated metrics without test leakage;
4. reproduce the ARC-Challenge canonical evaluation slice;
5. run at least one local Qwen baseline on the same slice;
6. regenerate a comparison report from committed configuration and documented external credentials;
7. resume work from `checkpoints/CURRENT.md` and the active task file without relying on chat history.

## TASK-0010 research-release phase

After TASK-0009, Eval Lab moved from baseline construction to selective escalation and publication-quality reproducibility. That TASK-0010 draft is archived at `paper/archive/selective-escalation/`; TASK-0056 replaced it as the canonical paper with `paper/paper.md`.

TASK-0010 must produce:
- a frozen selective-escalation experiment;
- a compact versioned benchmark release;
- machine-readable provenance and validation metadata;
- an arXiv-ready independent research paper source.

The research release uses RO-Crate 1.3, PROV-O, stable SHACL, CFF 1.2.0, DataCite-compatible metadata, semantic versioning, and SHA-256 checksums.

A headline result is not publication-ready unless it can be traced from paper table/figure -> results artifact -> routing/prediction artifacts -> benchmark/model/calibration/source provenance.
