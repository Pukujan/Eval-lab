# Eval Lab Project Contract

## Main goal

Build a reproducible laboratory for evaluating and calibrating lightweight AI judge systems across multiple domains, with objective benchmarks and deterministic verifiers used as the primary source of truth wherever possible.

The project is not primarily about making a small model imitate a frontier model. It is about measuring whether lightweight judges can become reliable, calibrated decision systems under explicit rubrics.

## Initial systems under test

- Jev 1.13 Free / Jev 1.13 as a structured classification judge
- Qwen3-4B as a local generative judge when hardware permits
- Qwen3-1.7B as a lighter local generative baseline
- a compact encoder classifier such as ModernBERT-base for pure classification
- stronger chat models such as Luna, Sol, or Grok only as optional critics, rubric designers, adversaries, and disagreement analysts

## Initial research question

Can a lightweight judge achieve useful multi-domain accuracy and calibrated confidence on objectively labeled evaluation tasks, and can selective escalation make it operationally reliable?

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
- training large local models before baselines are measured

## Context contract for v0

All judge inputs should fit a common short-context envelope, initially 4,096 tokens or less. This is a deliberate experimental constraint, not a claim about model capability.

## Project phases

1. Lab bootstrap and reproducibility.
2. Objective benchmark adapters and canonical record schema.
3. Jev baseline and calibration.
4. Lightweight local baselines.
5. Bias and perturbation tests.
6. Selective escalation experiments.
7. Optional judge-specific fine-tuning only after baseline evidence warrants it.

## Definition of success for v0

v0 is successful when another agent can clone the repo, reproduce at least one objective benchmark run, evaluate Jev and one local baseline on the same held-out data, fit calibration on a separate split, and regenerate the report from committed configuration plus documented external credentials.
