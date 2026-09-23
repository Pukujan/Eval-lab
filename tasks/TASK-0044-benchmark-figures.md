# TASK-0044 — Reproducible benchmark figures and research-page visuals

## Status

Complete. The Eval Lab figure release and Design Bakery research-page release
are merged; the hosted page and all four public PNG assets were verified.

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

## Goal

Publish reproducible, data-first benchmark figures from committed result
artifacts and make the figures available in the consolidated paper and public
research page without pooling incomparable experiments or inventing metrics.

## Acceptance criteria

- Four PNG/SVG figure pairs are generated from EXP-022, EXP-024, EXP-025, and
  EXP-019 artifacts.
- The figure manifest records source paths and SHA-256 fingerprints.
- The consolidated paper embeds the figures with captions explaining the
  evidence and limitations.
- The Design Bakery research page serves the corresponding assets with alt text
  and responsive styling.
- Ruff, syntax compilation, and repository checks are run; unresolved build
  limitations are recorded rather than hidden.

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
  than four minutes; the install was stopped. Static asset/path checks passed,
  and the hosted Vercel preview/deployment build plus production rendering
  were verified.

## Checkpoint log

TASK-0044 generated and visually inspected the four figures, embedded them in
the paper, and published the Eval Lab and Design Bakery changes. The first
merged PR exposed only a task-contract omission: this file lacked the required
headings checked by `scripts/check_repo_contract.py`; PR #32 added those
headings without changing any experiment or figure content. Design Bakery PR
#39 then merged the public assets/content; the hosted page serves all four
figures.

## Handoff

The benchmark figure release is complete. If the site build or deployment
fails, debug only the Design Bakery asset/rendering path; do not regenerate
figures from hand-entered values or alter completed experiment artifacts.

## Next atomic action

Resume the preregistered objective-domain track in TASK-0042: freeze the GLEIF
snapshot and implement its canonical adapter before blind scoring.
