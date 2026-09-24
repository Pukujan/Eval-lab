# TASK-0057 — Rewrite the judge paper as a readable narrative

## Status

Complete pending PR/CI/merge — tracked by GitHub issue #65.

## Objective

Owner feedback on the published paper said it was hard to read: walls of
numbers, huge tables, charts that are hard to read, and a story that is hard to
follow. Rewrite `paper/paper.md` for a smart non-specialist without changing
the research question or the evidence. Every number must stay script-backed.

## Goal

Structure: At a glance → The problem → Setup → What happened → What we found
(four findings, each with one headline, a short paragraph and at most one chart)
→ What it means → Limitations → Future work, with full tables in collapsed
appendices.

## Scope

- `paper/paper.md`, `paper/README.md`, `paper/limitations.md`,
  `paper/reproducibility.md`
- `scripts/analyze_judge_comparison.py`: slim `body_*` tables (≤ 8 rows,
  ≤ 5 columns, 1-decimal percentages) and a generated EXP-025 Grok appendix
  table, which replaces the hand-typed one
- `scripts/generate_benchmark_figures.py`:
  - three new finding charts, 9 in wide, ≥ 14 pt labels, with the finding as
    the title;
  - larger fonts on the appendix charts;
  - removed `blind_conditional_vs_all_record`
- `tests/test_judge_comparison_analysis.py`: new check that every decimal
  percentage and 4-decimal metric in the paper prose appears in committed
  EXP-029, EXP-025 or EXP-019 results
- `experiments/EXP-20260924-029-consolidated-judge-analysis/` (regenerated
  `results.json` and `report.md`; README note)
- `tasks/TASK-0057-readable-paper.md`, `checkpoints/CURRENT.md`

## Scientific decisions

- No new runs; same 25 arms, same EXP-029 statistics.
- Body numbers are rounded to 1 decimal; exact values with Wilson intervals
  and Holm-corrected McNemar tests are in Appendices A and B.
- One correction relative to the previous draft: Kev-4B's advantage over the
  baseline is **not** mostly from pairwise records. It gains +60 correct on
  single records and +47 on pairwise records. The text now says it is
  strongest on pairwise (93.5%) and only modestly above the baseline on single
  records (59.5%).
- The EXP-025 no-schema failure breakdown (57/6/1) is not in EXP-025
  `results.json`, so it was dropped from the table ("no readable answers").

## Acceptance criteria

- The paper follows the structure above, and body tables stay within ~8 rows
  and ~5 columns.
- The drift test and the prose-number test pass.
- The figures are regenerated deterministically and the manifest is updated.
- Local gates and CI pass, and the PR is squash-merged.

## Checkpoint log

### 2026-09-24 — narrative rewrite

Status: complete pending PR/CI/merge; GitHub issue #65 created.

Commands run (authoring clone, Linux):

- `analyze_judge_comparison.py --update-paper` and
  `generate_benchmark_figures.py` (charts checked visually at 700 px wide)
- `uv lock --check`, `check_repo_contract.py`, `ruff check .`,
  `ruff format --check` on changed Python files, `mypy src/eval_lab`,
  `python -m pytest -q`, `uv build`

Decisions: the Design Bakery rendering work (design-bakery issue #48) is
paused by the owner pending a UX research pass. This task changes only Eval
Lab.

## Handoff

The site mirror (`db-r-2026-010`) still shows the TASK-0056 version until the
paused design-bakery work resumes.

## Next atomic action

After merge, close issue #65 by hand. `finalize_checkpoint.py` refuses while
the untracked `worktrees/` folder exists.
