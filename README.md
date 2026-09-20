# Eval Lab

Clean-slate lab for objective-grounded judge evaluation and calibration.

## v0 goals

- Benchmark Jev as a fast structured classifier/judge.
- Compare lightweight local students: Qwen3-4B, Qwen3-1.7B, and encoder classifiers.
- Keep objective verifiers / benchmark answer keys separate from model-generated supervision.
- Measure accuracy, balanced accuracy, Brier score, ECE, NLL, position bias, and selective-risk coverage.
- Use stronger chat models only for rubric decomposition, critiques, hard-negative generation, and disagreement analysis.

## First experiment

1. Build a small held-out classification set with objective labels.
2. Run Jev 1.13 Free on exactly the same examples and rubric wording.
3. Run a local baseline on the same set.
4. Fit calibration only on a separate calibration split.
5. Evaluate once on untouched test data.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export OPENCODE_API_KEY=...
python scripts/jev_smoke.py
```

Do not commit API keys or private benchmark data.
