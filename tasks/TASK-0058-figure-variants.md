# TASK-0058 — Light/dark and wide/tall figure variants, ranked judge chart

## Status

Figure variants merged in PR #68 (`0b996a5`). Follow-up (two-layer paper)
pending PR/CI/merge — issue #67 reopened for it.

## Objective

The paper's figures must read well in light and dark themes and on phones, and
the Design Bakery site (design-bakery #48) needs matching variants. Replace the
appendix accuracy-vs-coverage scatter with a ranked chart, and move the paper
metadata below the At a glance box.

## Goal

Every figure is produced by one script run as four SVG variants,
`NAME.{light,dark}.{wide,tall}.svg`, plus `NAME.data.json` with the plotted
numbers (so a site can later render the same chart interactively, with the
SVGs as the static fallback).

## Scope

- `scripts/generate_benchmark_figures.py`: themes (light, dark) × layouts
  (wide 10 in, tall 4.4 in); tall layouts stack multi-panel charts; ≥ 14 pt
  text; per-figure source line; PNGs dropped; `manifest.json` lists variants
  and data files; new `judges_ranked` replaces `blind_accuracy_vs_coverage`
- `scripts/analyze_judge_comparison.py`: `shared_ranks_all_record` in EXP-029
  `results.json` (competition rank; a judge shares the rank of its group's top
  judge when the Holm-corrected McNemar p over all 760 questions is ≥ 0.05)
- `paper/paper.md`: `<figure data-figure="NAME"><picture>` markup with
  dark/tall `<source>` elements; Figure A1 is the ranked chart; Finding 1 notes
  that four judges share first place; Status/Evidence/Repository moved below
  At a glance
- `paper/README.md`, `paper/reproducibility.md`
- `tasks/TASK-0058-figure-variants.md`, `checkpoints/CURRENT.md`

## Scientific decisions

- No new runs. Shared ranks are a presentation of the existing EXP-029
  Holm-corrected all-record McNemar tests; no new test family is introduced.
- Result: four judges share rank 1 (Qwen3.8 Flash, Qwen 3.8 Max, Kimi K2.7
  Code, GLM 5.3 Flash); eight judges score below the always-same-answer
  baseline.

## Acceptance criteria

- Six figures × four SVG variants plus data files, regenerated
  deterministically (two runs, identical hashes).
- Variants checked visually (wide at 760 px, tall at 350 px, both themes).
- Drift and prose-number tests pass; local gates and CI pass; PR squash-merged.

## Checkpoint log

### 2026-09-24 — figure variants

Status: complete pending PR/CI/merge; GitHub issue #67 created.

Commands run (authoring clone, Linux):

- `analyze_judge_comparison.py --update-paper`,
  `generate_benchmark_figures.py` twice (identical hashes)
- `uv lock --check`, `check_repo_contract.py`, `check_workspace_policy.py`,
  `ruff check .`, `ruff format --check` on changed Python files,
  `mypy src/eval_lab`, `python -m pytest -q`, `uv build`

### 2026-09-24 — two-layer paper (follow-up)

Owner request: the paper must work as a two-minute quick read and a deep
dive. Changes in `paper/paper.md`:

- claim title and a one-sentence subtitle (`<p class="paper-subtitle">`);
- "The short version" box: five plain-language bullets, at most two numbers
  each, followed by one summary chart (the skipped-questions chart, now
  Figure 1; the accuracy chart is Figure 2);
- each finding: a question heading, a bold one-line takeaway, a short
  paragraph, at most one chart, then `<details class="deep-dive">` ("Details
  for deep divers") with method nuances, tables and statistics; Setup and
  What happened follow the same pattern;
- jargon (AI judge, rate limit, blind set, API/local, coverage, harness,
  Wilson interval, McNemar, Holm correction, preregistered, tokens, thinking,
  always-same-answer baseline) defined on first use;
- `paper/README.md` documents the two layers.

No numbers changed; the drift and prose-number tests pass.

## Handoff

design-bakery #48 (TASK-DB-0053) mirrors this paper and serves the variants
with theme- and width-aware switching.

## Next atomic action

After merge, close issue #67 by hand if "Closes #67" does not close it.
