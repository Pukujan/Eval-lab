# Objective and calibrated judgment under frozen rubrics: Grok Build, Jev, Qwen, and selective escalation

**Status:** working paper / benchmark results through EXP-028 complete; pending owner review
**Experiment family:** EXP-013, EXP-014, EXP-019, EXP-022, EXP-024, EXP-025,
EXP-027, and EXP-028
**Repository:** Eval Lab

## Abstract

We evaluate model judges on a frozen, typed objective-decision pool with
answer-key and deterministic-verifier gold labels. The central question is
whether a judge can be accurate, calibrated, auditable, and safely routed under
explicit rubrics—not which provider is cheapest. The primary comparison holds
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
A separate bakeoff (EXP-027) ran six compact local decision-model
configurations on one 16 GiB Apple M1 host over the identical 760 blind
records: Kev-4B was the strongest completed local arm at 64.34% blind accuracy
with full coverage, far below the provider routes, and Bespoke Nimble-9B and
Kev-9B were not run because their pinned configurations do not fit the host.
On LegalBench Hearsay (EXP-028, 94 test items), only Kev-4B (72.34%) clearly
exceeded the 56.38% always-`No` rate.
These results support objective, evidence-grounded domain pilots, but do not
establish general legal or financial reasoning ability.

## 1. Research question

The focused question is:

> Can a judge system achieve useful multi-domain accuracy and calibrated
> confidence on objectively labeled tasks, and can selective escalation make
> it operationally reliable?

The completed provider waves compare independently routed judges as a
measurement study. Model price is a secondary operational metric alongside
latency, coverage, and provider availability; it is not the scientific
selection criterion.

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

Cost and latency are recorded for operational analysis, but the primary
scientific criteria are correctness, calibration, consistency, coverage, and
evidence provenance.

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

![InferHub blind-wave accuracy and execution coverage](figures/benchmark/inferhub_wave_accuracy_coverage.png)

*Figure 1. InferHub routes are separated into conditional correctness and
execution coverage. DeepSeek V4 Flash has the highest conditional accuracy in
this wave, but Qwen3.8 Flash is the full-coverage operational default.*

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

![Direct blind-wave accuracy and execution coverage](figures/benchmark/direct_wave_accuracy_coverage.png)

*Figure 2. The direct wave keeps Grok, Jev, and Qwen on the same axes while
showing why a resolved-label score must be read together with coverage.*

### 3.3 Multidomain caution

The Qwen multidomain holdout prevents the latest high scores from being read as
universal reasoning scores. On a broader collection, blind accuracy varied by
source: 65.5% on GSM8K, 84.2% on professional law, 79.5% on machine learning,
and 99.2% on the Eval Lab objective pool. Small synthetic subsets ranged from
20% to 100%. The model is therefore highly task- and protocol-dependent.

Source: [EXP-013 multidomain report](../experiments/EXP-20260921-013-qwen-multidomain-holdout/report.md).

### 3.4 Local decision models on the frozen pool

EXP-027 runs compact, Jev-style local decision models one at a time on the
same frozen EXP-015 pool used by the provider waves (dataset fingerprint
`b7edd612...`; 648 public-selection and 760 blind record IDs). Every arm ran on
one 2020 MacBook Pro (Apple M1, 16 GiB unified memory) with pinned model and
runtime revisions and unquantized weights. These models score the fixed legal
labels natively instead of returning structured text through a provider API,
so the comparison with Sections 3.1–3.2 is same-records, not same-harness.
The blind holdout is primary; no model, prompt, or calibration choice was fit
on it.

| Arm | Resolved | Coverage | Accuracy | 95% Wilson interval | p50 latency |
|---|---:|---:|---:|---:|---:|
| Kev-4B | 760/760 | 100.00% | 64.34% | 60.87–67.67% | 1,047 ms |
| SemIf (Qwen3.5-4B) | 760/760 | 100.00% | 54.74% | 51.18–58.24% | 1,322 ms |
| Verdict 1.4 | 569/760 | 74.87% | 51.49% | 47.39–55.58% | 133 ms |
| Verdict pre-v1.4 | 526/760 | 69.21% | 50.38% | 46.12–54.63% | 71 ms |
| Kev-0.8B | 760/760 | 100.00% | 50.26% | 46.72–53.81% | 177 ms |
| Laya 421M | 748/760 | 98.42% | 48.53% | 44.96–52.11% | 141 ms |
| Bespoke Nimble-9B | not run | n/a | n/a | n/a | n/a |
| Kev-9B | not run | n/a | n/a | n/a | n/a |

Unresolved records are statuses, not wrong answers. Verdict returns an explicit
`__insufficient_evidence__` abstention (179 blind records for Verdict 1.4, 234
for the pre-v1.4 configuration of the same 151M weights); Verdict 1.4 and Laya
also skipped 12 blind records each at their 512-token context cap. Nimble-9B
(weights about 18 GB, unquantized only) and Kev-9B (upstream 32 GB Mac sizing)
were not loaded on the 16 GiB host; their absence is not a result.

Kev-4B is the only local arm whose interval clears the others, and most of its
advantage comes from pairwise records: 93.52% on the 108 blind pairwise
records versus 59.51% on the 652 single pass/fail records. The other arms score
between 48.59% and 53.83% on single records, and Kev-0.8B reaches only 31.48%
on the three-label pairwise records. Even Kev-4B is far below the same-record
provider results (Jev 89.87% and Qwen Flash 97.36% in EXP-022), so none of
these local models is a drop-in replacement for the provider judges on this
pool. Verdict's abstention lowers coverage to 69–75% while accepted-prediction
accuracy stays near 50%.

Public-selection results are descriptive only: Kev-4B 68.83% (648/648), SemIf
54.17% (648/648), Verdict pre-v1.4 50.22% (454/648), Laya 49.53% (638/648),
Verdict 1.4 48.94% (472/648), and Kev-0.8B 47.38% (648/648). Kev-4B is 4.49
points lower on blind than on public; SemIf is 0.57 points higher.

Source: [EXP-027 report](../experiments/EXP-20260924-027-local-decision-bakeoff/report.md)
and [results](../experiments/EXP-20260924-027-local-decision-bakeoff/results.json).

![Local decision models on EXP-027 and EXP-028](figures/benchmark/local_decision_models.png)

*Figure 5. EXP-027 blind accuracy (95% Wilson intervals) and coverage, and
EXP-028 Hearsay accuracy against the always-`No` rate. The two benchmarks are
separate panels and are not pooled; Nimble-9B and Kev-9B were not run.*

### 3.5 LegalBench Hearsay

EXP-028 applies the same local arms to the official fixed-label LegalBench
Hearsay task (CC BY 4.0), pinned at dataset revision `daec8237`. The task page
reports 95 test items, but the pinned machine-readable source contains 94; the
94 rows are used as distributed and no item was invented. Gold labels come
from the benchmark answer key. Of the 94 test labels, 53 are `No`, so always
answering `No` scores 56.38%.

| Arm | Resolved | Accuracy | 95% Wilson interval | Balanced accuracy | Macro F1 |
|---|---:|---:|---:|---:|---:|
| Kev-4B | 94/94 | 72.34% | 62.56–80.37% | 0.7326 | 0.7233 |
| Laya 421M | 94/94 | 61.70% | 51.60–70.89% | 0.5693 | 0.5215 |
| Kev-0.8B | 94/94 | 54.26% | 44.22–63.96% | 0.5695 | 0.5336 |
| SemIf (Qwen3.5-4B) | 94/94 | 48.94% | 39.07–58.88% | 0.5444 | 0.4125 |
| Verdict 1.4 | 94/94 | 43.62% | 34.04–53.70% | 0.5000 | 0.3037 |
| Verdict pre-v1.4 | 94/94 | 43.62% | 34.04–53.70% | 0.5000 | 0.3037 |

Only Kev-4B's interval lies above the majority-class rate. Laya's point
estimate exceeds it, but its interval includes it and its balanced accuracy is
0.5693. Both Verdict configurations answered `Yes` on all 94 items with no
abstentions, which is why their balanced accuracy is exactly 0.5000; SemIf
answered `Yes` on 87 of 94. Hearsay is one small task: it is kept separate from
EXP-027 and is not evidence of general legal reasoning.

Source: [EXP-028 report](../experiments/EXP-20260924-028-legalbench-hearsay/report.md)
and [results](../experiments/EXP-20260924-028-legalbench-hearsay/results.json).

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

![Grok protocol ablation](figures/benchmark/grok_protocol_ablation.png)

*Figure 3. No tested Grok protocol variant passed the preregistered public
gate; the blind typed baseline retained high coverage but the same severe
single/pairwise asymmetry.*

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

![Local Qwen 4B calibration](figures/benchmark/local_qwen_calibration.png)

*Figure 4. Split-safe temperature scaling improves the local Qwen 4B
confidence interface while leaving selected labels and accuracy unchanged.*

The EXP-027 local decision models expose native choice probabilities, and
Brier, NLL, and ECE are computed separately for single and pairwise records.
No temperature scaling was fitted in EXP-027, so these are raw native
confidences. They are uneven: Kev-4B's blind pairwise confidences are
comparatively well calibrated (Brier 0.1362, ECE 0.0890 on 108 records), but
its single-record confidences are not (Brier 0.5987, ECE 0.2594 on 652
records), and SemIf's blind single-record ECE is 0.3232. Laya's upstream
checkpoint warns that some confidence entries are uncalibrated, and Verdict's
probability metrics cover only non-abstaining predictions.

## 6. What this establishes

The completed evidence establishes:

1. Objective typed judging can be compared reproducibly across independent
   routes when records, rubrics, labels, and splits are frozen.
2. Coverage and parser/provider status materially change the operational
   ranking; conditional accuracy alone is insufficient.
3. Qwen Flash is the strongest completed operational route on this pool, while
   Jev is a strong high-coverage independent comparator; this is a measurement
   result, not a price ranking.
4. Grok's low score persists under the selected baseline, but remains a
   protocol-specific result rather than a universal capability estimate.
5. Calibration is a separate property from accuracy and requires validated
   probabilities plus a split-safe calibration procedure.
6. The compact local decision models tested so far are not competitive with
   the provider judges on this pool: the best completed arm, Kev-4B, reaches
   64.34% blind accuracy at full coverage, and Verdict's abstention lowers
   coverage while accepted-prediction accuracy stays near 50% (51.49% and
   50.38%).

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
- EXP-027 and EXP-028 ran on a single 16 GiB Apple M1 host. Bespoke Nimble-9B
  and Kev-9B were not run because their pinned, unquantized configurations
  exceed that host; the local comparison covers six configurations, not eight.
- Local arms use different context caps (512 tokens for Laya and Verdict 1.4,
  1,024 for Kev and Verdict pre-v1.4, 4,096 for SemIf); over-cap records are
  skipped statuses.
- LegalBench Hearsay has 94 test items, so its intervals are wide.

## 9. Reproducibility map

- [EXP-013 multidomain Qwen](../experiments/EXP-20260921-013-qwen-multidomain-holdout/)
- [EXP-014 independent Jev](../experiments/EXP-20260921-014-independent-jev-benchmark/)
- [EXP-019 calibration and head-to-head study](../experiments/EXP-20260921-019-calibrated-judge-study/)
- [EXP-022 direct Grok/Jev/Qwen wave](../experiments/EXP-20260922-022-fast-provider-wave/)
- [EXP-024 cross-provider wave](../experiments/EXP-20260922-024-inferhub-recommendation-wave/)
- [EXP-025 Grok protocol ablation](../experiments/EXP-20260922-025-grok-protocol-ablation/)
- [EXP-027 local decision-model bakeoff](../experiments/EXP-20260924-027-local-decision-bakeoff/)
- [EXP-028 LegalBench Hearsay](../experiments/EXP-20260924-028-legalbench-hearsay/)
- Figures: `scripts/generate_benchmark_figures.py` (requires the `figures`
  extra) regenerates every figure and `figures/benchmark/manifest.json`.

This paper is a working synthesis with EXP-028 analyzed. Its status remains
pending only for owner review; all headline tables are checked against
committed result artifacts.
