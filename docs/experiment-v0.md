# Experiment v0

## Research question

Can a fast structured decision model or lightweight local model act as a calibrated rubric judge on multi-domain tasks when labels are anchored in objective benchmarks?

## Systems

- Jev 1.13 Free / Jev 1.13
- Qwen3-4B (local, short-context contract)
- Qwen3-1.7B (lighter local baseline)
- Optional encoder baseline such as ModernBERT-base
- Strong chat models used only for analysis / data enrichment

## Domains

Start with four objectively scorable domains:

1. multiple-choice knowledge/reasoning
2. arithmetic / short math
3. instruction-following constraints
4. code outputs with executable tests

## Splits

Use source-problem-level splitting so variants of the same source problem never cross train/calibration/test boundaries.

- train: optional student training
- dev: prompt/rubric iteration
- calibration: fit thresholds / temperature / isotonic calibration
- test: frozen final evaluation

## Metrics

- accuracy and balanced accuracy
- macro F1
- Brier score
- negative log likelihood
- expected calibration error
- A/B position-swap consistency
- risk-coverage curve
- abstention coverage at target error rates

## Jev protocol

Jev is evaluated as a classifier, not as a generative grader. Use its typed `noul`, `choice`, and `score` questions and retain returned probabilities. Do not convert teacher agreement into ground truth.

Run at least three prompt/rubric forms:
- concise criterion
- decomposed atomic criteria
- paraphrased criterion

Use identical held-out examples for every system.
