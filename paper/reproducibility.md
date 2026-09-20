# Reproducibility appendix

```powershell
$env:PYTHONPATH = "$PWD\src"
.venv\Scripts\python.exe scripts/build_selective_benchmark.py
.venv\Scripts\python.exe scripts/run_selective_escalation.py --skip-providers
.venv\Scripts\python.exe scripts/generate_research_artifacts.py
.venv\Scripts\python.exe scripts/validate_research_artifacts.py --benchmark benchmark/eval-lab-select-v0.1.0
```

Provider smoke calls are isolated with `scripts/smoke_task0010_providers.py`; pinned and rolling Jev outputs are never pooled.
