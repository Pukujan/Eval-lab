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
| `figures/benchmark/` | Generated figures and `manifest.json` with source hashes. |
| `references.bib` | Bibliography used by the archived LaTeX draft. |
| `archive/` | Superseded drafts, kept for history; see `archive/README.md`. |

## Structure

`paper.md` has two layers.

- **Quick read (about two minutes):** a claim title, a one-sentence
  subtitle (`<p class="paper-subtitle">`), a plain-language **short version**
  (3–5 bullets, no jargon, at most two numbers each) and one summary chart.
  A reader can stop there.
- **Full read:** The problem → Setup → What happened → What we found → What it
  means → Limitations → Future work. Each finding has a question as its
  heading, then a one-line bold takeaway, a short paragraph and at most one
  chart. Method nuances, per-experiment tables and statistics sit in
  `<details class="deep-dive">` blocks whose summary starts with "Details for
  deep divers". Full tables and paired tests are in collapsed appendices.

Jargon is defined on first use. Body tables are small (≤ ~8 rows).

Markdown conventions (render on GitHub and are mirrored on the Design Bakery
site):

- Callouts use GitHub alert syntax: `> [!IMPORTANT]` for the short-version box,
  `> [!NOTE]` for side notes.
- Every figure has four SVG variants from one script run:
  `NAME.{light,dark}.{wide,tall}.svg` (wide for desktop, tall for screens
  under ~700px), plus `NAME.data.json` with the plotted numbers so a site can
  later draw the same chart interactively. In the paper a figure is
  `<figure data-figure="NAME"><picture>` with `<source>` elements for
  dark/tall (`prefers-color-scheme`, `max-width: 700px`) and an
  `<img src="figures/benchmark/NAME.light.wide.svg">` fallback, followed by a
  `<figcaption>` whose first sentence (after the figure label) is the
  takeaway. Chart titles state the
  finding.
- Figure A1 (`judges_ranked`) uses shared ranks: a judge shares the rank of the
  top judge of its group when the Holm-corrected McNemar p-value over all 760
  questions is at least 0.05 (`shared_ranks_all_record` in EXP-029
  `results.json`).
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
