# Reproducibility

Everything in [`paper.md`](paper.md) regenerates offline from committed
artifacts. No provider credentials or model downloads are needed.

```powershell
uv sync --locked --extra dev --extra figures
uv run --locked python scripts/analyze_judge_comparison.py --update-paper
uv run --locked python scripts/generate_benchmark_figures.py
uv run --locked python -m pytest tests/test_judge_comparison_analysis.py
uv run --locked python scripts/export_chart_data.py          # needs a clean tree
uv run --locked python -m pytest tests/test_chart_data_export.py
```

| Output | Produced by | From |
| --- | --- | --- |
| `experiments/EXP-20260924-029-consolidated-judge-analysis/results.json`, `report.md` | `scripts/analyze_judge_comparison.py` | blind prediction files of EXP-013/014/015/016/017/022/024/025/027 |
| Generated tables in `paper.md` (slim `body_*` tables and full appendix tables) | `scripts/analyze_judge_comparison.py --update-paper` | EXP-029 analysis (plus EXP-025 public variants for the Grok appendix table) |
| `figures/benchmark/finding_accuracy_range.*`, `finding_skipped_questions.*`, `finding_request_settings.*` (body), `judges_ranked.*` (appendix; `*.svg` variants plus `*.data.json`) | `scripts/generate_benchmark_figures.py` | EXP-029 `results.json` |
| `figures/benchmark/grok_protocol_ablation.*` | `scripts/generate_benchmark_figures.py` | EXP-025 results |
| `figures/benchmark/local_qwen_calibration.*` | `scripts/generate_benchmark_figures.py` | EXP-019 results |
| `data/judges-blind-760.json`, `data/charts/*.json`, `data/index.json` (interactive chart data, JSON-LD provenance) | `scripts/export_chart_data.py` | EXP-029 `results.json`, figure `*.data.json`, `data/sources/arm-metadata.yaml` |

Input files are fingerprinted with LF-normalized SHA-256 (in EXP-029
`results.json` and `figures/benchmark/manifest.json`), so Windows CRLF and
Linux LF checkouts give identical hashes. Both scripts are deterministic;
rerunning them should produce no diff. `tests/test_judge_comparison_analysis.py` also checks that every decimal percentage and 4-decimal metric in the paper prose appears in the committed EXP-029, EXP-025 or EXP-019 results.

The archived selective-escalation LaTeX draft keeps its own reproducibility
notes in `archive/selective-escalation/reproducibility.md`.
