# Reproducibility appendix

```powershell
$env:PYTHONPATH = "$PWD\src"
.venv\Scripts\python.exe scripts/build_selective_benchmark.py
.venv\Scripts\python.exe scripts/run_selective_escalation.py --skip-providers --provider-limit 500 --output experiments/EXP-20260920-012-selective-escalation-qwen-streaming --pinned-predictions experiments/EXP-20260920-009-selective-escalation/provider-pinned.jsonl --rolling-predictions experiments/EXP-20260920-009-selective-escalation/provider-rolling.jsonl --qwen-predictions experiments/EXP-20260920-009-selective-escalation/qwen-streaming-final-merged-20260920-010/predictions.jsonl --experiment-id EXP-20260920-012-selective-escalation-qwen-streaming
.venv\Scripts\python.exe scripts/generate_research_artifacts.py --experiment experiments/EXP-20260920-012-selective-escalation-qwen-streaming --smoke-experiment experiments/EXP-20260920-009-selective-escalation
.venv\Scripts\python.exe scripts/validate_research_artifacts.py --benchmark benchmark/eval-lab-select-v0.1.0
```

Provider smoke calls are isolated with `scripts/smoke_task0010_providers.py`; pinned and rolling Jev outputs are never pooled.

Project Continuity Modules (PCM) was inspected at `Pukujan/project-continuity-modules@3a34b4a73842c824de5359f06e04568e8ce4aaa4`. Eval Lab maps PROJECT.md to PCM PROJECT, checkpoints/CURRENT.md to CURRENT, TASK files to TASK, and checkpoint logs to CHECKPOINT. PCM currently exposes minimal and software templates; its planned research profile is not implemented, so this release treats PCM as a continuity compatibility reference and keeps RO-Crate 1.3 plus PROV-O as the scientific provenance standard.
