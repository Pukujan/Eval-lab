# TASK-0019 — Calibrated judge construction and independent head-to-head study

- Status: active
- Owner: Codex/research execution agent
- Priority: P1
- Branch: task/TASK-0019-calibrated-judge-study
- Depends on: TASK-0015, TASK-0016, and TASK-0017 completed artifacts

## Goal

Complete the research study on how Eval Lab constructs rubric-grounded,
calibrated judges and how independent judge implementations compare on the
same frozen typed benchmark.

The paper is about the calibration method and judge-construction protocol, not
provider reliability. Provider execution states remain in raw artifacts for
auditability, but are not a primary scientific outcome.

## Research questions

1. Does a frozen rubric and typed decision protocol produce comparable,
   auditable judge decisions across independent model routes?
2. Does split-safe post-hoc calibration improve the reliability of a judge's
   confidence without changing its selected labels?
3. How do Grok Build, Jev, YOLO-Auto Qwen Flash, and local Qwen 4B compare
   head-to-head under the same objective gold and rubric packet?
4. Which parts of the Eval Lab pipeline are required to call a judge
   calibrated rather than merely accurate or fluent?

## Included arms

- Grok Build through the direct authenticated xAI `grok` CLI only.
- Jev through the authorized OpenRouter Jev-only route only.
- YOLO-Auto `qwen3.8-flash`.
- Local `Qwen/Qwen3-4B` using the completed 4-bit forced-choice runtime.

Luna and Sol are excluded from this study because the orchestrator requires a
vendor-independent comparison. Their completed artifacts remain immutable
historical evidence and are not used in the primary tables, pairwise analyses,
calibration, adjudication, or paper conclusions.

No OpenCode route is permitted. No provider output is gold.

## Frozen method

- Reuse the exact EXP-015 pool and typed System-One packet read-only.
- Use objective answer-key and deterministic-verifier gold.
- Use the public-selection partition only for calibration fitting and method
  development; keep the blind holdout untouched until the analysis is frozen.
- Fit scalar temperature scaling separately for local single and pairwise
  probability outputs.
- Compare label-only arms on normalized labels, accuracy, balanced accuracy,
  macro F1, per-domain behavior, and same-record agreement.
- Compute Brier score, NLL, ECE, and risk/coverage only for validated
  probability-bearing predictions. Do not infer probabilities from prose or
  labels.
- Treat provider failures as missing execution states rather than wrong labels;
  do not turn provider behavior into a scientific claim.

## Outputs

- `tasks/TASK-0019-calibrated-judge-study.md`
- `experiments/EXP-20260921-019-calibrated-judge-study/`
- `scripts/report_calibrated_judge_study.py`
- focused report/analysis tests
- an updated paper draft focused on calibration and independent judge
  comparison
- `checkpoints/CURRENT.md`

## Acceptance criteria

- [ ] New EXP-019 preregistration is committed before any new derived result.
- [ ] Luna and Sol are explicitly excluded from every primary EXP-019 table and
  comparison.
- [ ] The report explains the rubric, typed output contract, gold provenance,
  calibration split, temperature method, and probability eligibility rule.
- [ ] Existing EXP-014 through EXP-017 artifacts remain byte-immutable.
- [ ] A unified non-Luna report is generated from committed artifacts only.
- [ ] Grok's anomalous result receives a direct-route/parser sanity analysis
  without changing the frozen blind result.
- [ ] Per-domain, pairwise agreement, calibration, and uncertainty outputs are
  included where supported.
- [ ] Repository contract, Ruff, tests, and diff check pass.

## Checkpoint log

### 2026-09-21 — task opened

Status: active. The research scope was corrected from a generic objective
accuracy comparison to a calibration-and-judge-construction study. Luna and Sol
are excluded for vendor-independence reasons; Grok, Jev, Qwen Flash, and local
Qwen 4B remain.

Completed: created the isolated TASK-0019 worktree from the completed TASK-0017
calibration commit and read the project, checkpoint, and experiment contracts.

Exact files changed: this task file only.

Commands run: created `D:\\claude\\eval-lab\\.worktrees\\TASK-0019-calibrated-judge-study`;
read `PROJECT.md`, `checkpoints/CURRENT.md`, and
`docs/EXPERIMENT_PROTOCOL.md`; inspected existing calibration and provider
adapters.

Test results: no tests or provider calls run for TASK-0019 yet.

Decision: create a new experiment ID because the arm set and research question
changed. Reuse completed provider/local outputs read-only and make the first
new action a frozen offline preregistration/report plan.

Unresolved questions: whether the final paper should include a new direct Grok
sanity smoke as a diagnostic appendix; the existing blind result itself remains
unchanged either way.

Next atomic action: commit the EXP-019 preregistration and implement the
offline non-Luna analysis report.

## Handoff

Read in order:

1. `PROJECT.md`
2. `checkpoints/CURRENT.md`
3. this task file
4. `docs/EXPERIMENT_PROTOCOL.md`

Active worktree: `D:/claude/eval-lab/.worktrees/TASK-0019-calibrated-judge-study`
on branch `task/TASK-0019-calibrated-judge-study`.
