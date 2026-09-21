# Reproducibility appendix

```powershell
$env:PYTHONPATH = "$PWD\src"
.venv\Scripts\python.exe scripts/build_selective_benchmark.py
.venv\Scripts\python.exe scripts/run_selective_escalation.py --skip-providers --provider-limit 500 --output experiments/EXP-20260920-012-selective-escalation-qwen-streaming --pinned-predictions experiments/EXP-20260920-009-selective-escalation/provider-pinned.jsonl --rolling-predictions experiments/EXP-20260920-009-selective-escalation/provider-rolling.jsonl --qwen-predictions experiments/EXP-20260920-009-selective-escalation/qwen-streaming-final-merged-20260920-010/predictions.jsonl --experiment-id EXP-20260920-012-selective-escalation-qwen-streaming
.venv\Scripts\python.exe scripts/generate_research_artifacts.py --experiment experiments/EXP-20260920-012-selective-escalation-qwen-streaming --smoke-experiment experiments/EXP-20260920-009-selective-escalation
.venv\Scripts\python.exe scripts/validate_research_artifacts.py --benchmark benchmark/eval-lab-select-v0.1.0
```

Provider smoke calls are isolated with `scripts/smoke_task0010_providers.py`; pinned and rolling Jev outputs are never pooled.
