# EXP-20260921-017 — Local Qwen 4B judge calibration

Status: preregistered plan; no blind local labels requested.

## Hypothesis

Forced-choice probabilities from a locally hosted Qwen 4B judge will provide more
useful confidence information after temperature scaling fit on the public calibration
partition. Calibration is expected to improve held-out Brier score, NLL, ECE, and
risk/coverage behavior without changing the underlying evidence or using blind labels.

## Frozen inputs

- Source pool: the exact EXP-015 pool copied from EXP-014: 648
  `public_selection` records and 760 `blind_holdout` records.
- Records fingerprint:
  `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`.
- Blind record-ID fingerprint:
  `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`.
- Typed packet fingerprint:
  `0d07bd8b8b60bd7f0b5b7a5f5819b7d329ea121f686b240e465695b6f6eca1e4`.
- Gold provenance: benchmark answer keys and deterministic verifiers only.

## Arms and reference roles

| Arm | Access | Role | Probability status |
| --- | --- | --- | --- |
| local_qwen_4b | local Transformers runtime | new primary calibration arm | forced-choice log-likelihood probabilities |
| grok | existing direct xAI CLI run from EXP-015 | immutable label reference | unavailable in EXP-015 |
| luna | existing direct Codex subscription run from EXP-015 | immutable label reference | unavailable in EXP-015 |
| qwen_flash | existing YOLO-Auto run from EXP-015 | immutable label reference | unavailable in EXP-015 |
| jev_pinned | existing pinned EXP-014 output | immutable label reference | unavailable in EXP-014 |
| sol | direct Codex subscription, optional only | descriptive label reference | not required |

## Calibration rule

For the local arm, fit one scalar temperature per judgment mode (`single` and
`pairwise`) using only successful predictions with probabilities on the
`public_selection` partition. Apply those artifacts to the blind predictions without
reading blind labels. Preserve raw probabilities and calibrated probabilities as
separate fields/files. If a mode has insufficient successful calibration records, mark
that mode unavailable rather than fitting on blind data.

## Metrics and comparisons

- Accuracy, balanced accuracy, macro-F1, and Wilson 95% accuracy interval.
- Resolved coverage, unresolved/runtime status counts, p50/p95 latency.
- Raw and calibrated Brier score, negative log likelihood, and ECE.
- Raw and calibrated risk/coverage and coverage at target error rates.
- Calibration temperatures and exact fit-record IDs/fingerprint.
- Same-record agreement with immutable EXP-015 and EXP-014 reference outputs.
- Runtime identity, model revision, context cap, device, dtype, and score semantics.

Label-only arms are not assigned calibration metrics. A prompt-requested confidence
field from an external provider would be self-reported, not native, and is outside
this experiment.

## Exclusions and stopping

No model selection, prompt tuning, temperature fitting, or threshold selection may
read blind labels. Provider failures and local context errors remain unresolved and
receive no fallback labels. Any changed model, prompt, pool, calibration split, or
merge rule requires a new experiment ID.

## Planned artifacts

- `README.md`, `PLAN.md`, `experiment.yaml`;
- local smoke, public calibration, and blind prediction directories;
- raw and calibrated prediction JSONL;
- calibration artifacts, results, reports, reference comparison, and checksums.
