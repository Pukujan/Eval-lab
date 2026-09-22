# EXP-025 — Grok protocol ablation

EXP-025 is complete. The public gate selected the original typed-schema
protocol because no alternative improved the mode-balanced score by the
preregistered 0.10 threshold while retaining at least 95% coverage.

The blind Grok 4.6 typed-baseline rerun resolved 757/760 records (99.605%
coverage), with 3 provider errors. Single accuracy was 49.85% over 650/652
resolved records; pairwise accuracy was 1.87% over 107/108. The low score and
single/pairwise asymmetry persist under the selected baseline. A Windows
locale-decoding defect was repaired in the no-schema arm, but no tested
protocol produced a materially better contract.

See the machine-readable summary in results.json, the detailed report in
report/report.md, and the public paper synthesis in paper/benchmark_comparison_study.md.
