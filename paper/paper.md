# Accuracy is not enough: correctness and coverage of independent judges on identical objective decisions

**Status:** working paper; pending owner review<br />
**Evidence:** EXP-013, EXP-014, EXP-015, EXP-016, EXP-017, EXP-019, EXP-022, EXP-024, EXP-025, EXP-027; consolidated in EXP-029<br />
**Repository:** [Eval Lab](https://github.com/Pukujan/Eval-lab/tree/main)

## Abstract

Model judges are usually compared by one accuracy number. We gave 25 judge arms,
from sub-billion-parameter local models to frontier APIs, the same 760 blind,
typed decisions with objective gold labels (answer keys or deterministic
verifiers). For each run we report two things separately: coverage, the share
of records that received a legal label, and accuracy. We report accuracy both
among answered records and over all 760, where an unanswered record earns
nothing. Wilson intervals and exact paired McNemar tests with Holm correction
come from a committed script, not from hand-entered tables.

The best full-coverage API routes reached 99.21% (Qwen3.8 Flash) and 99.08%
(Qwen 3.8 Max). The two are statistically indistinguishable. Accuracy-only
reporting hid three kinds of failure. The run with the highest conditional
accuracy, DeepSeek V4 Flash at 99.84%, answered only 80.39% of records. A
rate-limited Qwen run scored 99.10% on the 58.16% of records it answered.
Local Verdict models reached about 50% on the records they did not abstain
on, but fell to 34.87–38.55% over all records, below the 50.26% of a
majority-label reference. The same model on the same records scored 84.48% or
97.36% depending only on its request configuration. Jev held full coverage at
89.87–90.00%. The best local model reached 64.34%. Grok Build stayed at
41.58–43.55% over all records in four runs, collapsing on pairwise decisions.
Accuracy tables for judges should always carry coverage, the unresolved-state
breakdown, and the request configuration.

## 1. Question and problem

> **Research question.** When independent judges, from small local models to
> frontier APIs, receive identical typed decisions with objective gold labels,
> how do their accuracy and coverage differ, and what does accuracy-only
> reporting hide?

Teams pick a model judge from a headline accuracy score. That score is
normally computed over the answers the judge returned. It is silent about
records that were rate-limited, timed out, failed to parse, or were declined,
and it hides the request settings that produced it. This study holds the
records, rubric, label set and gold labels fixed. Every arm faces the same 760
blind decisions, so its correctness and its missing verdicts can be read side
by side.

This is a measurement study of objective, typed decisions. It does not rank
providers by price. It does not claim general legal, financial or open-ended
reasoning ability, and it does not evaluate routing or escalation (Section 7).

## 2. Setup

### 2.1 Records and gold labels

The frozen EXP-015 pool contains 1,408 records: 648 public-selection and 760
source-problem-disjoint blind-holdout records. The pool was built in EXP-013 and
reused byte-for-byte by EXP-014 and EXP-015. Only the blind holdout is analysed
here. Each record has a question, one candidate (`single`: `pass`/`fail`) or two
candidates (`pairwise`: `A`/`B`/`TIE`), a rubric, the legal label set, and a gold
label from a benchmark answer key or deterministic verifier. Model outputs are
never used as gold.

<!-- generated:composition -->
| Source | Single | Pairwise | Total |
|---|---:|---:|---:|
| ARC-Easy (pairwise) | 0 | 100 | 100 |
| Eval Lab synthetic (4 families) | 12 | 8 | 20 |
| EvalLab-Select / ARC-Challenge | 120 | 0 | 120 |
| GSM8K | 200 | 0 | 200 |
| MMLU (8 subjects) | 320 | 0 | 320 |
| **Total** | 652 | 108 | 760 |
<!-- /generated -->

The blind gold labels are nearly balanced: 324 `pass` and 328 `fail` single
records, and 54 `A` and 54 `B` pairwise records (no `TIE` gold labels).

### 2.2 Arms

An arm is one committed run of one judge over all 760 blind records. API arms
receive the provider-neutral typed decision packet (`eval-lab-system-one`
v0.1.0) and must return one legal label. Local arms score the legal labels
natively on the same records. They answer the same questions, **but under a
different harness**, so local-versus-API comparisons are same-record, not
same-harness. The EXP-015 + EXP-016 Qwen arm is the only derived arm. It is a
declared merge, also used in EXP-019, in which the 317 rate-limited EXP-015
records are filled from the separate EXP-016 retry. The majority-label
reference answers `fail` for every single record and `B` for every pairwise
record; it is the frozen EXP-014 baseline.

Not run or excluded: MiMo V2.5 (EXP-024) returned HTTP 402 on both canary
attempts, so no blind predictions exist. Bespoke Nimble-9B and Kev-9B (EXP-027)
do not fit the 16 GiB host in their pinned configurations. Luna (EXP-015) is
excluded under the project's vendor-independent comparison policy (EXP-019). A
missing arm is not a result.

### 2.3 Metrics and tests

- **Resolved:** the arm returned a legal label. Everything else is an explicit
  status: rate limited (HTTP 429), provider error, provider timeout, parse
  failure, abstention, or context-cap skip.
- **Coverage** = resolved / 760.
- **Conditional accuracy** = correct / resolved. This is the number
  accuracy-only tables report.
- **All-record accuracy** = correct / 760. An unresolved record earns no
  credit, as it would in a pipeline that needs a verdict for every item.
- **Intervals:** 95% Wilson score intervals.
- **Paired tests:** exact two-sided McNemar tests on (a) records both arms
  resolved and (b) all 760 records, with unresolved counted as not correct.
  Holm correction is applied over all 325 arm pairs, separately for each view.

Everything in the tables below is generated by
[`scripts/analyze_judge_comparison.py`](https://github.com/Pukujan/Eval-lab/blob/main/scripts/analyze_judge_comparison.py)
from committed prediction files. The run is recorded as
[EXP-029](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260924-029-consolidated-judge-analysis/),
and a test fails if a table here drifts from the script's output.

## 3. Results

### 3.1 Every arm on the same 760 records

<!-- generated:main -->
| Arm | Family | Resolved | Coverage | Conditional accuracy (95% CI) | All-record accuracy (95% CI) | Unresolved |
|---|---|---:|---:|---:|---:|---|
| Qwen3.8 Flash (EXP-024) | API | 760/760 | 100.00% | 99.21% (98.3–99.6) | 99.21% (98.3–99.6) | — |
| Qwen 3.8 Max (EXP-024) | API | 760/760 | 100.00% | 99.08% (98.1–99.6) | 99.08% (98.1–99.6) | — |
| Kimi K2.7 Code (EXP-024) | API | 758/760 | 99.74% | 98.55% (97.4–99.2) | 98.29% (97.1–99.0) | provider error 1, parse failure 1 |
| GLM 5.3 Flash (EXP-024) | API | 756/760 | 99.47% | 97.88% (96.6–98.7) | 97.37% (96.0–98.3) | provider error 2, parse failure 2 |
| Qwen3.8 Flash, EXP-015 + EXP-016 retry (declared merge) | API | 759/760 | 99.87% | 97.50% (96.1–98.4) | 97.37% (96.0–98.3) | provider error 1 |
| Qwen3.8 Flash (EXP-022) | API | 759/760 | 99.87% | 97.36% (96.0–98.3) | 97.24% (95.8–98.2) | parse failure 1 |
| MiniMax M3 (EXP-024) | API | 744/760 | 97.89% | 97.98% (96.7–98.8) | 95.92% (94.3–97.1) | parse failure 16 |
| GLM 5.2 (EXP-024) | API | 727/760 | 95.66% | 99.17% (98.2–99.6) | 94.87% (93.1–96.2) | parse failure 33 |
| Jev 1.13 (EXP-014) | API | 760/760 | 100.00% | 90.00% (87.7–91.9) | 90.00% (87.7–91.9) | — |
| Jev 1.13 (EXP-022) | API | 760/760 | 100.00% | 89.87% (87.5–91.8) | 89.87% (87.5–91.8) | — |
| Qwen3.8 Flash, thinking off (EXP-013/014) | API | 754/760 | 99.21% | 84.48% (81.7–86.9) | 83.82% (81.0–86.3) | parse failure 6 |
| DeepSeek V4.1 Flash (EXP-024) | API | 621/760 | 81.71% | 98.71% (97.5–99.3) | 80.66% (77.7–83.3) | parse failure 139 |
| DeepSeek V4 Flash (EXP-024) | API | 611/760 | 80.39% | 99.84% (99.1–100.0) | 80.26% (77.3–82.9) | parse failure 149 |
| Kev-4B (EXP-027) | local | 760/760 | 100.00% | 64.34% (60.9–67.7) | 64.34% (60.9–67.7) | — |
| Qwen3.8 Flash, one pass (EXP-015) | API | 442/760 | 58.16% | 99.10% (97.7–99.6) | 57.63% (54.1–61.1) | rate limited (429) 317, provider error 1 |
| SemIf (Qwen3.5-4B) (EXP-027) | local | 760/760 | 100.00% | 54.74% (51.2–58.2) | 54.74% (51.2–58.2) | — |
| Kev-0.8B (EXP-027) | local | 760/760 | 100.00% | 50.26% (46.7–53.8) | 50.26% (46.7–53.8) | — |
| Laya 421M (EXP-027) | local | 748/760 | 98.42% | 48.53% (45.0–52.1) | 47.76% (44.2–51.3) | context-cap skip 12 |
| Qwen3-4B local forced choice (EXP-017) | local | 760/760 | 100.00% | 44.61% (41.1–48.2) | 44.61% (41.1–48.2) | — |
| Grok 4.6 Build (EXP-015) | API | 756/760 | 99.47% | 43.78% (40.3–47.3) | 43.55% (40.1–47.1) | provider error 2, provider timeout 2 |
| Grok 4.6 Build (EXP-022) | API | 757/760 | 99.61% | 43.46% (40.0–47.0) | 43.29% (39.8–46.8) | rate limited (429) 2, provider error 1 |
| Grok 4.6 Build, typed rerun (EXP-025) | API | 757/760 | 99.61% | 43.06% (39.6–46.6) | 42.89% (39.4–46.4) | provider error 1, provider timeout 2 |
| Grok 4.7 Build (EXP-022) | API | 726/760 | 95.53% | 43.53% (40.0–47.2) | 41.58% (38.1–45.1) | rate limited (429) 1, provider error 33 |
| Verdict 1.4 (EXP-027) | local | 569/760 | 74.87% | 51.49% (47.4–55.6) | 38.55% (35.2–42.1) | abstention 179, context-cap skip 12 |
| Verdict pre-v1.4 (EXP-027) | local | 526/760 | 69.21% | 50.38% (46.1–54.6) | 34.87% (31.6–38.3) | abstention 234 |
| Majority label (EXP-014 reference) | reference | 760/760 | 100.00% | 50.26% (46.7–53.8) | 50.26% (46.7–53.8) | — |
<!-- /generated -->

![Conditional accuracy against coverage for every arm](figures/benchmark/blind_accuracy_vs_coverage.png)

*Figure 1. Each point is one arm on the same 760 blind records. Dotted curves
mark constant all-record accuracy: an arm far to the left can have high
conditional accuracy and still answer few records correctly.*

Roughly five tiers are visible:

1. **About 99% at full coverage:** Qwen3.8 Flash and Qwen 3.8 Max (EXP-024).
2. **About 97–99% with some missing verdicts:** Kimi K2.7 Code, GLM 5.3 Flash,
   MiniMax M3, GLM 5.2, and the YOLO-Auto Qwen Flash runs with provider-default
   settings.
3. **About 90% at full coverage:** Jev.
4. **44.61–64.34% conditional:** local models.
5. **About 43%:** Grok Build, significantly below the majority reference
   (Table 3).

The majority-label reference sits at 50.26%. Kev-0.8B lands exactly on it.
Laya 421M, local Qwen3-4B, and every Grok run fall below it.

### 3.2 What accuracy-only reporting hides

![Conditional versus all-record accuracy](figures/benchmark/blind_conditional_vs_all_record.png)

*Figure 2. Hollow markers show conditional accuracy and filled markers show
all-record accuracy. The gap is the share of records the arm never answered
correctly because it never answered them.*

Ranking arms by conditional accuracy and by all-record accuracy gives
different orders:

<!-- generated:ranks -->
| Arm | Rank by conditional accuracy | Rank by all-record accuracy | Shift |
|---|---:|---:|---:|
| DeepSeek V4 Flash (EXP-024) | 1 | 13 | -12 |
| Qwen3.8 Flash (EXP-024) | 2 | 1 | +1 |
| GLM 5.2 (EXP-024) | 3 | 8 | -5 |
| Qwen3.8 Flash, one pass (EXP-015) | 4 | 15 | -11 |
| Qwen 3.8 Max (EXP-024) | 5 | 2 | +3 |
| DeepSeek V4.1 Flash (EXP-024) | 6 | 12 | -6 |
| Kimi K2.7 Code (EXP-024) | 7 | 3 | +4 |
| MiniMax M3 (EXP-024) | 8 | 7 | +1 |
| GLM 5.3 Flash (EXP-024) | 9 | 4 | +5 |
| Qwen3.8 Flash, EXP-015 + EXP-016 retry (declared merge) | 10 | 5 | +5 |
| Qwen3.8 Flash (EXP-022) | 11 | 6 | +5 |
| Jev 1.13 (EXP-014) | 12 | 9 | +3 |
| Jev 1.13 (EXP-022) | 13 | 10 | +3 |
| Qwen3.8 Flash, thinking off (EXP-013/014) | 14 | 11 | +3 |
| Kev-4B (EXP-027) | 15 | 14 | +1 |
| Verdict 1.4 (EXP-027) | 17 | 24 | -7 |
| Verdict pre-v1.4 (EXP-027) | 18 | 25 | -7 |
| Kev-0.8B (EXP-027) | 19 | 17 | +2 |
| Laya 421M (EXP-027) | 20 | 18 | +2 |
| Qwen3-4B local forced choice (EXP-017) | 21 | 19 | +2 |
| Grok 4.6 Build (EXP-015) | 22 | 20 | +2 |
| Grok 4.6 Build (EXP-022) | 24 | 21 | +3 |
| Grok 4.6 Build, typed rerun (EXP-025) | 25 | 22 | +3 |
<!-- /generated -->

Three kinds of missing verdict produce the largest shifts:

- **Parse failures.** DeepSeek V4 Flash has the highest conditional accuracy
  in the study but 149 parse failures. It drops from first to thirteenth.
  DeepSeek V4.1 Flash (139 parse failures) and GLM 5.2 (33) move the same way.
  On the records both answered, DeepSeek V4 Flash and Qwen3.8 Flash cannot be
  distinguished. Over all 760 records the difference is decisive (Table 3).
- **Rate limits.** The one-pass EXP-015 Qwen run scored 99.10% on what it
  answered, but 317 rate-limited records leave it at 57.63% overall. The
  separate EXP-016 retry recovers those records. Reporting the one-pass
  number alone would describe a judge that answered barely more than half the
  pool.
- **Abstentions.** Verdict 1.4 and its pre-v1.4 configuration abstain on 179
  and 234 records. They are close to 50% on what they answer. On shared
  records Verdict 1.4 cannot be distinguished from the majority reference.
  Over all records it is significantly worse (Table 3).

Provider errors and timeouts are small for most API arms. The exception is
Grok 4.7, with 33 process-exit errors.

### 3.3 Paired comparisons

<!-- generated:pairs -->
| Comparison (A vs B) | Shared resolved | A-only / B-only correct | Holm p (shared) | A-only / B-only correct, all 760 | Holm p (all 760) |
|---|---:|---:|---:|---:|---:|
| Qwen3.8 Flash (EXP-024) vs Qwen 3.8 Max (EXP-024) | 760 | 4 / 3 | 1.0000 | 4 / 3 | 1.0000 |
| Qwen3.8 Flash (EXP-024) vs DeepSeek V4 Flash (EXP-024) | 611 | 0 / 1 | 1.0000 | 145 / 1 | <0.0001 |
| Qwen3.8 Flash (EXP-024) vs GLM 5.2 (EXP-024) | 727 | 3 / 2 | 1.0000 | 35 / 2 | <0.0001 |
| Qwen3.8 Flash (EXP-022) vs Jev 1.13 (EXP-022) | 759 | 67 / 10 | <0.0001 | 67 / 11 | <0.0001 |
| Qwen3.8 Flash (EXP-022) vs Qwen3.8 Flash (EXP-024) | 759 | 1 / 15 | 0.0545 | 1 / 16 | 0.0195 |
| Qwen3.8 Flash, thinking off (EXP-013/014) vs Qwen3.8 Flash (EXP-022) | 753 | 7 / 103 | <0.0001 | 7 / 109 | <0.0001 |
| Jev 1.13 (EXP-014) vs Jev 1.13 (EXP-022) | 760 | 4 / 3 | 1.0000 | 4 / 3 | 1.0000 |
| Jev 1.13 (EXP-022) vs Kev-4B (EXP-027) | 760 | 222 / 28 | <0.0001 | 222 / 28 | <0.0001 |
| Grok 4.6 Build (EXP-022) vs Grok 4.7 Build (EXP-022) | 723 | 14 / 15 | 1.0000 | 30 / 17 | 1.0000 |
| Grok 4.6 Build (EXP-022) vs Grok 4.6 Build, typed rerun (EXP-025) | 754 | 14 / 11 | 1.0000 | 16 / 13 | 1.0000 |
| Kev-4B (EXP-027) vs SemIf (Qwen3.5-4B) (EXP-027) | 760 | 108 / 35 | <0.0001 | 108 / 35 | <0.0001 |
| Kev-4B (EXP-027) vs Majority label (EXP-014 reference) | 760 | 370 / 263 | 0.0027 | 370 / 263 | 0.0019 |
| SemIf (Qwen3.5-4B) (EXP-027) vs Majority label (EXP-014 reference) | 760 | 319 / 285 | 1.0000 | 319 / 285 | 1.0000 |
| Grok 4.6 Build (EXP-022) vs Majority label (EXP-014 reference) | 757 | 11 / 62 | <0.0001 | 11 / 64 | <0.0001 |
| Verdict 1.4 (EXP-027) vs Majority label (EXP-014 reference) | 569 | 218 / 212 | 1.0000 | 218 / 307 | 0.0089 |
<!-- /generated -->

*Table 3. "A-only / B-only correct" counts the records where exactly one arm is
correct; these discordant counts drive McNemar's test.*

- The two full-coverage leaders (Qwen3.8 Flash and Qwen 3.8 Max) disagree on
  only seven records and are statistically indistinguishable.
- The two Jev runs (EXP-014 and EXP-022) also agree closely, which suggests
  Jev's result is stable across runs.
- Qwen Flash beats Jev in the matched EXP-022 wave.
- Jev beats the best local model, Kev-4B, by a wide margin.
- Kev-4B beats both SemIf and the majority reference. SemIf does not beat
  the reference.
- Grok 4.6 and Grok 4.7 do not differ from each other, and neither does the
  Grok 4.6 typed rerun from EXP-022.

### 3.4 Same model, same records, different request

The same YOLO-Auto `qwen3.8-flash` model scored 84.48% in EXP-013 and 97.36%
in EXP-022 on identical records. The difference is significant (Table 3). The
records are byte-identical, and the model ID, typed specification and wire
protocol are the same. The committed runner code differs:

- **EXP-013** reused `run_qwen_streaming_retry._prompt`, which sets
  `max_tokens=128` and `chat_template_kwargs={"enable_thinking": false}`.
  EXP-014's Qwen comparison arm is the same prediction file, not a separate
  run.
- **EXP-015, EXP-016 and EXP-022** used `run_grok_luna_qwen_bakeoff._qwen_payload`.
  It sends the same system message and typed payload at temperature 0 but sets
  neither a token limit nor a thinking flag, leaving both at the provider
  default. Git history shows neither field was ever present in that runner.
- **EXP-024** reached the model through InferHub (`ali/qwen3.8-flash`) with a
  different, user-only prompt (`run_inferhub_arm.build_prompt`) and
  `max_tokens=1024`.

<!-- generated:qwen -->
| Run | Request configuration | Median latency (resolved) | Coverage | Conditional accuracy | GSM8K accuracy |
|---|---|---:|---:|---:|---:|
| Qwen3.8 Flash, thinking off (EXP-013/014) | run_qwen_streaming_retry._prompt: max_tokens=128, enable_thinking=False | 0.47 s | 99.21% | 84.48% | 65.5% (131/200) |
| Qwen3.8 Flash, one pass (EXP-015) | run_grok_luna_qwen_bakeoff._qwen_payload: no max_tokens, no thinking flag | 4.22 s | 58.16% | 99.10% | 98.5% (196/199) |
| Qwen3.8 Flash, EXP-015 + EXP-016 retry (declared merge) | as EXP-015; rate-limited records filled from the EXP-016 retry | 4.16 s | 99.87% | 97.50% | 98.5% (196/199) |
| Qwen3.8 Flash (EXP-022) | run_grok_luna_qwen_bakeoff._qwen_payload: no max_tokens, no thinking flag | 4.34 s | 99.87% | 97.36% | 99.5% (199/200) |
| Qwen3.8 Flash (EXP-024) | run_inferhub_arm.build_prompt: user-only prompt, max_tokens=1024 | 5.52 s | 100.00% | 99.21% | 99.0% (198/200) |
<!-- /generated -->

The gap sits almost entirely in reasoning-heavy sources. On GSM8K arithmetic
the configured-off run accepted many wrong solutions. The median resolved
latency rose roughly ninefold under the default configuration. The EXP-024
InferHub route reports a median of 165 completion tokens per resolved record,
for a JSON label of a few characters.

The artifacts are consistent with the provider performing hidden reasoning
under default settings and not when it was explicitly disabled. The YOLO-Auto
runs did not record token usage, so this mechanism is inferred from the
request configuration and latency, not observed directly.

What the artifacts do establish is that request configuration alone moved the
same model by about 13 points on the same records. A reported judge score
without its request configuration is not reproducible.

### 3.5 Per-source breakdown of the same pool

EXP-013 has previously been described as a broader multidomain collection. It
is not. It is the same 760-record blind pool, broken down by source. The
breakdown below applies that view to six representative arms.

<!-- generated:sources -->
| Source (blind records) | Qwen3.8 Flash, thinking off (EXP-013/014) | Qwen3.8 Flash (EXP-022) | Qwen3.8 Flash (EXP-024) | Jev 1.13 (EXP-022) | Grok 4.6 Build (EXP-022) | Kev-4B (EXP-027) |
|---|---:|---:|---:|---:|---:|---:|
| ARC-Easy (pairwise) (100) | 97.0% (97/100) | 100.0% (100/100) | 100.0% (100/100) | 100.0% (100/100) | 1.0% (1/100) | 96.0% (96/100) |
| Eval Lab synthetic (4 families) (20) | 52.6% (10/19) | 70.0% (14/20) | 95.0% (19/20) | 70.0% (14/20) | 40.0% (8/20) | 60.0% (12/20) |
| EvalLab-Select / ARC-Challenge (120) | 99.2% (119/120) | 99.2% (119/120) | 100.0% (120/120) | 99.2% (119/120) | 51.7% (62/120) | 84.2% (101/120) |
| GSM8K (200) | 65.5% (131/200) | 99.5% (199/200) | 99.0% (198/200) | 71.5% (143/200) | 50.0% (100/200) | 50.0% (100/200) |
| MMLU (8 subjects) (320) | 88.9% (280/315) | 96.2% (307/319) | 99.1% (317/320) | 95.9% (307/320) | 49.8% (158/317) | 56.2% (180/320) |
<!-- /generated -->

Averages over the pool mask large source effects:

- GSM8K separates arms most. Jev reaches 71.5% there against 99.5% for Qwen
  Flash in the same wave.
- Every Grok run fails the pairwise ARC-Easy items.
- The 20-record synthetic families are too small to support per-source claims.

### 3.6 The low end: local models

The six EXP-027 local decision models and the EXP-017 local Qwen3-4B scorer
answered the same 760 records on a single laptop-class host. They score legal
labels natively, a different harness from the API arms. They used context caps
from 512 to 4,096 tokens; over-cap records are skipped statuses.

Kev-4B is the strongest local arm at 64.34%. It is the only one clearly above
the majority reference, and most of its advantage comes from pairwise records
(Table 4). SemIf is not distinguishable from the reference (Table 3). The rest
cluster around or below 50%, and the Verdict models lose a quarter to a third
of the pool to abstention. None is a substitute for the API judges
on this pool.

<!-- generated:modes -->
| Arm | Single pass/fail accuracy | Pairwise A/B/TIE accuracy |
|---|---:|---:|
| Qwen3.8 Flash (EXP-024) | 99.08% (646/652) | 100.00% (108/108) |
| Qwen 3.8 Max (EXP-024) | 98.93% (645/652) | 100.00% (108/108) |
| Kimi K2.7 Code (EXP-024) | 98.46% (640/650) | 99.07% (107/108) |
| GLM 5.3 Flash (EXP-024) | 97.53% (632/648) | 100.00% (108/108) |
| Qwen3.8 Flash, EXP-015 + EXP-016 retry (declared merge) | 97.70% (636/651) | 96.30% (104/108) |
| Qwen3.8 Flash (EXP-022) | 97.54% (635/651) | 96.30% (104/108) |
| MiniMax M3 (EXP-024) | 97.80% (622/636) | 99.07% (107/108) |
| GLM 5.2 (EXP-024) | 99.36% (617/621) | 98.11% (104/106) |
| Jev 1.13 (EXP-014) | 88.96% (580/652) | 96.30% (104/108) |
| Jev 1.13 (EXP-022) | 88.80% (579/652) | 96.30% (104/108) |
| Qwen3.8 Flash, thinking off (EXP-013/014) | 83.13% (537/646) | 92.59% (100/108) |
| DeepSeek V4.1 Flash (EXP-024) | 98.49% (522/530) | 100.00% (91/91) |
| DeepSeek V4 Flash (EXP-024) | 99.80% (509/510) | 100.00% (101/101) |
| Kev-4B (EXP-027) | 59.51% (388/652) | 93.52% (101/108) |
| Qwen3.8 Flash, one pass (EXP-015) | 98.83% (338/342) | 100.00% (100/100) |
| SemIf (Qwen3.5-4B) (EXP-027) | 53.83% (351/652) | 60.19% (65/108) |
| Kev-0.8B (EXP-027) | 53.37% (348/652) | 31.48% (34/108) |
| Laya 421M (EXP-027) | 48.59% (311/640) | 48.15% (52/108) |
| Qwen3-4B local forced choice (EXP-017) | 49.85% (325/652) | 12.96% (14/108) |
| Grok 4.6 Build (EXP-015) | 50.39% (327/649) | 3.74% (4/107) |
| Grok 4.6 Build (EXP-022) | 50.54% (328/649) | 0.93% (1/108) |
| Grok 4.6 Build, typed rerun (EXP-025) | 49.85% (324/650) | 1.87% (2/107) |
| Grok 4.7 Build (EXP-022) | 50.97% (315/618) | 0.93% (1/108) |
| Verdict 1.4 (EXP-027) | 51.55% (249/483) | 51.16% (44/86) |
| Verdict pre-v1.4 (EXP-027) | 51.06% (217/425) | 47.52% (48/101) |
<!-- /generated -->

*Table 4. Accuracy by decision mode (resolved records).*

## 4. Robustness and failure analysis: Grok Build

Grok Build is the one API judge that answers nearly every record yet performs
at or below the majority reference. Four blind runs across three experiments
(EXP-015, EXP-022 for 4.6 and 4.7, EXP-025) give the same picture:

- about 50% on single records;
- 0.93–3.74% on pairwise records (Table 4);
- about 43% overall.

The Build CLI surfaced `grok-4.6-build` and `grok-4.7-build`. Requested and
surfaced model IDs are kept separate in the artifacts.

EXP-025 preregistered a test of whether the typed contract caused the failure.
It compared four variants on a 64-record public diagnostic: the original typed
schema, explicit task wording with schema, semantic labels with schema, and
explicit wording with no native schema. To replace the baseline, a variant had
to keep at least 95% public coverage and improve the mode-balanced score by at
least 0.10.

No variant passed:

| Variant | Public resolved | Mode-balanced score |
|---|---:|---:|
| typed schema (baseline) | 64/64 | 0.2656 |
| explicit schema | 63/64 | 0.2581 |
| semantic schema | 63/64 | 0.2661 |
| explicit, no schema | 0/64 | n/a (57 parse failures, 6 provider errors, 1 rate limit) |

The ablation found and fixed a real harness defect: a Windows locale-decoding
error in the shared stream reader. It did not find a better contract. The
typed baseline's blind rerun reproduced the earlier result, and paired tests
find no difference between runs (Table 3).

The honest conclusion is narrow. Grok Build underperforms sharply under this
typed-judge harness family. The experiments cannot separate model behaviour
from harness effects, and this is not a general capability estimate.

![Grok protocol ablation](figures/benchmark/grok_protocol_ablation.png)

*Figure 3. EXP-025 public diagnostic and blind typed-baseline rerun.*

Source: [EXP-025](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260922-025-grok-protocol-ablation/).

## 5. Discussion: how judge results should be reported

On objective typed decisions, the same records separate judges clearly, from
about 99% down to below the majority reference. But the order depends on what
is counted. Three reporting rules follow directly from the results:

1. **Report coverage and the unresolved breakdown next to accuracy.** In this
   study the highest conditional accuracy belonged to an arm that answered
   80.39% of records. Abstention turned roughly 50% conditional accuracy into
   an all-record score below a constant-label baseline.
2. **Report all-record accuracy, or state the fallback.** Whether an unanswered
   record is retried, routed elsewhere, or counted as a miss is part of the
   judge's operational definition.
3. **Report the request configuration.** Token limits, thinking flags, prompt
   framing and route moved one model by about 13 points on identical records.

## 6. Limitations

- **One pool.** It is objective and typed, and dominated by MMLU (320) and
  GSM8K (200). There are only 108 pairwise records and no `TIE` gold labels.
  Results do not transfer to open-ended, subjective, legal-opinion or
  expert-adjudicated tasks.
- **Runs, not models.** Arms are single runs from different dates, harnesses
  and routes. Apart from Jev (two runs), Grok 4.6 (three) and Qwen Flash
  (four configurations), there is no run-to-run replication. Provider
  behaviour can change between dates.
- **Local arms** use a different harness and different context caps from the
  API arms. Nimble-9B and Kev-9B were not run.
- **Qwen explanation.** The Section 3.4 explanation rests on committed request
  configuration and latency. Token usage was not recorded for the YOLO-Auto
  runs, so hidden reasoning is inferred, not observed. EXP-024 also changed
  the prompt and route, so its gain cannot be attributed to one factor.
- **Parse failures** in EXP-024 are recorded as `label_not_found`, but the raw
  response text was not retained. Whether the cause is the model, output
  length, or the parser cannot be determined from the artifacts.
- **Multiple testing.** Holm correction over 325 pairs is conservative. Paired
  tests on shared records exclude each arm's unresolved records by
  construction.
- **Exclusions.** Luna is excluded by project policy, so the study cannot
  speak to that model.
- **Confidence.** Calibration is outside the research question. Only local
  scorers expose probabilities; see Appendix A.

## 7. Future work (moved out of this paper)

These directions appeared in earlier drafts. They are kept out of this paper
because they answer different questions or lack completed evidence. Earlier
drafts are preserved in [`paper/archive/`](https://github.com/Pukujan/Eval-lab/tree/main/paper/archive/).

- **Selective escalation and routing** (EXP-009 to EXP-012). In the completed
  replay, every calibrated routing policy collapsed to nearly zero local
  coverage and was marked descriptive. There is no positive evidence yet.
- **Domain pilots:**
  - LegalBench Hearsay (EXP-028) is a small, separate task.
  - GLEIF (EXP-026) is preregistered but not run.
  - SEC EDGAR/XBRL and CourtListener tracks and HumanEval (EXP-020) are
    planning-only.
- **Provider selection and price** (EXP-023/024 InferHub recommendation
  policy). This is an operational question, not the scientific subject.
- **Training a small judge:** TF-IDF student (EXP-008), teacher-assisted hard
  negatives (EXP-004/007).
- **Confidence calibration** for probability-bearing local arms (EXP-027
  native probabilities) and a confidence interface for API judges.

## Appendix A. Calibration (outside the research question)

No API arm exposed a validated probability map, so API judges are not called
calibrated here. For the local Qwen3-4B scorer (EXP-017/019), scalar
temperature scaling was fit on public-selection records only, separately for
single (T = 6.864867) and pairwise (T = 403.428793) records. It was then
applied once to the blind holdout.

Labels and accuracy (44.61%) were unchanged. Blind Brier score fell from 0.7037
to 0.5160, NLL from 1.0767 to 0.7430, and ECE from 0.3411 to 0.0783. The judge's
confidence became more honest while its decisions stayed weak. Calibration is a
separate property from accuracy.

![Local Qwen3-4B calibration](figures/benchmark/local_qwen_calibration.png)

Source: [EXP-019](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260921-019-calibrated-judge-study/).

## Appendix B. Reproducibility

Regenerate the analysis, the paper tables and the figures offline, with no
provider credentials:

```powershell
uv sync --locked --extra dev --extra figures
uv run --locked python scripts/analyze_judge_comparison.py --update-paper
uv run --locked python scripts/generate_benchmark_figures.py
uv run --locked python -m pytest tests/test_judge_comparison_analysis.py
```

Every source prediction file is listed with an LF-normalized SHA-256 in
[EXP-029 `results.json`](https://github.com/Pukujan/Eval-lab/blob/main/experiments/EXP-20260924-029-consolidated-judge-analysis/results.json).

Experiment bundles:

- [EXP-013 Qwen Flash, thinking off](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260921-013-qwen-multidomain-holdout/)
- [EXP-014 independent Jev](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260921-014-independent-jev-benchmark/)
- [EXP-015 Grok/Qwen bakeoff](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/)
- [EXP-016 Qwen rate-limit retry](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260921-016-qwen-rate-limit-retry/)
- [EXP-017 local Qwen3-4B](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260921-017-judge-calibration/)
- [EXP-019 calibration study](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260921-019-calibrated-judge-study/)
- [EXP-022 direct wave](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260922-022-fast-provider-wave/)
- [EXP-024 InferHub wave](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260922-024-inferhub-recommendation-wave/)
- [EXP-025 Grok protocol ablation](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260922-025-grok-protocol-ablation/)
- [EXP-027 local decision models](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260924-027-local-decision-bakeoff/)
- [EXP-029 consolidated analysis](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260924-029-consolidated-judge-analysis/)
