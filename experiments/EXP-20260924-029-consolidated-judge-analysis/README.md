# EXP-20260924-029 — Consolidated judge analysis

Offline re-analysis of committed blind predictions. It makes **no model or
provider calls**. It supplies every number in the canonical paper
[`paper/paper.md`](../../paper/paper.md).

## Question

When independent judges, from small local models to frontier APIs, receive
identical typed decisions with objective gold labels, how do their accuracy and
coverage differ, and what does accuracy-only reporting hide?

## Inputs

The 760 blind records of the EXP-014/EXP-015 matched pool (652 single, 108
pairwise), plus the prediction files for 25 judge arms from EXP-013, EXP-014,
EXP-015, EXP-016, EXP-017, EXP-022, EXP-024, EXP-025 and EXP-027. Every input
file is listed in `results.json` with an LF-normalized SHA-256 so CRLF and LF
checkouts give the same hash.

EXP-027 local arms score the same records with a different harness (native
label scoring, not the provider typed-output protocol).

## Outputs

- `results.json` — per arm: coverage, conditional and all-record accuracy with
  95% Wilson intervals, status breakdown, per-mode and per-source accuracy,
  median latency and tokens where recorded; exact McNemar tests for all 325
  arm pairs (shared resolved records and all 760), Holm-corrected.
- `report.md` — human-readable summary of the same data.

## Reproduce

```powershell
uv sync --locked --extra dev --extra figures
uv run --locked python scripts/analyze_judge_comparison.py --update-paper
uv run --locked python scripts/generate_benchmark_figures.py
uv run --locked python -m pytest tests/test_judge_comparison_analysis.py
```

The script is deterministic; `tests/test_judge_comparison_analysis.py` checks
that the committed `results.json` and the generated paper tables are current.

## Not run / excluded

- MiMo V2.5: HTTP 402 on both canary attempts (EXP-024); no predictions.
- Bespoke Nimble-9B and Kev-9B: pinned configurations do not fit the 16 GiB host.
- Luna: excluded by the EXP-019 vendor-independent comparison policy.
