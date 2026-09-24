# Accuracy is not enough: correctness and coverage of independent judges on identical objective decisions

> [!IMPORTANT]
> **At a glance**
>
> - **The problem:** AI "judges" are usually compared by one accuracy score, which ignores the questions a judge never answered.
> - **What we did:** we gave 25 judges, from small laptop models to frontier APIs, the same 760 questions with known right answers, and counted both what they got right and what they skipped.
> - **Finding 1:** the best judges got about 99% of all questions right, and the top two are statistically tied.
> - **Finding 2:** a high accuracy score can hide a judge that skipped up to four in ten questions.
> - **Finding 3:** the same model scored 84.5% or 97.4% on the same questions, depending only on its request settings.
> - **Finding 4:** most small local models, and Grok Build, did no better than always giving the same answer.

**Status:** working paper; pending owner review<br />
**Evidence:** EXP-013 to EXP-027 prediction files, consolidated by the offline analysis EXP-029<br />
**Repository:** [Eval Lab](https://github.com/Pukujan/Eval-lab/tree/main)

## 1. The problem

Teams increasingly use one AI model to grade another model's work. They pick
that "judge" by looking at a single accuracy number.

That number is usually computed only over the questions the judge answered. A
judge can hit a rate limit, return text nobody can parse, or decline to answer,
and none of that shows up in its accuracy.

> **Research question.** When independent judges, from small local models to
> frontier APIs, receive identical typed decisions with objective gold labels,
> how do their accuracy and coverage differ, and what does accuracy-only
> reporting hide?

This is a measurement study of objective decisions. It does not rank
providers in general, and it does not cover open-ended or subjective grading.

## 2. Setup

**The questions.** Every judge saw the same 760 held-back questions, called
the blind set. Most ask whether a proposed answer is correct (`pass` or
`fail`). The rest show two answers and ask which is better (`A` or `B`). The
right answer always comes from an answer key or an automatic checker, never
from a model.

<!-- generated:body_sources -->
| Source | Questions | What it tests |
|---|---:|---|
| MMLU (8 subjects) | 320 | school and professional knowledge |
| GSM8K | 200 | grade-school math word problems |
| ARC-Challenge | 120 | harder science questions |
| ARC-Easy | 100 | pick the better of two answers |
| Eval Lab synthetic | 20 | small hand-built checks |
<!-- /generated -->

**The judges.** A "judge" here means one recorded run of one model over all
760 questions. API judges got an identical, strictly formatted request and had
to reply with one allowed label. Local models ran on the author's own hardware
and scored the allowed labels directly. That is a different harness, so
local-versus-API comparisons use the same questions but not the same method.

**What we measured.**

- **Coverage** is the share of the 760 questions a judge answered with an
  allowed label.
- **Accuracy when it answered** is correct answers divided by answered
  questions. This is the number most leaderboards report.
- **Accuracy over all 760** counts a skipped question as wrong, as it would be
  in a pipeline that needs a verdict for every item.
- A **Wilson interval** is the range the true accuracy plausibly falls in
  (95% confidence) given the sample size.
- A **McNemar test** compares two judges on the same questions by looking only
  at questions where exactly one of them was right.

Every table and chart comes from committed scripts
([`analyze_judge_comparison.py`](https://github.com/Pukujan/Eval-lab/blob/main/scripts/analyze_judge_comparison.py),
[`generate_benchmark_figures.py`](https://github.com/Pukujan/Eval-lab/blob/main/scripts/generate_benchmark_figures.py)),
and a test fails if the paper drifts from their output.

## 3. What happened

Most API judges ran cleanly, but several runs lost questions along the way,
and one discovery changed how we read the results.

**Runs lost questions in different ways.** One Qwen run hit the provider's
rate limit on 317 questions; a separate retry recovered them. DeepSeek V4
Flash and V4.1 Flash returned answers our parser could not read on 149 and 139
questions. Two local Verdict models declined to answer a quarter to a third of
the time. MiMo V2.5 was refused with a payment error (HTTP 402) before it
answered anything, and two 9-billion-parameter local models did not fit in the
16 GB test machine. We report all of these as results, not as footnotes.

**Grok Build failed, and fixing the format did not help.** Grok Build
answered nearly every question but was right only about four times in ten. It
almost always chose the wrong answer on "which is better" questions. A
preregistered follow-up (EXP-025) tried four different request formats. It
found and fixed a real bug in our text decoding on Windows, but no format
improved the score (Appendix D).

**The same model gave two very different scores.** Qwen3.8 Flash scored 84.5%
in its first run and 97.4% in a later run on the exact same questions. The
question files are byte-identical, and the model name and request format match.
What differed was a setting in the script that sent the requests.

<!-- generated:body_qwen -->
| Qwen3.8 Flash run | Request settings | Typical answer time | Correct when it answered | Math (GSM8K) |
|---|---|---:|---:|---:|
| EXP-013 | 128-token cap, thinking off | 0.5 s | 84.5% | 65.5% |
| EXP-022 | provider defaults | 4.3 s | 97.4% | 99.5% |
| EXP-024 | other route and prompt, 1,024-token cap | 5.5 s | 99.2% | 99.0% |
<!-- /generated -->

The first run capped each reply at 128 tokens and switched the model's
"thinking" off. The later runs left both at the provider default. With the
defaults, answers took about nine times longer, and math accuracy jumped from
65.5% to 99.5%. That suggests the model reasons silently before answering when
allowed to. We could not confirm this directly because those runs did not
record token counts.

## 4. What we found

### Finding 1: The best judges got about 99% right, and the top two are tied

Qwen3.8 Flash and Qwen 3.8 Max answered every question and got 99.2% and
99.1% right. On only seven questions was one right and the other wrong, so
the difference is not meaningful. Kimi K2.7 Code, GLM 5.3 Flash and MiniMax M3
came close behind. Kimi K2.7 Code and GLM 5.3 Flash cannot be separated from
Qwen3.8 Flash either, so four judges share first place in the full ranking
(Figure A1). Jev also answered everything but got 89.9% right, a clear
step down.

<figure data-figure="finding_accuracy_range">
  <picture>
    <source media="(prefers-color-scheme: dark) and (max-width: 700px)" srcset="figures/benchmark/finding_accuracy_range.dark.tall.svg" />
    <source media="(max-width: 700px)" srcset="figures/benchmark/finding_accuracy_range.light.tall.svg" />
    <source media="(prefers-color-scheme: dark)" srcset="figures/benchmark/finding_accuracy_range.dark.wide.svg" />
    <img src="figures/benchmark/finding_accuracy_range.light.wide.svg" alt="Bar chart of accuracy over all 760 questions for selected judges" />
  </picture>
  <figcaption>Figure 1. Share of all 760 questions each judge got right; skipped questions count as wrong. The dashed line is the always-same-answer baseline.</figcaption>
</figure>

<!-- generated:body_leaders -->
| Judge | Type | Answered | Correct, all 760 questions |
|---|---|---:|---:|
| Qwen3.8 Flash | API | 100.0% | 99.2% |
| Qwen 3.8 Max | API | 100.0% | 99.1% |
| Kimi K2.7 Code | API | 99.7% | 98.3% |
| Jev 1.13 | API | 100.0% | 89.9% |
| Kev-4B (best local model) | local | 100.0% | 64.3% |
| Always-same-answer baseline | reference | 100.0% | 50.3% |
| Grok 4.6 Build | API | 99.6% | 43.3% |
<!-- /generated -->

### Finding 2: A high accuracy score can hide a judge that skips questions

DeepSeek V4 Flash had the highest accuracy of any judge on the questions it
answered, 99.8%. But it answered only 80.4% of them, so it got 80.3% of the
full set right. It falls from first place to thirteenth once skipped
questions count.

The same pattern appears with rate limits and abstentions. A rate-limited
Qwen run looked excellent on paper while answering barely more than half the
questions. The Verdict models answered about half correctly, but once their
abstentions count they fall below the always-same-answer baseline.

<figure data-figure="finding_skipped_questions">
  <picture>
    <source media="(prefers-color-scheme: dark) and (max-width: 700px)" srcset="figures/benchmark/finding_skipped_questions.dark.tall.svg" />
    <source media="(max-width: 700px)" srcset="figures/benchmark/finding_skipped_questions.light.tall.svg" />
    <source media="(prefers-color-scheme: dark)" srcset="figures/benchmark/finding_skipped_questions.dark.wide.svg" />
    <img src="figures/benchmark/finding_skipped_questions.light.wide.svg" alt="Dumbbell chart comparing accuracy when answered with accuracy over all questions" />
  </picture>
  <figcaption>Figure 2. Hollow dot: accuracy on answered questions. Filled dot: accuracy over all 760. The gap is what an accuracy-only table hides.</figcaption>
</figure>

<!-- generated:body_hidden -->
| Judge | Answered | Correct when it answered | Correct, all 760 | Why questions were lost |
|---|---:|---:|---:|---|
| DeepSeek V4 Flash | 80.4% | 99.8% | 80.3% | 149 unreadable answers |
| GLM 5.2 | 95.7% | 99.2% | 94.9% | 33 unreadable answers |
| Qwen3.8 Flash, one pass | 58.2% | 99.1% | 57.6% | 317 rate-limited |
| Verdict 1.4 (local) | 74.9% | 51.5% | 38.6% | 179 abstained, 12 too long for the model |
| Verdict pre-v1.4 (local) | 69.2% | 50.4% | 34.9% | 234 abstained |
<!-- /generated -->

### Finding 3: Request settings moved one model as much as switching models

The Qwen result in Section 3 is a finding in its own right. Changing only the
request settings moved the same model from 84.5% to 97.4% on identical questions.
That gap is larger than the gap between Qwen and Jev.

<figure data-figure="finding_request_settings">
  <picture>
    <source media="(prefers-color-scheme: dark) and (max-width: 700px)" srcset="figures/benchmark/finding_request_settings.dark.tall.svg" />
    <source media="(max-width: 700px)" srcset="figures/benchmark/finding_request_settings.light.tall.svg" />
    <source media="(prefers-color-scheme: dark)" srcset="figures/benchmark/finding_request_settings.dark.wide.svg" />
    <img src="figures/benchmark/finding_request_settings.light.wide.svg" alt="Bar chart of Qwen3.8 Flash accuracy under different request settings" />
  </picture>
  <figcaption>Figure 3. Qwen3.8 Flash on the same questions under three request settings, overall and on GSM8K math.</figcaption>
</figure>

### Finding 4: Most small local models did no better than always giving the same answer

A judge that always says `fail` (or `B` for two-answer questions) is right
50.3% of the time here. Kev-4B was the only local model clearly above that,
at 64.3%. It was strongest on the two-answer questions (93.5%) and only
modestly above the baseline on the rest (59.5%). SemIf and Kev-0.8B were not
meaningfully different from the baseline, and the rest scored below it.

Grok Build is an API judge, but it landed with this group: its best run got
43.6% right, significantly below the baseline.

<!-- generated:body_local -->
| Model | Answered | Correct, all 760 |
|---|---:|---:|
| Kev-4B (best local model) | 100.0% | 64.3% |
| SemIf 4B | 100.0% | 54.7% |
| Kev-0.8B | 100.0% | 50.3% |
| Laya 421M | 98.4% | 47.8% |
| Qwen3-4B | 100.0% | 44.6% |
| Verdict 1.4 (local) | 74.9% | 38.6% |
| Verdict pre-v1.4 (local) | 69.2% | 34.9% |
| Always-same-answer baseline | 100.0% | 50.3% |
<!-- /generated -->

## 5. What it means

On objective questions with known answers, judges really do differ, from
near-perfect to worse than a constant guess. But the ranking depends on what
you count. Three reporting rules follow:

1. **Always report coverage next to accuracy**, with a breakdown of why
   questions were lost: rate limits, errors, unreadable answers, abstentions.
2. **Report accuracy over all questions**, or state exactly what happens to a
   skipped one (retried, sent to another judge, or counted as a miss).
3. **Report the request settings**: token caps, thinking flags, prompt and
   route. Without them a judge score cannot be reproduced.

## 6. Limitations

- **One question pool.** It is objective and typed, and dominated by MMLU and
  GSM8K. There are only 108 two-answer questions and no ties. Results may not
  carry over to open-ended or subjective grading.
- **Runs, not models.** Each judge is usually a single run on a single date,
  through a specific route. Only Jev (two runs), Grok 4.6 (three) and Qwen
  Flash (four setups) were repeated. Providers can change behaviour over time.
- **Local models used a different harness** and different length limits.
  Two 9B models were not run.
- **The Qwen explanation is inferred.** It rests on the recorded settings and
  answer times; token counts were not recorded. The InferHub run also changed
  the prompt and route, so its gain cannot be pinned on one factor.
- **Unreadable answers** were recorded, but the raw text was not kept, so we
  cannot tell whether the model, its length, or our parser was at fault.
- **Many comparisons.** Correcting for 325 pairwise tests is conservative.
- **Exclusions.** Luna is excluded by project policy.

## 7. Future work

These topics appeared in earlier drafts and are kept out of this paper
because they answer different questions or lack finished evidence. Earlier
drafts are in [`paper/archive/`](https://github.com/Pukujan/Eval-lab/tree/main/paper/archive/).

- **Routing and selective escalation** (EXP-009 to EXP-012): in the completed
  replay, every routing policy kept almost nothing local. No positive evidence
  yet.
- **Domain pilots:** LegalBench Hearsay (EXP-028); GLEIF (EXP-026,
  preregistered, not run); SEC EDGAR/XBRL, CourtListener and HumanEval
  (EXP-020, planning only).
- **Provider selection and price** (EXP-023/024): an operational question.
- **Training a small judge:** TF-IDF student (EXP-008) and teacher-assisted
  hard negatives (EXP-004/007).
- **Confidence calibration** for local models and a confidence interface for
  API judges.

## Appendix A. Every judge, in full

All 25 judges and the reference, ordered by accuracy over all 760 questions.
Intervals are 95% Wilson intervals.

<details>
<summary>Full results table (26 rows)</summary>

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

</details>

<details>
<summary>How rankings change when skipped questions count (rank shifts)</summary>

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

</details>

<details>
<summary>Accuracy by question type (single answer vs pick-the-better)</summary>

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

</details>

<details>
<summary>Accuracy by source for six representative judges</summary>

The earlier EXP-013 report described this breakdown as a broader collection.
It is the same 760-question blind pool, split by source.

<!-- generated:sources -->
| Source (blind records) | Qwen3.8 Flash, thinking off (EXP-013/014) | Qwen3.8 Flash (EXP-022) | Qwen3.8 Flash (EXP-024) | Jev 1.13 (EXP-022) | Grok 4.6 Build (EXP-022) | Kev-4B (EXP-027) |
|---|---:|---:|---:|---:|---:|---:|
| ARC-Easy (pairwise) (100) | 97.0% (97/100) | 100.0% (100/100) | 100.0% (100/100) | 100.0% (100/100) | 1.0% (1/100) | 96.0% (96/100) |
| Eval Lab synthetic (4 families) (20) | 52.6% (10/19) | 70.0% (14/20) | 95.0% (19/20) | 70.0% (14/20) | 40.0% (8/20) | 60.0% (12/20) |
| EvalLab-Select / ARC-Challenge (120) | 99.2% (119/120) | 99.2% (119/120) | 100.0% (120/120) | 99.2% (119/120) | 51.7% (62/120) | 84.2% (101/120) |
| GSM8K (200) | 65.5% (131/200) | 99.5% (199/200) | 99.0% (198/200) | 71.5% (143/200) | 50.0% (100/200) | 50.0% (100/200) |
| MMLU (8 subjects) (320) | 88.9% (280/315) | 96.2% (307/319) | 99.1% (317/320) | 95.9% (307/320) | 49.8% (158/317) | 56.2% (180/320) |
<!-- /generated -->

</details>

<details>
<summary>Question pool composition</summary>

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

</details>

<figure data-figure="judges_ranked">
  <picture>
    <source media="(prefers-color-scheme: dark) and (max-width: 700px)" srcset="figures/benchmark/judges_ranked.dark.tall.svg" />
    <source media="(max-width: 700px)" srcset="figures/benchmark/judges_ranked.light.tall.svg" />
    <source media="(prefers-color-scheme: dark)" srcset="figures/benchmark/judges_ranked.dark.wide.svg" />
    <img src="figures/benchmark/judges_ranked.light.wide.svg" alt="Ranked chart of all 25 judges by accuracy over all 760 questions, with 95% intervals and share answered" />
  </picture>
  <figcaption>Figure A1. Four judges share first place, and eight score below the always-same-answer baseline. Judges share a rank when a Holm-corrected McNemar test over all 760 questions cannot separate them from the top judge of their group; red percentages mark judges that answered fewer than 99% of questions.</figcaption>
</figure>

## Appendix B. Paired tests

Exact two-sided McNemar tests on (a) questions both judges answered and (b)
all 760 questions with skipped counted as wrong. Holm correction is applied
over all 325 pairs, separately for each view. "A-only / B-only correct"
counts questions where exactly one judge was right.

<details>
<summary>Selected paired comparisons (15 rows)</summary>

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

</details>

## Appendix C. Qwen request settings in detail

- **EXP-013** used `run_qwen_streaming_retry._prompt`, which sets
  `max_tokens=128` and `chat_template_kwargs={"enable_thinking": false}`.
  EXP-014's Qwen arm is the same prediction file, not a separate run.
- **EXP-015, EXP-016 and EXP-022** used
  `run_grok_luna_qwen_bakeoff._qwen_payload`: the same system message and
  payload at temperature 0, with no token limit and no thinking flag. Git
  history shows neither field was ever present in that runner.
- **EXP-024** used InferHub (`ali/qwen3.8-flash`) with a user-only prompt
  (`run_inferhub_arm.build_prompt`) and `max_tokens=1024`.

<details>
<summary>All Qwen3.8 Flash runs (5 rows)</summary>

<!-- generated:qwen -->
| Run | Request configuration | Median latency (resolved) | Coverage | Conditional accuracy | GSM8K accuracy |
|---|---|---:|---:|---:|---:|
| Qwen3.8 Flash, thinking off (EXP-013/014) | run_qwen_streaming_retry._prompt: max_tokens=128, enable_thinking=False | 0.47 s | 99.21% | 84.48% | 65.5% (131/200) |
| Qwen3.8 Flash, one pass (EXP-015) | run_grok_luna_qwen_bakeoff._qwen_payload: no max_tokens, no thinking flag | 4.22 s | 58.16% | 99.10% | 98.5% (196/199) |
| Qwen3.8 Flash, EXP-015 + EXP-016 retry (declared merge) | as EXP-015; rate-limited records filled from the EXP-016 retry | 4.16 s | 99.87% | 97.50% | 98.5% (196/199) |
| Qwen3.8 Flash (EXP-022) | run_grok_luna_qwen_bakeoff._qwen_payload: no max_tokens, no thinking flag | 4.34 s | 99.87% | 97.36% | 99.5% (199/200) |
| Qwen3.8 Flash (EXP-024) | run_inferhub_arm.build_prompt: user-only prompt, max_tokens=1024 | 5.52 s | 100.00% | 99.21% | 99.0% (198/200) |
<!-- /generated -->

</details>

## Appendix D. Grok Build protocol ablation

EXP-025 compared four request formats on a 64-question public diagnostic. To
replace the baseline, a format had to keep at least 95% coverage and improve
the mode-balanced score by at least 0.10. None did, and the blind rerun of
the baseline matched the earlier runs (Appendix B).

<!-- generated:grok_ablation -->
| Request format | Public answered | Mode-balanced score |
|---|---:|---:|
| typed schema (baseline) | 64/64 | 0.2656 |
| explicit wording + schema | 63/64 | 0.2581 |
| semantic labels + schema | 63/64 | 0.2661 |
| explicit wording, no schema | 0/64 | n/a (no readable answers) |
<!-- /generated -->

<figure data-figure="grok_protocol_ablation">
  <picture>
    <source media="(prefers-color-scheme: dark) and (max-width: 700px)" srcset="figures/benchmark/grok_protocol_ablation.dark.tall.svg" />
    <source media="(max-width: 700px)" srcset="figures/benchmark/grok_protocol_ablation.light.tall.svg" />
    <source media="(prefers-color-scheme: dark)" srcset="figures/benchmark/grok_protocol_ablation.dark.wide.svg" />
    <img src="figures/benchmark/grok_protocol_ablation.light.wide.svg" alt="Bar chart of Grok Build scores under four request formats" />
  </picture>
  <figcaption>Figure D1. No request format beat the typed baseline on the EXP-025 public diagnostic.</figcaption>
</figure>

Source: [EXP-025](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260922-025-grok-protocol-ablation/).

## Appendix E. Calibration (outside the research question)

No API judge exposed usable probabilities. For the local Qwen3-4B scorer
(EXP-017/019), temperature scaling was fit on public questions only and
applied once to the blind set. Accuracy stayed at 44.61%, while Brier score
fell from 0.7037 to 0.5160, NLL from 1.0767 to 0.7430 and ECE from 0.3411 to
0.0783. Its confidence became more honest while its decisions stayed weak.

<figure data-figure="local_qwen_calibration">
  <picture>
    <source media="(prefers-color-scheme: dark) and (max-width: 700px)" srcset="figures/benchmark/local_qwen_calibration.dark.tall.svg" />
    <source media="(max-width: 700px)" srcset="figures/benchmark/local_qwen_calibration.light.tall.svg" />
    <source media="(prefers-color-scheme: dark)" srcset="figures/benchmark/local_qwen_calibration.dark.wide.svg" />
    <img src="figures/benchmark/local_qwen_calibration.light.wide.svg" alt="Bar charts of calibration error before and after temperature scaling" />
  </picture>
  <figcaption>Figure E1. Calibration made local Qwen3-4B's confidence more honest without changing its answers.</figcaption>
</figure>

Source: [EXP-019](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260921-019-calibrated-judge-study/).

## Appendix F. Reproducibility

Everything regenerates offline, with no provider credentials:

```powershell
uv sync --locked --extra dev --extra figures
uv run --locked python scripts/analyze_judge_comparison.py --update-paper
uv run --locked python scripts/generate_benchmark_figures.py
uv run --locked python -m pytest tests/test_judge_comparison_analysis.py
```

Every source prediction file is listed with an LF-normalized SHA-256 in
[EXP-029 `results.json`](https://github.com/Pukujan/Eval-lab/blob/main/experiments/EXP-20260924-029-consolidated-judge-analysis/results.json).

Chart data for the interactive versions of these figures is exported by
`scripts/export_chart_data.py` to
[`paper/data/`](https://github.com/Pukujan/Eval-lab/tree/main/paper/data/). It has
one row per judge run and no individual questions or answer keys. Each file
records the exporter's commit and the SHA-256 of every input, as W3C PROV-O terms
in JSON-LD. CI checks each file against a JSON Schema and SHACL shapes, and
recomputes every hash. Provenance here means these hashes, commits and tests; see
[`docs/PROVENANCE.md`](https://github.com/Pukujan/Eval-lab/blob/main/docs/PROVENANCE.md).

Experiment bundles:
[EXP-013](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260921-013-qwen-multidomain-holdout/),
[EXP-014](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260921-014-independent-jev-benchmark/),
[EXP-015](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/),
[EXP-016](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260921-016-qwen-rate-limit-retry/),
[EXP-017](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260921-017-judge-calibration/),
[EXP-019](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260921-019-calibrated-judge-study/),
[EXP-022](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260922-022-fast-provider-wave/),
[EXP-024](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260922-024-inferhub-recommendation-wave/),
[EXP-025](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260922-025-grok-protocol-ablation/),
[EXP-027](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260924-027-local-decision-bakeoff/),
[EXP-029](https://github.com/Pukujan/Eval-lab/tree/main/experiments/EXP-20260924-029-consolidated-judge-analysis/).
