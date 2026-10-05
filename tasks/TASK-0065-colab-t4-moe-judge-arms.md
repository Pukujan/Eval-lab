# TASK-0065 - Google Colab T4 compute path and two MoE judge arms

## Status

In progress. GitHub issue #83. Branch `task/TASK-0065-colab-t4-moe-judge-arms`.

## Goal

Add a free-tier Google Colab T4 GPU as a second judge compute path, and grade
two recent small-active-parameter MoE models through the frozen Eval Lab
decision benchmark as label-only typed-choice arms: Ornith 1.5 35B-A3B (IQ2_XXS)
and Maple Preview 20B-A1B (requantized TQ2_0 -> Q2_0, Q4_K output head).

## Scope

- New experiment `experiments/EXP-20261005-031-colab-t4-moe-judge-arms/`
  (append-only; no completed experiment is modified) with requests, verbatim
  raw runner output, canonical predictions, `results.json`, and `report.md`.
- `scripts/build_colab_moe_requests.py`: build gold-free requests from the frozen
  EXP-015 pool.
- `scripts/run_colab_moe_judge.py`: serve a GGUF with `llama-server` and ask for
  exactly one legal label under a GBNF grammar; append+fsync every prediction so
  a killed free-tier session resumes.
- `scripts/finalize_colab_moe_experiment.py`: normalize raw rows to the local
  bakeoff prediction shape and summarize with the shared summarizer.
- Tests: `tests/test_colab_moe_judge.py`, `tests/test_colab_moe_experiment.py`.
- `AGENTS.md`: a bounded compute exception for the free-tier Colab T4 path.
- Regenerate the run telemetry ledger in this task's checkpoint.

## Acceptance criteria

- Requests carry no gold label; their LF-normalized SHA-256 equals the files
  served on the VM.
- Both arms cover every record (coverage 1.0000) with a legal label and varied
  answers (no constant-answer collapse).
- `results.json`/`report.md` come from the shared summarizer; no hand-typed
  metrics; the blind partition selects nothing.
- Local gates pass: repo contract, workspace policy, Ruff, mypy, pytest,
  telemetry `--check`.

## Checkpoint log

### 2026-10-05 - experiment run and packaged

- Ornith 1.5 35B-A3B (IQ2_XXS): public 648/648 ok (0.5818), blind 760/760 ok
  (0.5539; single 0.5337, pairwise 0.6759).
- Maple Preview 20B-A1B (Q2_0): public 648/648 ok (0.4954), blind 760/760 ok
  (0.4895; single 0.4969, pairwise 0.4444).
- Maple's official ternary TQ2_0 file has no CUDA kernel in stock llama.cpp
  (~41 prompt t/s on CPU); requantized to Q2_0 keeping the Q4_K head
  (~2,000 prompt t/s / ~200 gen t/s on the T4). The requantized file is not
  committed; its hash is in `model-revisions.json`.
- Colab session stopped after the run; no active sessions.
- Decision (advisor): land TASK-0064 first because the repo-global telemetry
  ledger cannot be split between two experiments; move the EXP-031 bundle,
  scripts, and tests aside, then land this task on its own branch.

### 2026-10-05 - landed after TASK-0064 merged

- TASK-0064 merged (`main` at 14628e6) and its checkpoint finalized; the
  canonical checkout is clean with one worktree.
- Restored the held EXP-031 bundle from `C:\work\scratch\hold-EXP-031\` (20
  experiment files + 3 scripts + 2 tests) and the task file; verified the file
  count matches the hold and nothing is gitignored.
- Added the bounded free-tier Colab T4 compute exception to `AGENTS.md`
  (task-scoped, repo never cloned to the VM, gold-free requests only, offline
  scoring, no ssh/console/repl/auth/Drive mount, one session, always
  `colab stop`, no tunnels/proxies, never upload/commit/print a token).
- `experiment.yaml`: `status: completed`, `code_commit:
  pending_task_checkpoint` (the landing SHA is not knowable pre-commit; no
  `code_commit` key is retrofitted into `results.json`).
- Regenerated the run telemetry ledger: 155 records, `--check` green; EXP-031
  contributes one experiment-scope record.
- EXP-031 is not added to the paper-prose number-provenance source list and the
  paper is not modified by this task (deferred: fold the new arms in as a new
  experiment, never retarget EXP-029's frozen tables).

## Handoff

Next atomic action: run the local gates (workspace policy, Ruff, mypy, pytest,
telemetry `--check`), publish this checkpoint with
`scripts/publish_checkpoint.py` against issue #83, and after it merges finalize
and close the issue.
