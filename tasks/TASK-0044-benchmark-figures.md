# TASK-0044 — Reproducible benchmark figures and research-page visuals

## Status

Complete for the Eval Lab figure release; Design Bakery site branch is ready
for commit and deployment.

## Objective

Create deterministic, data-first PNG/SVG figures for the consolidated benchmark
paper and publish the highest-value figures on the Design Bakery research page.
Anime imagery remains optional branding; numeric charts must be generated from
committed result artifacts and must not invent or pool incomparable metrics.

## Scope

- add a reproducible figure-generation script under `scripts/`;
- render direct-wave accuracy/coverage, InferHub accuracy/coverage, Grok
  protocol-ablation, and local-Qwen calibration figures;
- preserve provenance in a figure manifest and paper captions;
- copy the generated public assets into the Design Bakery research page and
  link them from the consolidated paper;
- run the repository contract/test gates and visually inspect the rendered PNGs.

## Scientific decisions

- accuracy is conditional on resolved labels; coverage is the resolved fraction
  of all 760 blind records;
- direct-provider and InferHub waves remain separate panels, not one pooled
  ranking;
- provider/parse failures remain visible as unresolved coverage;
- no probability metrics are rendered for label-only providers;
- local-Qwen calibration is shown as a separate metric panel because it is a
  confidence-interface result, not an accuracy win;
- figure inputs are committed EXP-022, EXP-024, EXP-025, and EXP-019 report
  artifacts only.

## Files expected to change

- `tasks/TASK-0044-benchmark-figures.md`
- `checkpoints/CURRENT.md`
- `scripts/generate_benchmark_figures.py`
- `paper/figures/benchmark/*.png`
- `paper/figures/benchmark/*.svg`
- `paper/figures/benchmark/manifest.json`

The Design Bakery worktree will receive corresponding public assets and paper
content changes in its own commit/branch.

## Commands and evidence

- `D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts\\generate_benchmark_figures.py`
  regenerated four PNG/SVG pairs and `paper/figures/benchmark/manifest.json`.
- `D:\\claude\\eval-lab\\.venv\\Scripts\\ruff.exe check scripts\\generate_benchmark_figures.py`
  passed.
- `D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe -m py_compile scripts\\generate_benchmark_figures.py`
  passed.
- `git diff --check` passed.
- Visual inspection completed for all four PNGs: direct wave, InferHub wave,
  Grok protocol ablation, and local-Qwen calibration. Labels, captions, axes,
  unresolved/no-schema states, and calibration callout were readable.
- The generated manifest records SHA-256 fingerprints for EXP-022, EXP-024,
  EXP-025, and EXP-019 source result artifacts.

## Unresolved questions

- The Design Bakery full frontend build was not completed because the local
  pnpm workspace dependency bootstrap was still copying packages after more
  than four minutes; the install was stopped. Static asset/path checks passed.

## Next atomic action

Commit/push the Eval Lab figure release and the Design Bakery research-page
asset/content update, then verify the hosted deployment serves all four PNGs.
