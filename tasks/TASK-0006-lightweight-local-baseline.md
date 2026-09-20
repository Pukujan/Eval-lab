# TASK-0006 — Lightweight Local Judge Baseline

- Status: ready-for-review
- Owner: Codex/local agent
- Priority: P0
- GitHub issue: #10
- Depends on: TASK-0002, TASK-0004, TASK-0005
- TASK-0003 predictions optional for direct Jev comparison when provider quota allows
- Branch: task/TASK-0006-lightweight-local-baseline

## Goal

Run at least one lightweight local Qwen judge over the same canonical synthetic and ARC evaluation records and produce the first v0 comparison report.

## Why

The core research question requires measuring how far a cheap/local judge can go before escalation to a stronger/provider judge is needed.

## Baseline ladder

Required first target:
- `Qwen/Qwen3-0.6B`

Preferred if feasible:
- `Qwen/Qwen3-1.7B`

Optional stretch:
- `Qwen/Qwen3-4B`

Do not make 4B a completion requirement.

## Feasibility gate

Before full evaluation:
1. load model/runtime;
2. run 20 canonical records;
3. record RAM/VRAM observations if available;
4. record median/p95 latency;
5. confirm context cap;
6. checkpoint before attempting a larger model.

## Scoring contract

Prefer forced-choice label sequence scoring rather than sampled prose.

For each legal label:
- compute conditional sequence log-likelihood;
- retain raw log-score;
- softmax across legal labels;
- emit normalized JudgePrediction.

Legal classes:
- PASS/FAIL
- A/B/TIE

If the chosen runtime cannot expose scores, label-only evaluation is allowed but probability/calibration metrics are marked unavailable.

## Inputs

- TASK-0005 canonical ARC record IDs
- synthetic fixtures
- TASK-0004 metrics/reporting
- `docs/SDD.md` section 10
- `docs/TDD.md` section 9

## Outputs

- local Qwen judge adapter
- model/runtime configuration
- 20-record feasibility report
- full chosen evaluation-slice predictions
- aggregate/per-domain metrics
- calibration results when probabilities are available
- first v0 comparison report
- checkpoint recommending next research task

## Allowed files

- `src/eval_lab/judges/qwen.py`
- `scripts/run_qwen_baseline.py`
- local runtime/config helpers
- `tests/`
- `pyproject.toml` local extra if needed
- experiment/report artifacts allowed by experiment protocol
- this task file
- `checkpoints/CURRENT.md`

Do not commit model weights/caches.

## Acceptance criteria

- [x] Qwen3-0.6B feasibility attempted first
- [x] at least one local model completes selected evaluation slice
- [x] exact model id/revision/runtime/device/dtype recorded
- [x] context cap recorded and enforced
- [x] identical canonical record IDs used for comparisons
- [x] probabilities/raw scores emitted when runtime supports them
- [x] metrics/report generated
- [x] Jev comparison included if successful Jev predictions exist; otherwise marked unavailable/provider-blocked
- [x] next research recommendation based on evidence recorded
- [x] full local merge gate passes

## Validation

See `docs/TDD.md` section 9.

## Stop conditions

Stop before scaling model size if:
- 0.6B already causes unacceptable memory pressure;
- record IDs differ from reference evaluation slice;
- runtime truncates context silently;
- probability computation uses incomparable class score semantics.

## Checkpoint log

Append execution evidence here.

### 2026-09-20 — Codex/local agent start

Started from accepted TASK-0005 merge commit `644202fbdd49a3735775ae1c55d1e621de1044d6` in dedicated worktree `D:\claude\eval-lab-TASK-0006` on branch `task/TASK-0006-lightweight-local-baseline`.

Read, in order: `PROJECT.md`, `AGENTS.md`, `checkpoints/CURRENT.md`, this task file, SDD section 10, TDD section 9, and `docs/ACCESS_MODEL_MATRIX.md`.

Commands and results:
- `git worktree add D:\\claude\\eval-lab-TASK-0006 -b task/TASK-0006-lightweight-local-baseline main` -> created at `644202fbdd49a3735775ae1c55d1e621de1044d6`.
- `git status --short --branch` -> clean `task/TASK-0006-lightweight-local-baseline`.

Decision: attempt `Qwen/Qwen3-0.6B` first with forced-choice scoring, a declared 4,096-token context cap, and a 20-record feasibility run before considering any larger model or fallback.

Next atomic action: implement the local Qwen adapter/runtime configuration and run the required 20-record feasibility gate without committing model weights or caches.

### 2026-09-20 — TASK-0006 local feasibility and calibration

Environment:
- Windows 11, Python `3.12.10`, NVIDIA GeForce RTX 4060 Laptop GPU with 8,188 MiB VRAM and 16 GiB system RAM.
- Dedicated worktree `D:\claude\eval-lab-TASK-0006`, branch `task/TASK-0006-lightweight-local-baseline`.
- Qwen runtime: PyTorch `2.11.0+cu128`, CUDA `12.8`, Transformers `5.17.0`, device `cuda:0`, dtype `torch.float16`.
- The model cache remained outside the repository; no credentials, `.env` files, or API keys were used.

Implemented files and artifacts:
- `src/eval_lab/judges/__init__.py`, `src/eval_lab/judges/qwen.py`.
- `scripts/run_qwen_baseline.py`.
- `tests/test_qwen.py`.
- `experiments/EXP-20260920-001-qwen-0-6b-raw/` raw feasibility arm.
- `experiments/EXP-20260920-002-qwen-0-6b-calibrated/` calibrated follow-up with raw/calibrated predictions, calibration artifact, results, and report.
- Updated this task log and `checkpoints/CURRENT.md`.

Feasibility commands and results:
- `nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader` -> RTX 4060 Laptop GPU, driver `592.00`, `8188 MiB`.
- `& .venv-qwen\\Scripts\\python.exe -c "import torch; ..."` -> `torch=2.11.0+cu128`, `cuda=True`, GPU detected.
- `& .venv-qwen\\Scripts\\python.exe scripts/run_qwen_baseline.py --limit 20 --output-dir experiments/EXP-20260920-001-qwen-0-6b-raw` -> completed 20/20 predictions; model revision `c1899de289a04d12100db370d81485cdf75e47ca`; median latency `190.28 ms`, p95 `348.39 ms`; no execution failures.
- `& .venv-qwen\\Scripts\\python.exe scripts/run_qwen_baseline.py --limit 20 --output-dir experiments/EXP-20260920-002-qwen-0-6b-calibrated` -> completed 20/20 evaluation predictions plus 6 separate calibration predictions; median latency `140.10 ms`, p95 `288.31 ms`; no execution failures.

Calibration evidence:
- Scalar temperature fit only on six synthetic single-label records with `split=calibration`; no test labels were used.
- Fitted temperature: `20.09618943455915`; applied to nine eligible single-label held-out predictions; pairwise records remained unchanged.
- Raw -> calibrated NLL: `1.269123964251841` -> `1.03955085928192`.
- Raw -> calibrated Brier: `0.8265485329815269` -> `0.651196287033591`.
- Raw -> calibrated ECE: `0.41255129356979847` -> `0.306242807193657`.

Validation commands and exact results:
- `& D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/check_repo_contract.py` -> `Repository contract OK`.
- `& D:\\claude\\eval-lab\\.venv\\Scripts\\ruff.exe check .` -> `All checks passed!`.
- `& D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe -m pytest -q` -> `55 passed in 1.34s`.

Decisions:
- Use forced-choice conditional sequence log-likelihoods and softmax over the exact canonical class set; raw log-scores and normalized probabilities are retained.
- Enforce the 4,096-token cap by raising before model execution when the assembled prompt and label continuation do not fit; no silent truncation.
- Keep the first local target at Qwen3-0.6B. The model fits comfortably on the machine and completed the feasibility slice, but the 20-record result is too small for a stronger-model claim.
- Mark Jev comparison `unavailable_provider_blocked` because the successful TASK-0003 smoke was not available; its live result was rate-limited and no label was fabricated.

Recommendation: use this evidence to define the next bounded research task around external/reference judge comparison and selective escalation on a larger frozen public slice. Do not begin fine-tuning from this 20-record feasibility result; a Qwen3-1.7B run remains optional and should be admitted only as a separately checkpointed experiment.

Blockers: none. The known GitHub Actions no-runner condition remains external infrastructure; local validation is green.

Next atomic action: commit the completed TASK-0006 artifacts and checkpoint, push `task/TASK-0006-lightweight-local-baseline`, open the review PR, and update this log with its URL before merge.

## Handoff

After TASK-0006, do not automatically start fine-tuning. Use the report to define the next task: judge training/distillation, harder benchmarks, rubric decomposition, or selective escalation.
