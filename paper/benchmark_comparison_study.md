# Benchmark performance of typed objective judges: Grok Build, Jev, Qwen, and low-cost routes

**Status:** working paper / benchmark results through EXP-025 complete; pending owner review
**Experiment family:** EXP-013, EXP-014, EXP-019, EXP-022, EXP-024, and EXP-025
**Repository:** Eval Lab

## Abstract

We evaluate model judges on a frozen, typed objective-decision pool with
answer-key and deterministic-verifier gold labels. The primary comparison holds
the records, rubric, legal labels, and blind split fixed while changing the
model route. We report correctness separately from execution coverage and keep
provider, rate-limit, and parse failures unresolved. Across the completed
direct and InferHub waves, Qwen Flash and Qwen Max are the strongest operational
routes on this pool, Jev is highly reliable but less accurate, and Grok Build
returns valid outputs but underperforms sharply under the current typed judge
protocol. The Grok result is treated as a protocol-specific diagnostic rather
than evidence of universal model weakness. EXP-025 completed a preregistered
prompt/output ablation with no winning protocol replacement: the selected
typed baseline remained low on the blind holdout and the single/pairwise
asymmetry persisted. A separate calibration study shows that local Qwen 4B
confidence can be calibrated split-safely even when its labels remain weak.
These results support objective, evidence-grounded domain pilots, but do not
establish general legal or financial reasoning ability.

## 1. Research question

The focused question is:

> How accurately and reliably do inexpensive and independently routed model
> judges solve the same typed objective decisions, and what can the completed
> evidence tell us about Grok Build, Jev, Qwen, and calibration?

This paper is a benchmark-comparison study. Inference-provider recommendation
policy, catalog ranking, and general production routing are supporting
artifacts, not the scientific subject of the paper.

## 2. Evaluation contract

Each record contains a question, candidate answer(s), a rubric, a closed legal
label set, and an objective gold label. Single records use `pass`/`fail`;
pairwise records use `A`/`B`/`TIE`. Gold provenance is either a trusted answer
key or a deterministic verifier. Model judgments are never promoted to gold.

The main frozen provider pool contains 1,408 records: 648 public-selection
records and 760 source-problem-disjoint blind-holdout records. The same typed
packet is sent to each direct comparison arm. Accuracy is conditional on a
resolved label; coverage is the resolved fraction of all records. Parse and
provider failures remain explicit statuses rather than being silently counted
as wrong or right.

## 3. Completed benchmark results

### 3.1 Latest blind cross-provider wave

The latest eight-route comparison uses the same 760-record blind holdout. The
table reports conditional accuracy and all-record coverage together because a
high score on a small resolved subset is not operationally sufficient.

| Model family / route | Resolved | Coverage | Accuracy |
|---|---:|---:|---:|
| Qwen3.8 Flash / `ali/qwen3.8-flash` | 760/760 | 100.00% | 99.21% |
| Qwen 3.8 Max / `ali/qwen3.8-max` | 760/760 | 100.00% | 99.08% |
| GLM 5.2 / `ali/glm-5.2` | 727/760 | 95.66% | 99.17% |
| Kimi K2.7 Code / `ali/kimi-k2.7-code` | 758/760 | 99.74% | 98.55% |
| DeepSeek V4 Flash / `cbcn/deepseek-v4-flash` | 611/760 | 80.39% | 99.84% |
| DeepSeek V4.1 Flash / `cb/deepseek-v4.1-flash` | 621/760 | 81.71% | 98.71% |
| GLM 5.3 Flash / `cbcn/glm-5.3-flash` | 756/760 | 99.47% | 97.88% |
| MiniMax M3 / `cbcn/minimax-m3` | 744/760 | 97.89% | 97.98% |

DeepSeek V4 Flash has the highest conditional accuracy, but 149 of 760 blind
records were unresolved by the current visible-content parser. Qwen3.8 Flash
is therefore the strongest operational route in this run: it combines the
highest full-coverage accuracy with no unresolved blind records.

Source: [EXP-024 results](../experiments/EXP-20260922-024-inferhub-recommendation-wave/RESULTS.md).

### 3.2 Direct Grok, Jev, and Qwen wave

The direct comparison was run independently over the same typed pool. The
blind results were:

| Arm | Resolved | Coverage | Accuracy |
|---|---:|---:|---:|
| Grok 4.6 Build | 757/760 | 99.61% | 43.46% |
| Grok 4.7 Build | 726/760 | 95.53% | 43.53% |
| Qwen Flash | 759/760 | 99.87% | 97.36% |
| Jev | 760/760 | 100.00% | 89.87% |

Jev and Qwen agree on approximately 89.9% of comparable blind records, while
Grok agrees with each of them on less than half. Grok 4.6 and 4.7 agree with
each other on approximately 95.3% of comparable records, but 4.7 does not
improve accuracy and has worse coverage.

Source: [EXP-022 blind comparison](../experiments/EXP-20260922-022-fast-provider-wave/runs/blind-comparison-20260922/report.md).

### 3.3 Multidomain caution

The Qwen multidomain holdout prevents the latest high scores from being read as
universal reasoning scores. On a broader collection, blind accuracy varied by
source: 65.5% on GSM8K, 84.2% on professional law, 79.5% on machine learning,
and 99.2% on the Eval Lab objective pool. Small synthetic subsets ranged from
20% to 100%. The model is therefore highly task- and protocol-dependent.

Source: [EXP-013 multidomain report](../experiments/EXP-20260921-013-qwen-multidomain-holdout/report.md).

## 4. What happened to Grok?

The Grok result is reproducible across EXP-019 and EXP-022, but its failure
pattern is not yet diagnostically complete. Grok generally returned valid
structured responses, so the primary problem was not simply authentication,
transport, or streaming coverage. Earlier diagnostics showed strong
mode-dependence: near-chance single decisions and a severe collapse on
pairwise decisions. The Build CLI surfaced `grok-4.6-build` and
`grok-4.7-build`, so the requested and resolved model identities were retained
separately.

The evidence supported a **protocol/harness hypothesis**, but the completed
ablation did not validate a replacement contract. The public packet combined
opaque short labels, a provider-neutral typed schema, and an agent-oriented
Build CLI. EXP-025 tested explicit task wording, semantic labels, native-schema
removal, and the original typed contract on a balanced public sample. No
alternative passed the preregistered gate. The selected typed baseline then
completed the blind rerun at 757/760 coverage and a mode-balanced score of
0.2586, with 49.85% single accuracy and 1.87% pairwise accuracy among resolved
labels. The scientifically correct statement is:

> Grok Build underperforms sharply under the current Eval Lab typed-judge
> harness. The ablation found a real Windows UTF-8 reader defect in one
> no-schema route, but fixing that defect and changing task labels/schema did
> not produce a materially better protocol. The result remains a
> protocol-specific diagnosis, not evidence of universal Grok weakness.

Source: [EXP-025 final report](../experiments/EXP-20260922-025-grok-protocol-ablation/RESULTS.md).

## 5. Calibration evidence

No label-only external provider in the completed comparison exposes a validated
native probability map, so Jev, Qwen Flash, and Grok are not called calibrated
merely because they are accurate or consistent.

The completed local Qwen 4B calibration experiment is different. Scalar
temperature scaling was fit on public calibration records only and then frozen
for the blind holdout. It left labels and accuracy unchanged but improved blind
Brier score from 0.7037 to 0.5160, NLL from 1.0767 to 0.7430, and ECE from
0.3411 to 0.0783. This is reliable evidence that the **local Qwen 4B
confidence interface** was calibrated split-safely; it is not evidence that
the weak judge became more accurate, nor that the external label-only models
are calibrated.

Source: [EXP-019 calibration study](../experiments/EXP-20260921-019-calibrated-judge-study/report.md).

## 6. What this establishes

The completed evidence establishes:

1. Objective typed judging can be compared reproducibly across independent
   routes when records, rubrics, labels, and splits are frozen.
2. Coverage and parser/provider status materially change the operational
   ranking; conditional accuracy alone is insufficient.
3. Qwen Flash is the strongest completed operational route on this pool, while
   Jev is a strong high-coverage independent comparator.
4. Grok's low score persists under the selected baseline, but remains a
   protocol-specific result rather than a universal capability estimate.
5. Calibration is a separate property from accuracy and requires validated
   probabilities plus a split-safe calibration procedure.

## 7. Real-world objective-data extension

The next benchmark tracks should use external sources with explicit snapshots,
source citations, and deterministic verifiers:

- GLEIF: LEI/status/name/date/entity-resolution and parent-child relationship
  records. This is structured registry data, not legal-opinion reasoning.
- SEC EDGAR/XBRL: filing metadata, accession/CIK matching, reported facts,
  units/periods, arithmetic reconciliation, and citation-span extraction. A
  filing is gold for what the issuer reported, not automatically for whether
  every issuer claim is true.
- CourtListener: citation verification, docket chronology, case metadata,
  quote attribution, and retrieval-plus-evidence tasks. Legal holding quality
  requires expert adjudication and should not be treated as automatically
  objective.

Each domain needs a new experiment ID and entity/case-disjoint splits. These
tracks are not included in the current benchmark scores.

## 8. Limitations

- The current pool is objective and typed but narrower than real financial or
  legal work.
- The newest cross-provider scores are route- and parser-specific.
- Conditional accuracy excludes unresolved provider and parse statuses, which
  are reported separately.
- The Grok ablation is complete, but harness-versus-model attribution remains
  bounded to the tested protocol family.
- The separate Bonsai 2 27B Mac run is retained in its own worktree and is not
  pooled into these cross-provider tables until its immutable artifact is
  transferred into the paper release.

## 9. Reproducibility map

- [EXP-013 multidomain Qwen](../experiments/EXP-20260921-013-qwen-multidomain-holdout/)
- [EXP-014 independent Jev](../experiments/EXP-20260921-014-independent-jev-benchmark/)
- [EXP-019 calibration and head-to-head study](../experiments/EXP-20260921-019-calibrated-judge-study/)
- [EXP-022 direct Grok/Jev/Qwen wave](../experiments/EXP-20260922-022-fast-provider-wave/)
- [EXP-024 cross-provider wave](../experiments/EXP-20260922-024-inferhub-recommendation-wave/)
- [EXP-025 Grok protocol ablation](../experiments/EXP-20260922-025-grok-protocol-ablation/)

This paper is a working synthesis with EXP-025 analyzed. Its status remains
pending only for owner review; all headline tables are checked against
committed result artifacts.
