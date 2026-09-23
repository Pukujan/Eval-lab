# EXP-20260921-014 — Independent Jev Benchmark Plan

## Hypothesis

Pinned Jev will be competitive with Qwen and the frozen local student on objective typed decisions, while its native probabilities, option-order behavior, and cross-domain calibration may differ by dataset family.

## Primary comparison

Compare pinned `typesafe/jev-1.13` with the same canonical record IDs evaluated by Qwen3.8 Flash and the frozen TASK-0009 TF-IDF/logistic-regression student. Keep rolling `~typesafe/jev-latest` as a separate canary. Do not pool JevBench measurements into this comparison.

## Planned data

Use a new source/split manifest derived from the current objective pool after TASK-0011 is complete:

- EvalLab-Select v0.1.0 ARC anchor;
- ARC-Easy;
- GSM8K;
- the preregistered MMLU subjects;
- four deterministic Eval Lab synthetic domains.

The final source revisions, record counts, source-family partition, and SHA-256 fingerprint will be frozen in this experiment before final evaluation. No record is duplicated to meet a target count. JevBench task text and labels are excluded.

## Protocol arms

1. pinned Jev `typesafe/jev-1.13`, native Choice probabilities;
2. rolling Jev `~typesafe/jev-latest`, reported as a separate canary;
3. Qwen3.8 Flash through the frozen YOLO-Auto route, label-only unless verified probabilities become available;
4. frozen local TASK-0009 arm D;
5. deterministic/majority baselines.

Every arm receives the same canonical state, rubric, legal label set, context cap, and record IDs. Gold labels are withheld from provider request construction and used only after prediction normalization for scoring.

## Robustness controls

- fixed label-order permutation on a predeclared subset;
- rubric paraphrase pair on a predeclared subset;
- three repeated calls on a predeclared subset to measure stability;
- invalid/malformed output and provider-failure accounting;
- no automatic retry in the primary pass; any recovery pass is a separately named execution artifact;
- a deterministic answer-key/verifier baseline and majority-class baseline;
- native Jev distributions kept separate from verbalized distributions.

## Metrics

Primary: accuracy, balanced accuracy, macro F1, unresolved rate, and 95% Wilson intervals by dataset and arm.

Probability-supported: multiclass Brier, NLL, ECE, reliability bins, and risk/coverage. These are computed only for native, normalized probability maps whose label set exactly matches the frozen legal options.

Operational: p50/p95 raw caller latency, actual token/cost metadata, calls per 1,000, status counts, and first-call/cold-start annotation where available.

Robustness: option-order invariance, paraphrase agreement and both-correct rate, repeated-call label stability, and probability stability.

## Exclusion and stopping rules

- JevBench items, labels, and result artifacts are excluded from the primary data.
- A provider/model mismatch, malformed probability vector, or schema failure is retained as status evidence and is not repaired into a label.
- A 401/403/429 or repeated infrastructure failure stops that provider pass; unattempted records remain unattempted.
- Changing the source, rubric, model version, prompt, calibration, or split after final evaluation requires a new experiment ID.
- Final labels cannot select prompts, thresholds, source records, or stopping decisions.

## Reproducibility outputs

The completed experiment will contain a frozen source/split manifest, checksums, normalized predictions, provider ledger, results JSON, per-domain report, perturbation report, limitations, and exact reproduction commands. The paper will cite raw artifacts rather than JevBench's composite score.

## Execution gate

This plan is not executable yet. First finish TASK-0011 and record its final Qwen blind-holdout status. Then freeze EXP-014's source/split manifest and commit it before any live Jev call.
