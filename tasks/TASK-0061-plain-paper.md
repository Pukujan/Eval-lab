# TASK-0061 — Plain-language paper and simple charts

## Status

In progress. GitHub issue #74. Branch `task/TASK-0061-plain-paper`.

## Objective

Owner feedback (2026-09-24): the published paper reads as AI-written, is too
verbose, and a first-time reader cannot tell what it is about. The charts
(dumbbell, ranked CI dots) make no sense.

Rewrite the top of `paper/paper.md` around one real question from the 760-item
blind set, in a human voice, following `writing-guide/GUIDE.md` and
`writing-guide/rules.json`. Move methods, statistics, per-run tables, the Grok
Build follow-up and calibration into a "Full data and methods" appendix. Redraw
the headline charts as plain bars.

## Goal

A first-time reader understands the paper in one screen: what the study did,
what the four findings are, and what to do about them. The charts read as plain
bars anyone can follow without a legend.

## Scope

- `paper/paper.md`: short main text (claim title, one-sentence subtitle, real
  example question, numbered findings, one-line "what to do"), then a "Full data
  and methods" appendix holding the old sections and tables intact
- `scripts/generate_benchmark_figures.py`: Figure 1 becomes a stacked horizontal
  bar per judge (right/wrong/skipped of 760, sorted by right, direct labels,
  labelled baseline line, 1-3 annotations, plain source line); the ranked chart
  becomes plain bars with statistically tied judges greyed; the settings chart
  becomes two bars (84.5% vs 97.4%) with plain setting names; light/dark x
  wide/tall SVG variants and `NAME.data.json` kept
- `paper/data/` re-exported with `scripts/export_chart_data.py` (clean tree)
- `paper/README.md`, `paper/limitations.md`, `checkpoints/CURRENT.md`
- `tasks/TASK-0061-plain-paper.md`

## Scientific decisions

- No new runs, no new numbers. Every figure and table still comes from the
  committed EXP-029 / EXP-025 / EXP-019 results; the prose-number test and the
  table-drift test are unchanged and must keep passing.
- The DeepSeek V4 Flash skip rate is computed from committed data: 149 of 760
  records unresolved (coverage 0.8039), which is about one question in five.
  It is stated in words because `19.6` is not a leaf value in the committed
  results and the prose-number test only accepts numbers traceable to them.
- The example question is blind record `arc-single:Mercury_405804:wrong`
  ("Which resource is renewable?", answer key `fail`, candidate `A) oil`).

## Acceptance criteria

- `pytest tests` green, including the prose-number and table-drift tests.
- Six figures x four SVG variants plus data files, regenerated deterministically.
- PNG previews of the new charts and the new main text rendered to
  `D:\claude\agent-runs\el-paper-shots\`.
- PR merged with green CI.

## Checkpoint log

### 2026-09-24 — plain-language rewrite, simple charts, previews

Status: in progress; PR/CI/merge pending.

Done:

- `paper/paper.md` rewritten: claim title, one-sentence subtitle, a worked
  example from blind record `arc-single:Mercury_405804:wrong` (DeepSeek V4 Flash
  answered 99.8% right but scored 80.3% over all 760 because 149 replies were
  unreadable), four numbered findings, a one-line "what to do", then "Full data
  and methods" holding the old sections, generated blocks and tables intact.
- `scripts/generate_benchmark_figures.py`: Figure 1 is now a stacked
  right/wrong/skipped bar per judge out of 760 with a labelled 50.3% baseline;
  Figure 2 is plain accuracy bars with judges tied with the leader greyed;
  Figure 3 is two bars for the same model under two settings; the ranked chart
  greys tied judges. All six figures still emit four SVG variants plus
  `NAME.data.json`; two runs produce identical hashes.
- `paper/data/` re-exported from the clean tree; `paper/README.md`,
  `paper/limitations.md`, `paper/reproducibility.md` describe the new charts.
- `pytest tests`: 189 passed, 1 failed. The failure is
  `test_repo_contract.py::test_contract_validator_passes` and it is
  environmental: the workspace-policy check lists the other worktrees
  registered on this machine (`D:\claude\eval-lab`, `wt-el-live`,
  `worktrees\TASK-0054-harness-review`), which are outside this worktree. The
  two task-file findings it reported were real and are fixed here.
- PNG previews in `D:\claude\agent-runs\el-paper-shots\`: six figures x
  light wide and light tall, plus `paper-top.light.wide.png` for the new main
  text.

## Handoff

The Design Bakery mirror (design-bakery #48) consumes `paper/data/` and the
four SVG variants per figure; the chart data was re-exported for this rewrite.

## Next atomic action

Commit in steps, push `task/TASK-0061-plain-paper`, open the PR, wait for CI,
then squash-merge.
