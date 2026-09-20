# EXP-20260920-009 — Selective Escalation and System-One Differential

Status: frozen routing output with explicit provider statuses.

The complete objective pool contains 2,863 threshold-selection records and 2,356 final-evaluation records. The current local result evaluates all records with the frozen TASK-0009 student and retains unresolved states for provider arms whose bulk calls were unavailable. The independent smoke canary contains separate pinned Jev, rolling Jev, and YOLO-Auto Qwen files; rolling results are excluded from scientific pooling.

Exact commands:

```powershell
$env:PYTHONPATH = "$PWD\src"
.venv\Scripts\python.exe scripts/run_selective_escalation.py --skip-providers
.venv\Scripts\python.exe scripts/smoke_task0010_providers.py --env-file .env --limit 1
.venv\Scripts\python.exe scripts/generate_research_artifacts.py
.venv\Scripts\python.exe scripts/validate_research_artifacts.py --benchmark benchmark/eval-lab-select-v0.1.0
```
