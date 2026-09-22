# EXP-20260921-019 — Calibrated judge construction and independent head-to-head

## Status

Planned. This preregistration must be committed before any new derived result
is generated.

## Hypothesis

A rubric-grounded typed decision contract plus split-safe calibration produces a
more auditable judge than an unconstrained label stream. Temperature scaling of
local forced-choice probabilities should improve held-out confidence quality
without changing the selected labels. Independent judge routes will show
meaningful head-to-head differences even when they receive the same rubric and
objective record.

## Study design

The exact EXP-015 pool is reused read-only. The public-selection partition is
the calibration/method partition; the 760-record blind holdout is the primary
comparison partition. Gold comes only from trusted benchmark answer keys and
deterministic verifiers. No judge output is used as gold.

The common rubric packet is the frozen Eval Lab System-One typed protocol with
legal labels `pass/fail` for single records and `A/B/TIE` for pairwise records.
Each prediction must preserve the canonical record ID, model identity, prompt
version, protocol version, and execution status.

## Arms

| Arm | Route | Role |
|---|---|---|
| Grok Build | direct authenticated xAI `grok` CLI | external label judge |
| Jev | OpenRouter Jev-only route | external typed judge |
| Qwen Flash | YOLO-Auto `qwen3.8-flash` | external label judge |
| Local Qwen 4B | local CUDA 4-bit forced-choice scorer | probability-bearing calibrated judge |

Luna and Sol are excluded from this experiment because the orchestrator's
vendor-independent comparison policy excludes those vendor-domain arms. Their
artifacts are not deleted or altered, but they are not included in EXP-019
results, figures, pairwise comparisons, calibration, adjudication, or claims.

## Calibration protocol

Calibration is a post-hoc transformation of a frozen judge's probability
outputs, not retraining and not relabeling. Local Qwen 4B emits normalized
probabilities from conditional log-likelihoods over the legal labels. Fit one
scalar temperature per judgment mode on public-selection labels only, then
apply the frozen artifact to blind predictions.

External arms are label-only in the completed artifacts. They remain eligible
for label-quality and agreement comparisons but do not receive invented
probability metrics. A future provider-native probability run would require a
new experiment ID.

## Primary outputs

1. A method description of rubric construction, typed normalization, gold
   provenance, split discipline, and calibration fitting.
2. A non-Luna head-to-head label comparison on the blind holdout.
3. Local Qwen raw-versus-calibrated accuracy, Brier, NLL, ECE, and risk/coverage
   results.
4. Per-domain metrics and same-record agreement where predictions are present.
5. A limitations section distinguishing model quality, confidence quality, and
   execution missingness without making provider reliability the research
   question.

## Exclusions and stopping rules

- Do not add Luna or Sol after preregistration.
- Do not call OpenCode for any arm.
- Do not use OpenRouter for Grok, Qwen Flash, or Codex models; OpenRouter is
  Jev-only.
- Do not overwrite EXP-014, EXP-015, EXP-016, or EXP-017.
- Do not refit calibration on blind labels.
- Do not treat missing provider calls as wrong labels or silently invent labels.
- If a prompt, pool fingerprint, model ID, or calibration rule changes, stop and
  create a new experiment ID.
