# Eval Lab paper

**Canonical paper:** [`paper.md`](paper.md) — *Accuracy is not enough:
correctness and coverage of independent judges on identical objective
decisions.*

Research question: when independent judges, from small local models to
frontier APIs, receive identical typed decisions with objective gold labels,
how do their accuracy and coverage differ, and what does accuracy-only
reporting hide?

## Layout

| Path | Contents |
| --- | --- |
| `paper.md` | The single canonical paper. |
| `limitations.md` | Limitations of the canonical paper (mirrors Section 6). |
| `reproducibility.md` | How to regenerate every table and figure offline. |
| `data/` | Interactive chart data with JSON-LD provenance (`scripts/export_chart_data.py`); see `docs/PROVENANCE.md`. |
| `figures/benchmark/` | Generated figures and `manifest.json` with source hashes. |
| `references.bib` | Bibliography used by the archived LaTeX draft. |
| `archive/` | Superseded drafts, kept for history; see `archive/README.md`. |

## Structure

`paper.md` has two layers.

- **Quick read (about one screen):** a claim title, a one-sentence subtitle
  (`<p class="paper-subtitle">`), what we did told around one real question from
  the blind set, four numbered findings with two charts, and one line on what to
  do. No internal IDs, statistics or file paths. A reader can stop there.
- **Full data and methods:** everything behind those numbers, in the same page:
  how we scored, what each run lost, the leaders, what the skipped questions
  hide, local models, request settings, every judge in full, paired tests, the
  Grok Build follow-up, calibration, limitations, future work and
  reproducibility. Method nuances sit in `<details class="deep-dive">` blocks
  whose summary starts with "Details for deep divers"; the rest is in collapsed
  `<details>` tables.

Jargon is defined on first use, and only in the appendix. Body tables are small
(≤ ~8 rows).

Markdown conventions (render on GitHub and are mirrored on the Design Bakery
site):

- Callouts use GitHub alert syntax: `> [!NOTE]` for side notes.
- Every figure has four SVG variants from one script run:
  `NAME.{light,dark}.{wide,tall}.svg` (wide for desktop, tall for screens
  under ~700px), plus `NAME.data.json` with the plotted numbers so a site can
  later draw the same chart interactively. In the paper a figure is
  `<figure data-figure="NAME"><picture>` with `<source>` elements for
  dark/tall (`prefers-color-scheme`, `max-width: 700px`) and an
  `<img src="figures/benchmark/NAME.light.wide.svg">` fallback, followed by a
  `<figcaption>` whose first sentence (after the figure label) is the
  takeaway. Chart titles state the finding.
- Charts are plain bars with direct labels, a takeaway title and a source line:
  the headline chart is a stacked bar of right / wrong / skipped per grader out
  of all 760 questions, the accuracy charts are plain bars, and the tied judges
  are greyed. No dumbbell, whisker or error-bar charts. See
  `writing-guide/GUIDE.md` section 4 for the rules these follow.
- Figure A1 (`judges_ranked`) greys out judges tied with the leader: a judge
  shares rank 1 when the Holm-corrected McNemar p-value over all 760 questions
  is at least 0.05 (`shared_ranks_all_record` in EXP-029 `results.json`).
- Appendix tables sit inside `<details><summary>…</summary>` with blank lines
  around the generated block so Markdown tables render.

## Rules

- Tables inside `<!-- generated:NAME -->` blocks in `paper.md` are written by
  `scripts/analyze_judge_comparison.py --update-paper`. Never hand-edit them;
  `tests/test_judge_comparison_analysis.py` fails if they drift, and also fails
  if a decimal percentage in the prose is not found in the committed results.
- Figures are written by `scripts/generate_benchmark_figures.py` from committed
  results files; the manifest records each source's SHA-256.
- Links in the paper point at Eval Lab `main`.

See also `docs/RESEARCH_ARTIFACT_STANDARD.md`.
