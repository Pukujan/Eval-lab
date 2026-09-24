# EXP-025 — Grok protocol ablation results

**Status:** complete  
**Primary model:** Grok 4.6 Build CLI  
**Gold provenance:** frozen EXP-015 answer keys and deterministic verifiers  
**Blind holdout:** 760 source-problem-disjoint records

## Decision

The preregistered public gate required at least 95% public coverage and an
absolute improvement of at least 0.10 in mode-balanced accuracy over the
typed-schema baseline. No alternative passed. The blind confirmation therefore
used the original typed-schema protocol. Grok 4.7 was not rerun under EXP-025;
its EXP-022 result remains the version comparator.

## Public diagnostic

| Variant | Resolved | Coverage | Mode-balanced score | Statuses |
|---|---:|---:|---:|---|
| explicit_no_schema | 0/64 | 0.0000 | n/a | parse_error=57, provider_error=6, rate_limited=1 |
| explicit_schema | 63/64 | 0.9844 | 0.2580645 | ok=63, provider_error=1 |
| semantic_schema | 63/64 | 0.9844 | 0.2661290 | ok=63, provider_error=1 |
| typed_schema | 64/64 | 1.0000 | 0.2656250 | ok=64 |

The first no-schema pass exposed a Windows locale-decoding defect in the
shared stream reader. The reader was repaired to use explicit UTF-8 replacement
decoding, and the arm was resumed from its normalized checkpoint. Only the
repaired arm's final output is used here.

## Blind confirmation

| Variant | Resolved | Coverage | Mode-balanced score | Single accuracy | Pairwise accuracy | Statuses |
|---|---:|---:|---:|---:|---:|---|
| typed_schema | 757/760 | 0.9961 | 0.2585766 | 0.4984615 (650/652) | 0.0186916 (107/108) | ok=757, provider_error=3 |

The low score and the single/pairwise asymmetry persisted under the selected
baseline. The result is therefore a protocol-specific underperformance
diagnosis, not evidence of universal Grok capability weakness. The public
ablation did find a real harness defect, but repairing it and changing labels
or schema did not produce a materially better contract.

## Reproducibility

- Public run artifacts: runs/public-diagnostic-20260922/
- Blind run artifacts: runs/blind-typed-baseline-20260922/
- Combined report: report/report.md
- Public selection: public-report/selection.json
- Preregistration: experiment.yaml and README.md
