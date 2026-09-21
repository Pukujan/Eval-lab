# EXP-20260921-014 exact reproduction commands

Run from the repository root with `PYTHONPATH=src` and the shared local virtual environment.

```powershell
$env:PYTHONPATH='src'
& 'D:\claude\eval-lab\.venv\Scripts\python.exe' scripts/check_repo_contract.py
& 'D:\claude\eval-lab\.venv\Scripts\ruff.exe' check .
& 'D:\claude\eval-lab\.venv\Scripts\python.exe' -m pytest -q
```

The source freeze was created before live labels:

```powershell
$env:PYTHONPATH='src'
& 'D:\claude\eval-lab\.venv\Scripts\python.exe' scripts/freeze_independent_jev_benchmark.py
```

Pinned and rolling primary calls used the frozen blind partition and separate output directories:

```powershell
& 'D:\claude\eval-lab\.venv\Scripts\python.exe' scripts/run_independent_jev_arm.py --pool experiments/EXP-20260921-014-independent-jev-benchmark --partition blind_holdout --model typesafe/jev-1.13 --output experiments/EXP-20260921-014-independent-jev-benchmark/jev-pinned-blind-20260921 --timeout 90 --env-file 'C:\Users\pujan\OneDrive\Desktop\configs\.env'
& 'D:\claude\eval-lab\.venv\Scripts\python.exe' scripts/run_independent_jev_arm.py --pool experiments/EXP-20260921-014-independent-jev-benchmark --partition blind_holdout --model '~typesafe/jev-latest' --output experiments/EXP-20260921-014-independent-jev-benchmark/jev-rolling-blind-20260921 --timeout 90 --env-file 'C:\Users\pujan\OneDrive\Desktop\configs\.env'
```

The comparison report was generated with:

```powershell
& 'D:\claude\eval-lab\.venv\Scripts\python.exe' scripts/report_independent_jev.py --pool experiments/EXP-20260921-014-independent-jev-benchmark --pinned experiments/EXP-20260921-014-independent-jev-benchmark/jev-pinned-blind-20260921 --rolling experiments/EXP-20260921-014-independent-jev-benchmark/jev-rolling-blind-20260921 --qwen experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-blind-merged-20260921 --student experiments/EXP-20260920-008-small-judge-training/artifacts/student_D.json
```

Recovery smoke and robustness calls were stored under `recovery-smoke-pinned-20260921/`, `perturbations-pinned-20260921/`, and `perturbations-pinned-recovery-20260921/`. Credentials were read from the local environment file and never printed or written to artifacts.

The final pre-frozen robustness schedule was:

```powershell
& 'D:\claude\eval-lab\.venv\Scripts\python.exe' scripts/run_independent_jev_perturbations.py --pool experiments/EXP-20260921-014-independent-jev-benchmark --model typesafe/jev-1.13 --output experiments/EXP-20260921-014-independent-jev-benchmark/perturbations-pinned-final-20260921 --primary experiments/EXP-20260921-014-independent-jev-benchmark/jev-pinned-blind-20260921 --timeout 90 --env-file 'C:\Users\pujan\OneDrive\Desktop\configs\.env'
```
