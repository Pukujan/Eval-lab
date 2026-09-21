# Current Repository Checkpoint

## Authoritative status

TASK-0001 through TASK-0011 are complete in the current release line. TASK-0012 is
complete in its dedicated independent Jev worktree. TASK-0015 is active in a fresh
worktree for the matched Grok/Luna/Qwen Flash comparison; EXP-014 remains immutable.

## Program state

TASK-0001 local bootstrap is complete.
TASK-0002 through TASK-0009 implementation is merged; TASK-0009 merged in PR #24. TASK-0010 acceptance is complete in the EXP-20260920-012 completion replay and pushed branch.

The program is extended with TASK-0007 through TASK-0009 to fully use the user's existing model subscriptions/resources after the measurement foundation is complete.

## Main objective

TASK-0009 and TASK-0010 selective escalation/research release are complete. TASK-0011 has completed Qwen results across additional objective datasets and blind holdouts. TASK-0012 is now frozen for an independent Jev benchmark.

## Model-access decisions

- Jev baseline uses exact model id `jev-1.13-free`; no automatic paid fallback.
- Qwen3.8 Flash authoritative automated path is YOLO-Auto:
  - base URL `https://yolo-auto.com/v1`
  - model `qwen3.8-flash`
  - environment variable `YOLO_AUTO_API_KEY`
  - user reports the credential is already configured locally
- Grok Build is used only through the direct authenticated xAI `grok` CLI.
- ChatGPT Luna/Sol are used only through the direct authenticated Codex subscription CLI.
- OpenCode and OpenRouter are excluded from TASK-0015.

## Next task

TASK-0015 is active in `D:/claude/eval-lab-TASK-0015-bakeoff`. Its new EXP-015
preregistration uses the exact EXP-014 pool and typed System-One packet. Core arms are
Grok Build through the direct authenticated xAI `grok` CLI, Luna through the direct
authenticated Codex/ChatGPT subscription, and YOLO-Auto `qwen3.8-flash`; exact
surfaced model IDs and provider failures must be recorded separately. Do not modify or
overwrite EXP-014.

## Queued foundation

- TASK-0003 — Jev Free Baseline (#7)
- TASK-0004 — Metrics and Calibration (#8)
- TASK-0005 — ARC-Challenge Adapter (#9)
- TASK-0006 — Lightweight Local Judge (#10)

## Queued extension

- TASK-0007 — External Judge and Teacher Bakeoff (#12)
- TASK-0008 — Verified Teacher Hard Negatives (#13)
- TASK-0009 — Small Judge Training and Calibration Pilot (#14)

### 2026-09-20 — TASK-0009 start

TASK-0008 is merged in PR #23 at `bce665e8601686a860d14c4ed5671b33afa660ef`. TASK-0009 is active in `D:/claude/eval-lab-TASK-0009` on branch `task/TASK-0009-small-judge-training`.

Scope is frozen to a compact TF-IDF plus logistic-regression single-answer correctness student. The pilot will run objective-only, criterion-augmentation, verified-hard-negative, and combined training arms; select from dev metrics; fit post-hoc temperature calibration on calibration records only; and keep test/OOD labels frozen until the final run.

Planned files: `src/eval_lab/training.py`, `scripts/run_small_judge_training.py`, `tests/test_training.py`, EXP-008 artifacts, the task log, and this checkpoint log.

Next atomic action: commit the completed EXP-008 evidence and checkpoint, push TASK-0009, and open its review PR. Do not begin a dependent task before TASK-0009 is accepted and merged.

### 2026-09-20 — TASK-0009 local completion

EXP-008 completed after its pre-registration freeze. The compact TF-IDF plus logistic-regression student ran arms A-D; arm D was selected on dev NLL/accuracy only, and arm E was calibrated on six calibration records only. The frozen test slice contains 12 records across 4 source families; arm D reached `0.6667` accuracy and `0.6250` balanced accuracy. Calibration and its small-sample regression are retained in the report.

Local gate: `python scripts/check_repo_contract.py` -> `Repository contract OK`; `ruff check .` -> `All checks passed!`; `PYTHONPATH=src python -m pytest -q` -> `64 passed in 5.43s`. No credentials, `.env` files, model weights, or caches were committed.

Files changed: `src/eval_lab/training.py`, `scripts/run_small_judge_training.py`, `tests/test_training.py`, EXP-008 artifacts, TASK-0009 log, and this checkpoint log. No source-family leakage was detected; test labels were not used in fitting, selection, or calibration.

Next atomic action: commit the final TASK-0009 checkpoint, push the branch, open its review PR, and wait for acceptance/merge before any dependent task.

### 2026-09-20 — TASK-0009 merge checkpoint

PR #24 (`https://github.com/Pukujan/Eval-lab/pull/24`) merged TASK-0009 into `main` at `286731c035ea2149a98a64e4877ce2d768893631` on 2026-09-20 20:15:01 UTC. Local acceptance remained green: contract `OK`, Ruff clean, `64 passed in 4.35s`, and `git diff --check` clean. CI runs `35534868582` and `35534871113` reported the account Actions budget before workflow steps; the 3.12 jobs were cancelled.

Environment: Windows PowerShell; Python `3.12.10`; Git `2.51.2.windows.1`; Node `v24.14.1`; OpenCode CLI `1.18.31`. No secrets were printed or committed.

Files changed: `src/eval_lab/training.py`, `scripts/run_small_judge_training.py`, `tests/test_training.py`, EXP-008 artifacts, the TASK-0009 log, and this checkpoint log. No dependent task is queued.

Next atomic action: fast-forward the original `D:/claude/eval-lab` checkout to `286731c035ea2149a98a64e4877ce2d768893631`, cherry-pick this checkpoint, and push `main`.

### 2026-09-20 — TASK-0009 review handoff

TASK-0009 is pushed in PR [#24](https://github.com/Pukujan/Eval-lab/pull/24) at commit `1924c0ef8d16e23366067f547ec6001ca5339932`. Local validation is green: contract `OK`, Ruff clean, `64 passed in 4.35s`, and `git diff --check` clean. CI runs `35534868582` and `35534871113` failed before workflow steps because the account Actions budget prevented use; 3.12 matrix jobs were cancelled. No repository CI result was produced.

Next atomic action: merge PR #24, record its merge checkpoint, fast-forward the original `main` checkout, and push that checkpoint. Do not begin a dependent task.

### 2026-09-20 — TASK-0009 implementation and EXP-008 pre-registration

The compact TF-IDF plus logistic-regression student, leakage-safe arm builder, JSON artifacts, metrics runner, and unit tests are implemented. EXP-008 pre-registration is frozen at `experiments/EXP-20260920-008-small-judge-training/` with code commit `2e3e244eeb856f7cfce2d4047f8357f0b19d1c91`; no final test evaluation occurred before the freeze. Targeted tests pass: `4 passed in 4.84s`.

Next atomic action: execute EXP-008 after the pre-registration commit, then run the full local merge gate and record results before review.
- TASK-0009 — Small Judge Training Pilot (#14)

## External conditions

Jev may remain rate-limited; this is an execution state and does not block the rest of the program.

GitHub Actions runner scheduling remains infrastructure-only until runners are assigned; local validation remains authoritative.

### 2026-09-21 — TASK-0015 opened

TASK-0012 independent Jev benchmark acceptance is complete at commit `56bad5d`. A
separate TASK-0015 worktree was created at `D:/claude/eval-lab-TASK-0015-bakeoff` on
branch `task/TASK-0015-grok-luna-qwen-bakeoff`. EXP-015 is preregistered to copy the
exact 1,408-record EXP-014 pool and typed packet before any final provider labels.

Next atomic action: commit the direct-only route correction and offline runner/validator,
then run fresh one-record smoke tests for direct Grok Build CLI, direct Codex Luna, and
Qwen Flash in a new output directory. Preserve surfaced model IDs and provider statuses.

### 2026-09-21 — TASK-0015 direct-only route correction

The active TASK-0015 route is now explicitly direct-only: Grok uses the authenticated
xAI `grok` Build CLI; Luna and optional Sol use the authenticated Codex CLI with the
ChatGPT subscription; Qwen remains YOLO-Auto `qwen3.8-flash`. OpenCode and OpenRouter
are excluded from this experiment and are not valid fallbacks.

Completed: rewired the runner, pool manifest, freeze script, experiment manifest, plan,
README, task log, and active checkpoint to the direct routes. The earlier committed
non-primary preflight output remains historical evidence and will not be reused or
overwritten; the new smoke output must use `runs/smoke-direct-20260921/`.

Direct route checks already passed without exposing credentials: `grok models` showed
the authenticated xAI session with default `grok-4.6`; `codex doctor` showed ChatGPT
authentication with configured `gpt-5.6-luna`; a headless direct Grok probe surfaced
`grok-4.6-build`; and a headless direct Codex Luna probe returned the requested JSON
label through `codex exec`.

Files changed: direct route runner and freeze script; EXP-015 plan, README, manifest,
pool manifest, and checksums; TASK-0015; and this checkpoint.

Next atomic action: run the fresh direct-only smoke, validate it, then commit that
smoke artifact before attempting the matched public or blind pool.

### 2026-09-21 — direct-only route smoke passed

The first direct-only Grok invocation reached xAI but produced a parse error because
the Build CLI's default agent behavior used multiple workspace-inspection turns. No
alternate provider was tried. The runner was tightened using the direct CLI's native
JSON schema constraint, verbatim prompt mode, web-search disablement, and one-turn cap.

Fresh smoke command: `PYTHONPATH=src python scripts/run_grok_luna_qwen_bakeoff.py
--partition public_selection --limit 1 --models grok,luna,qwen_flash
--output experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/runs/smoke-direct-tight-20260921
--timeout 120 --env-file C:\Users\pujan\OneDrive\Desktop\configs\.env`.

Result: Grok direct xAI Build `ok: 1`, surfaced model `grok-4.6-build`; direct Codex
Luna `ok: 1`; YOLO-Auto Qwen Flash `ok: 1`. The validator passed and the normalized
artifact is retained under `runs/smoke-direct-tight-20260921/`. No raw provider
transcript or credential was written.

Files changed: the direct Grok invocation hardening and the two direct-only smoke
artifacts. Next atomic action: commit this checkpoint, then decide whether to proceed
with the public matched pool before the blind holdout.

### 2026-09-21 — TASK-0015 public execution in progress

The frozen `public_selection` partition is active in the existing process; the blind
holdout has not been requested. Exact command:

`$env:PYTHONPATH='src'; python scripts/run_grok_luna_qwen_bakeoff.py --partition
public_selection --models grok,luna,qwen_flash --workers 4 --timeout 120 --env-file
C:\Users\pujan\OneDrive\Desktop\configs\.env --output
experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/runs/public-direct-20260921`.

The direct Grok Build arm is first and is cycling records under the per-record timeout;
the runner has not yet written its normalized arm artifact. No OpenCode or OpenRouter
command is part of this process. Next atomic action: wait for the public run to
terminate, validate checksums/statuses/metrics, and checkpoint the result before any
blind-holdout execution.

### 2026-09-21 — TASK-0015 parallel streaming checkpoint

The old sequential, non-streaming public attempt was terminated before it wrote
normalized predictions. TASK-0015 now has a fresh, validated streaming runner:
parallel isolated direct xAI Grok CLI sessions use `grok-streaming-json` and unique
leader sockets; direct Codex Luna/Sol sessions consume `codex-jsonl`; and YOLO-Auto
Qwen Flash consumes OpenAI SSE. Each completed record is immediately checkpointed to
the arm JSONL and progress JSON, while final normalized order remains frozen-pool
order. No OpenCode or OpenRouter route is active.

Fresh combined smoke `runs/smoke-stream-all-20260921/` validated Grok `ok: 1` with
surfaced `grok-4.6-build`, Luna `ok: 1` with requested `gpt-5.6-luna`, and Qwen
`ok: 1` with `qwen3.8-flash`; validator passed. Focused tests are `6 passed` and
Ruff is clean.

Next atomic action: commit this runner/smoke checkpoint, then launch the fresh
parallel public-selection run with four workers. Keep the blind holdout untouched
until public outputs are complete and validated.

### 2026-09-21 — TASK-0015 fresh parallel public execution

The new public run is live at
`experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/runs/public-stream-parallel-20260921`.
It uses the direct xAI `grok` CLI, direct Codex subscription CLI, and YOLO-Auto Qwen
routes only, with four concurrent workers per arm and streaming enabled. The Grok
progress checkpoint reached `11/648` records, all `ok`, with four direct xAI child
sessions observed. Luna and Qwen have not started because the runner preserves arm
boundaries; the blind holdout remains untouched.

Next atomic action: monitor the live per-arm progress JSON, validate the completed
public artifact, and only then decide whether to request the blind holdout.

### 2026-09-21 — TASK-0015 paused for organized worktree move

The user requested a pause and relocation of the active work. The public provider
process was stopped with its partial output preserved: Grok `648/648` (`643 ok`, `5
provider_error`), Luna `532/648` (`532 ok`), and Qwen not started. The active run has
no final result artifact yet, so its per-arm prediction/progress files are the
authoritative resume checkpoints.

The runner now supports `--resume`: it validates checkpoint IDs, skips completed
records, appends only missing records, and finalizes the same run directory after all
arms complete. The worktree will be moved to
`D:\claude\eval-lab\.worktrees\TASK-0015-bakeoff`; no EXP-014 files or blind labels
will be changed.

Next atomic action: move and verify the registered worktree, then resume the public
run from the organized path with `--resume`.

### 2026-09-21 — TASK-0015 worktree consolidation complete

All 18 registered Eval Lab worktrees are now contained under
`D:\claude\eval-lab\.worktrees`; the old `D:\claude\eval-lab-TASK-*` and PR sibling
paths are gone. The active TASK-0015 branch remains
`task/TASK-0015-grok-luna-qwen-bakeoff` at
`D:\claude\eval-lab\.worktrees\TASK-0015-bakeoff`. The paused public checkpoints
are preserved: Grok `648/648`, Luna `532/648`, Qwen not started.

Next atomic action: resume the existing public run from the organized worktree with
`--resume --workers 4`; do not request blind-holdout records until public validation
passes.

### 2026-09-21 — TASK-0015 resumed from organized path

The resumable public run is live from
`D:\claude\eval-lab\.worktrees\TASK-0015-bakeoff`. It skipped Grok’s completed
`648/648` checkpoint, reused Luna’s `532` existing records, and has advanced Luna to
`539/648` with four direct `codex-jsonl` streaming sessions. Qwen has not started;
the blind holdout remains untouched.

Next atomic action: monitor the resumed Luna checkpoint, then run and validate Qwen
and the finalized public artifact from the same organized worktree.

## Next atomic action

TASK-0010 is complete at EXP-20260920-012. Leave the next program task unopened until review/triage. Historical checkpoint entries below are retained.

### 2026-09-20 — PR #15 contract validation

PR #15 initially failed the local planning contract because `tasks/TASK-0009-small-judge-training.md` lacked the required `## Outputs` heading. Added the missing task outputs without changing the program scope.

After the correction, rerun the local merge gate on the PR branch:

- `.venv\Scripts\python.exe scripts/check_repo_contract.py`
- `.venv\Scripts\ruff.exe check .`
- `.venv\Scripts\python.exe -m pytest -q`

- `.venv\Scripts\python.exe scripts/check_repo_contract.py` -> `Repository contract OK`.
- `.venv\Scripts\ruff.exe check .` -> `All checks passed!`.
- `.venv\Scripts\python.exe -m pytest -q` -> `11 passed in 1.89s`.

Decision: PR #15 is accepted and merged at `de294e10eb10e926c8ed18e7ffeba893ff7c1cf5`; its provider-access rules are now part of the current main state. The known no-runner CI condition remains infrastructure-only.

### 2026-09-20 — TASK-0002 implementation checkpoint

TASK-0002 implementation was checkpointed in commit `7f89439` before PR #15 was merged, then rebased onto the accepted main. Its pre-rebase local gate recorded `Repository contract OK`, `All checks passed!`, and `27 passed in 1.25s`; the deterministic export produced 24 sources and 120 records (72 single, 48 pairwise) with fingerprint `03cd497da246c641f84a89fd74380e1f340c327eab7850e0476b8379a7a1052c`.

TASK-0002 final local acceptance is green: repository contract `OK`, Ruff clean, and `29 passed`. The deterministic export reproduced 24 sources and 120 records (72 single, 48 pairwise) with fingerprint `03cd497da246c641f84a89fd74380e1f340c327eab7850e0476b8379a7a1052c`.

TASK-0002 is pushed in PR #16 (`https://github.com/Pukujan/Eval-lab/pull/16`) from commit `bae7955`.

PR #16 merged TASK-0002 into `main` at `1498581774ad5c7c4291f4e1dc68e58547d4126f`. TASK-0003 is active in `D:\claude\eval-lab-TASK-0003` on `task/TASK-0003-jev-objective-baseline`.

Next atomic action: implement the exact free Jev model contract and normalized provider-status handling.

TASK-0003 final local acceptance is green: repository contract `OK`, Ruff clean, and `37 passed`. The optional live smoke reached OpenCode and was normalized as `rate_limited` with `Retry-After 24496` seconds; no label was fabricated.

Next atomic action: commit and push TASK-0003, open its PR, and do not start TASK-0004 until TASK-0003 is accepted/merged.

TASK-0003 is pushed in PR #17 (`https://github.com/Pukujan/Eval-lab/pull/17`) from commit `a260259`.

PR #17 merged TASK-0003 into `main` at `a5cfc7982b5babd8dac73ba775276d95db0fd9e8`. TASK-0004 is active in `D:\claude\eval-lab-TASK-0004` on `task/TASK-0004-metrics-calibration`.

TASK-0004 local implementation and validation are complete in `D:\claude\eval-lab-TASK-0004` on `task/TASK-0004-metrics-calibration`.

Local gate: contract `OK`; Ruff clean; `47 passed in 0.78s` using Python `3.12.10` in the dedicated `.venv`.

TASK-0004 is pushed in PR [#18](https://github.com/Pukujan/Eval-lab/pull/18) at commit `a428c75a1dfd23887050c8891737f041833f061a`.

PR #18 merged TASK-0004 into `main` at `ec083499e8ce77c8cf2cf0614b05265ead24dd93`. TASK-0005 is active in `D:\claude\eval-lab-TASK-0005` on `task/TASK-0005-public-benchmark`.

TASK-0005 local implementation and validation are complete. Live source revision `210d026faf9955653af8916fad021475a3f00453` and slice fingerprint `b7a84b15c5ca352f2689f546721d8038ce9b31ecff711be606016a6996e05521` are recorded.

Local gate: contract `OK`; Ruff clean; `52 passed in 0.77s` using Python `3.12.10`.

PR #19 merged TASK-0005 into `main` at `644202fbdd49a3735775ae1c55d1e621de1044d6`. TASK-0006 is active in `D:\claude\eval-lab-TASK-0006` on `task/TASK-0006-lightweight-local-baseline`.

TASK-0006 local implementation and validation are complete. Qwen3-0.6B produced 20/20 normalized predictions on the committed synthetic/ARC slice; the calibrated follow-up improved held-out NLL, Brier, and ECE using separate calibration records.

Local gate: contract `OK`; Ruff clean; `55 passed in 0.55s` using Python `3.12.10`.

Commit `6452bc8` records the calibrated experiment outputs, `b0202e2` records the final local gate, and `cf50421` records the review PR. TASK-0006 is pushed in PR [#21](https://github.com/Pukujan/Eval-lab/pull/21), merged into `main` at `6cde993b91a7daca1b51bd8615d38538e80c9f71`. Its jobs were blocked before workflow steps because the GitHub Actions budget prevented further use; the 3.12 jobs were cancelled as a matrix consequence. Local validation remains green.

Next atomic action: update local `main` to the merge commit, then create the TASK-0007 worktree. Do not begin TASK-0007 before this main checkout update is complete.
TASK-0005 is pushed in PR [#19](https://github.com/Pukujan/Eval-lab/pull/19) at commit `d8f038d1725ffcc1121bc0381ae6cabad2e4136b`.

Next atomic action: merge PR #19 after the local merge gate, update local `main`, and only then create the TASK-0006 worktree.

### 2026-09-20 — TASK-0006 merge checkpoint

PR #21 merged TASK-0006 into `main` at `6cde993b91a7daca1b51bd8615d38538e80c9f71`. Local acceptance criteria are satisfied with repository contract `OK`, Ruff clean, and `55 passed in 0.55s`. GitHub Actions reported that the job was not started because an Actions budget prevented further use; the 3.12 matrix jobs were cancelled after the 3.11 budget failure. No workflow step ran.

Files changed for TASK-0006 are committed on the task branch and included in the merged PR: Qwen judge adapter, runner, tests, raw/calibrated experiment artifacts, task log, and checkpoint log. No credentials, `.env` files, model weights, or caches were committed.

Next atomic action: fast-forward the local `main` checkout to `6cde993b91a7daca1b51bd8615d38538e80c9f71`, then create the dedicated TASK-0007 worktree.

### 2026-09-20 — TASK-0007 local completion

TASK-0007 completed its provider census and frozen 20-record bakeoff. YOLO-Auto exposed and executed exact model qwen3.8-flash with 20/20 normalized predictions and accuracy 0.60. OpenCode free models nemotron-3.5-lightning-free and mimo-v2.5-free, plus surfaced opencode/grok-4.6, were attempted and recorded as one bounded timeout plus 19 skipped records per arm. Luna and Sol deterministic audit batches contain 10 records each. Jev remains unavailable because its prior live provider call was rate-limited.

Local gate: repository contract OK; Ruff clean; 57 passed in 0.99s. No .env, credentials, model weights, or caches were committed. GitHub Actions remains subject to the known account budget/no-runner condition.

Next atomic action: commit the checkpoint, push TASK-0007, open its review PR, and do not start TASK-0008 until TASK-0007 is accepted and merged.


### 2026-09-20 — TASK-0007 review handoff

TASK-0007 is pushed in PR #22 at commit f1f4c1cfa3c866d6e04f271d4c3339ad5dbb7b35. Local acceptance is green: contract OK, Ruff clean, 57 passed in 0.99s.

Next atomic action: merge PR #22 after the local merge gate, update local main, and only then create the TASK-0008 worktree. Do not start TASK-0008 until TASK-0007 is accepted and merged.

### 2026-09-20 — TASK-0007 merge checkpoint

PR #22 merged TASK-0007 into main at 1ecd5be35c2315ec927b35301c10aa48b8669371. Local acceptance is green: contract OK, Ruff clean, 57 passed in 0.99s. GitHub Actions again reported the external account budget condition before workflow steps.

Next atomic action: fast-forward the local main checkout to 1ecd5be35c2315ec927b35301c10aa48b8669371, then create the dedicated TASK-0008 worktree. Do not start TASK-0008 before this main checkout update is complete.

### 2026-09-20 — TASK-0008 local completion

TASK-0008 produced EXP-20260920-007 with 5 independently verified YOLO-Auto hard negatives from 20 non-test source families, preserving train/dev/calibration splits and excluding test sources. Luna completed 10 audit records and Sol completed 10 hardest-case records through one-record OpenCode requests. The earlier EXP-004 run with 18 verified candidates is retained as an append-only initial run.

Local gate: repository contract OK; Ruff clean; 60 passed in 1.60s. Provider timeouts are recorded separately from verifier outcomes. No credentials, .env files, or private data were committed.

Next atomic action: commit the review checkpoint, push TASK-0008, open its review PR, and do not start TASK-0009 until TASK-0008 is accepted and merged.

### 2026-09-20 — TASK-0008 merge checkpoint

PR #23 (`https://github.com/Pukujan/Eval-lab/pull/23`) merged TASK-0008 into `main` at `bce665e8601686a860d14c4ed5671b33afa660ef` on 2026-09-20 19:59:24 UTC. Local acceptance was green: `python scripts/check_contract.py` returned `Repository contract OK`, `ruff check .` returned clean, and `pytest -q` returned `60 passed in 1.60s`. GitHub Actions still reported the external account Actions budget/no-runner condition before any workflow step.

Environment: Windows PowerShell; Python 3.12.10; Git 2.51.2.windows.1; Node v24.14.1; OpenCode CLI 1.18.31. No secrets were printed or committed.

Files changed: `scripts/generate_hard_negatives.py`, `tests/test_hard_negatives.py`, EXP-004 and EXP-007 experiment artifacts, the TASK-0008 log, and this checkpoint log. Decisions and blockers are recorded in the task log. The final corpus contains 5 independently verified hard negatives, 10 Luna audits, 10 Sol audits, and explicit rejected/timeout/provider-blocked states.

Next atomic action: fast-forward `D:/claude/eval-lab` to `bce665e8601686a860d14c4ed5671b33afa660ef`, cherry-pick the post-merge checkpoint commit, push `main`, then create the TASK-0009 worktree. Do not start TASK-0009 before that update is complete.

### 2026-09-20 — TASK-0010 activation

TASK-0010 issue #25 is active on branch `task/TASK-0010-selective-escalation`, starting from main `6ae355f470d905f8fd8c85363a353674818b19f9`.

Primary student is the frozen TASK-0009 TF-IDF + logistic-regression arm D. The task adds selective escalation, pinned OpenRouter Jev, YOLO-Auto Qwen3.8 Flash differential evaluation, explicit metamorphic/differential tests, and a publication-quality research release.

Publication target:
- benchmark: EvalLab-Select v0.1.0
- paper: arXiv-ready LaTeX source
- provenance: RO-Crate 1.3 + PROV-O
- validation: stable SHACL Recommendation
- citation/deposit readiness: CFF 1.2.0 + DataCite 4.6-compatible metadata

PCM inspection is pinned to `Pukujan/project-continuity-modules@3a34b4a73842c824de5359f06e04568e8ce4aaa4`. PCM is a continuity compatibility reference; its research profile is not yet implemented in the inspected templates, so TASK-0010 does not depend on it.

Next atomic action: local Luna checks out TASK-0010, runs the planning merge gate, freezes the larger benchmark/split manifest and EXP-009 preregistration, then implements offline routing/metamorphic/differential tests before live final evaluation.

### 2026-09-20 — TASK-0010 frozen release and local evaluation

TASK-0010 is active in `D:/claude/eval-lab-TASK-0010` on `task/TASK-0010-selective-escalation`. Environment: Windows-11-10.0.26200-SP0, PowerShell, Python 3.12.10, Git 2.51.2.windows.1, Node v24.14.1. Freeze commit: `169a15d23a38db5c1246bde36db082e383467fe7`; implementation commit: `1aace02f6e5b7e9f1b0403c6ffbfe7b2ce27dbd6`.

EvalLab-Select v0.1.0 is frozen at fingerprint `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`, ARC revision `210d026faf9955653af8916fad021475a3f00453`, canonicalization `eval-lab-select-single-v1`, with `2,863` threshold-selection records from `1,427` source families and `2,356` final-evaluation records from `1,176` disjoint source families. The primary student is the frozen TASK-0009 TF-IDF/logistic arm D, restored from committed JSON.

Local evidence: repository contract `OK`; Ruff clean; full pytest `74 passed in 6.35s`; research-artifact validation reports checksums `ok`, RO-Crate `ok`, PROV-O parsed, SHACL conforms, CFF parsed, and paper present. Provider smoke command with ignored local `.env` returned `ok` for pinned `typesafe/jev-1.13`, rolling `~typesafe/jev-latest`, and YOLO-Auto `qwen3.8-flash`. Pinned bulk final subset returned `500/500 ok`; Qwen bulk did not finish and rolling is retained smoke-only. OpenCode Jev smoke was rate-limited.

CI diagnosis after local validation: run `35537436072` jobs `106148870777` and `106148870984` failed before steps, with `runner_id: 0`, empty runner name, `ubuntu-latest` label, and no logs. This is an external GitHub runner/account startup condition, not a local contract/test failure.

Files include the provider-independent routing core, selective benchmark/release, frozen arm-D artifact, provider adapters/runners, offline tests, EXP-009 results and smoke/differential outputs, RO-Crate 1.3/PROV-O/SHACL/DataCite artifacts, valid CFF, generated paper tables/figure, completed paper, reproducibility appendix, and limitations. `.env` is ignored; no credential values were printed or committed.

Decision: keep TASK-0010 active with `completed_with_provider_statuses` because the required Qwen/rolling bulk final labels are unresolved. Next atomic action: commit and push this checkpoint, then retry only the missing provider arms or record a provider-blocked acceptance checkpoint; do not begin TASK-0002.

### 2026-09-20 — CI collection defect

The new push reached CI steps. Runs `35541435860` and `35541433231` passed repository contract and Ruff, then pytest collection failed because the clean environment could not import `scripts` (`ModuleNotFoundError` in four existing test modules). Added `scripts/__init__.py` as the minimal package marker. Local validation after the fix: contract `OK`, Ruff clean, `74 passed in 30.51s`, and clean diff check.

Next atomic action: commit/push the CI package-marker fix and inspect the resulting CI run; retain the provider bulk blocker and do not begin TASK-0002.

### 2026-09-20 — TASK-0010 planning gate

TASK-0010 worktree `D:/claude/eval-lab-TASK-0010` is on `task/TASK-0010-selective-escalation` at expected head `50312637a28a71e279387db6293f17b99a11ed10`. The required contract and Ruff checks pass. The shared editable environment pointed at TASK-0006, so pytest was rerun with the current worktree source path and returned `65 passed in 25.36s`. No planning-contract defect was found.

Next atomic action: implement offline typed-question/routing, benchmark construction, and metamorphic/differential tests before any final evaluation labels or provider-scale run.

### 2026-09-20 — CI collection defect diagnosed

After commit `fb804569e841459671961f6cac9f8779219f3203` was pushed, CI runs `35541435860` and `35541433231` reached workflow steps. Contract and Ruff passed, but pytest collection failed on Python 3.12 because four existing test modules could not import `scripts` in the clean GitHub environment (`ModuleNotFoundError`). This was a real packaging defect masked by the local checkout path.

Fix: add the minimal `scripts/__init__.py` package marker. Local rerun returned contract `OK`, Ruff clean, `74 passed in 30.51s`, and clean `git diff --check`. No project scope or experiment semantics changed.

Next atomic action: commit and push the CI import fix, then inspect the new CI run. Keep TASK-0010 active until the provider acceptance blocker and the resulting CI run are resolved.

### 2026-09-20 — CI test invocation defect diagnosed

Duplicate CI runs `35541679787` and `35541681635` checked out `f65512b36132cb9a94c5fd5d420e486350410473`, completed installation, repository contract, and Ruff, then both Python 3.11 and 3.12 test jobs failed during collection because standalone `pytest -q` could not import `scripts`. Change `.github/workflows/ci.yml` to `python -m pytest -q`, preserving the repository test contract. Local validation: repository contract `OK`, Ruff clean, `74 passed in 31.38s`, and clean diff check.

Next atomic action: commit/push the workflow fix and inspect the fresh CI matrix; retain the provider bulk blocker and do not begin TASK-0002.

### 2026-09-20 — CI benchmark checksum defect diagnosed

Fresh CI runs `35541979823` and `35541981648` reached the test suite after the `python -m pytest` fix. Both failed one checksum assertion because the frozen benchmark checksum was based on Windows CRLF bytes while GitHub checked out LF bytes. Added `.gitattributes` to enforce LF for `benchmark/eval-lab-select-v0.1.0/*`, normalized the release files, and regenerated `checksums.sha256` from canonical LF bytes. Local contract/Ruff/full pytest are green (`74 passed in 25.63s`), and research-artifact validation reports checksums `ok`, RO-Crate `ok`, PROV-O parsed, SHACL conforms, CFF parsed, and paper present.

Next atomic action: commit/push the byte-stability fix and inspect the fresh CI matrix; retain the provider bulk blocker and do not begin TASK-0002.

### 2026-09-20 — CI green checkpoint

Commit `88ec75e184739cfc84ba9ccbacc5827a6da117a6` is pushed. CI runs `35542193123` (push) and `35542195848` (pull request) passed on Python 3.11 and 3.12, including installation, repository contract, Ruff, and `python -m pytest -q`. The workflow and benchmark byte-stability defects are resolved in the clean GitHub environment.

Next atomic action: retry only the missing Qwen and rolling provider arms against the frozen final-evaluation order, preserving separate output files and explicit failures; retain TASK-0010 active and do not begin TASK-0002.

### 2026-09-20 — Qwen contention checkpoint

The required YOLO-Auto provider/model remains `qwen3.8-flash`; Grok 4.6 cannot substitute for it. A 500-record Qwen attempt with 16 workers and 30-second timeout opened 16 HTTPS connections but made no batch progress after approximately six minutes and was terminated without labels. A separate ten-record probe with 8 workers and 12-second timeout returned `10 provider_error`. The pinned Jev output was preserved; rolling and Qwen remain separate unresolved arms. No credentials or raw payloads were printed or committed.

Next atomic action: retry only the Qwen arm during a stable YOLO-Auto window, then regenerate results/artifacts from its separate normalized output; keep TASK-0010 active and do not begin TASK-0002.

### 2026-09-20 — rolling Jev bulk checkpoint

Rolling Jev was run separately with 4 workers, provider limit `500`, and 12-second timeout. Model `~typesafe/jev-latest` returned `500 ok`; pinned `typesafe/jev-1.13` remains a separate `500 ok` arm. `provider-rolling.jsonl` and `provider-pinned.jsonl` remain separate, with no pooled pinned/rolling estimate. Research artifacts were regenerated, benchmark release bytes were canonicalized to LF, and artifact validation returned checksums `ok`, RO-Crate `ok`, PROV-O parsed, SHACL conforms, CFF parsed, and paper present. Qwen remains unresolved with no final labels; the System-One smoke differential remains `1/1` comparable and agreeing.

Next atomic action: commit the rolling output/results and checkpoint, then retry Qwen only after YOLO-Auto contention clears; do not substitute Grok or begin TASK-0002.

### 2026-09-20 — Qwen availability recheck

A fresh three-record YOLO-Auto probe for `qwen3.8-flash` with 2 workers and 20-second timeout returned `3 provider_error`; no labels or raw payloads were written. This remains an external provider availability condition. The frozen TASK-0010 arm set is unchanged. Grok/Luna and local Qwen 1.7B/4B remain candidates for a separately preregistered follow-up after TASK-0010 acceptance or explicit provider-blocking; TASK-0006’s local Qwen3-0.6B remains the existing broader-program baseline.

Next atomic action: retry Qwen only after provider contention changes; retain TASK-0010 active and do not expand the current experiment or begin TASK-0002.

### 2026-09-20 — current handoff checkpoint

Current head `cea7558568bafad4791353f53f7b8ad5286feacd` is pushed on the TASK-0010 branch. CI run `35543153294` passed Python 3.11 and 3.12 with install, contract, Ruff, and tests. EvalLab-Select v0.1.0 remains frozen at fingerprint `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`; counts are `2,863` threshold-selection and `2,356` final-evaluation. Pinned Jev is `500 ok`, rolling Jev is a separate `500 ok`, and YOLO-Auto Qwen has no final labels after repeated provider-error/stall evidence. No local 1.7B/4B weights were found in the standard Hugging Face cache.

Decision: keep TASK-0010 active with explicit provider statuses. Grok/Luna/local Qwen cannot replace the missing frozen Qwen arm; any such comparison requires a new experiment ID and provider manifest after acceptance or formal blocking.

Next atomic action: retry Qwen only after YOLO-Auto contention changes, or make the provider-blocked acceptance decision with the evidence already checkpointed; do not begin TASK-0002.

### 2026-09-20 — formal provider-blocked handoff

TASK-0010 is explicitly provider-blocked, not complete. The dedicated worktree lacks `.venv`; equivalent shared-environment validation passed repository contract, Ruff, `74 passed in 3.89s`, and diff check. Pinned Jev `typesafe/jev-1.13` is `500 ok`; rolling `~typesafe/jev-latest` is a separate `500 ok`; YOLO-Auto `qwen3.8-flash` at `https://yolo-auto.com/v1` has no final labels after a stalled 500-record attempt and repeated `provider_error`/latest `transport_error` probes. No fallback labels, credentials, or raw payloads were written.

Frozen benchmark remains fingerprint `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`, with `2,863` threshold and `2,356` final records. System-One smoke differential is `1/1` comparable and agreeing; artifact validation is green; CI run `35543153294` is green on Python 3.11/3.12.

Decision: preserve the frozen protocol. Grok/Luna/local Qwen 1.7B/4B cannot replace the missing Qwen arm and are deferred to a new experiment. Do not begin TASK-0002 or expand this branch.

Next atomic action: retry Qwen only after YOLO-Auto recovers, or obtain explicit acceptance of the provider-blocked release.

### 2026-09-20 — final CI verification for blocked handoff

The provider-blocked handoff is pushed at `afb74595e26084abc1975e2bd3c51553dbd1c8ba`. CI run `35543406626` passed Python 3.11 and 3.12 with install, repository contract, Ruff, and unit tests. The worktree is clean.

Next atomic action: wait for YOLO-Auto availability or obtain explicit provider-blocked acceptance; do not substitute a model or begin TASK-0002.

### 2026-09-20 — EXP-20260920-010 plan frozen before execution

User authorized a separate follow-up bakeoff while TASK-0010 remains explicitly provider-blocked. The durable plan is `experiments/EXP-20260920-010-multi-subscription-bakeoff/PLAN.md` with machine-readable `experiment.yaml`. It freezes the existing EvalLab-Select fingerprint, the deterministic 500-record final-evaluation prefix, the arm-D student, the typed System-One specification, and separate Grok 4.6, Luna, and Sol OpenCode subscription arms. YOLO Qwen and local Qwen 1.7B/4B are deferred and will not be silently substituted.

No new provider evaluation has started. Next atomic action: commit this plan, then implement and offline-test the subscription bakeoff runner/validator before any new provider call.

### 2026-09-20 — EXP-20260920-010 offline runner checkpoint

The plan is committed; the new runner/validator/tests are now implemented without provider calls. Targeted Ruff passes, targeted tests are `3 passed in 0.54s`, repository contract is `OK`, and diff check is clean. The runner uses the frozen 500-record final prefix and typed System-One v0.1.0, writes separate Grok/Luna/Sol outputs, and preserves unresolved failures. Qwen and local-weight arms remain deferred.

Next atomic action: commit the implementation, run the full offline gate, then perform a bounded subscription smoke before the 500-record arms.

### 2026-09-20 — provider-path diagnosis and OpenCode run stopped

EXP-010 was stopped before any final arm file was written after direct path checks showed the configured OpenCode route was not a subscription entitlement. `opencode --version` was `1.18.31`; the catalog exposed `opencode/grok-4.6`, `opencode-go/grok-4.6`, and `litellm/grok-4.6`. The explicit Go probe returned HTTP 403 requiring an active OpenCode Go subscription; the regular OpenCode Grok probe returned HTTP 402 insufficient account funds at `https://opencode.ai/zen/v1/responses`; LiteLLM returned a connection failure at `http://localhost:4000/v1/chat/completions`; no Grok CLI was installed. The running EXP-010 process was terminated before `predictions/grok.jsonl` existed. No credentials or raw prompts were printed.

Decision: preserve EXP-010’s plan and smoke/canary as separate route evidence, but do not claim its final evaluation. Use a new experiment ID for the available OpenRouter path.

### 2026-09-20 — EXP-20260920-011 OpenRouter provider-blocked result

Durable plan `experiments/EXP-20260920-011-openrouter-multi-subscription-bakeoff/PLAN.md` was committed before evaluation at `5e7df93`. The runner and offline streaming test are at `1d53b29`; the validator and 1-record smoke are at `d6d4ebb`; final normalized outputs are at `5277827`. OpenRouter model census returned HTTP 200 for `x-ai/grok-4.6`, `openai/gpt-5.6-luna`, and `openai/gpt-5.6-sol`. The smoke returned `1 ok` for each arm. The deterministic 500-record command with four workers returned Grok `368 ok/132 HTTP 402`, Luna `500 HTTP 402`, and Sol `500 HTTP 402`; the 402 errors identify account balance exhaustion. No fallback labels or credentials were written.

Local verification: repository contract `OK`, Ruff clean, `80 passed in 31.55s`, and research-artifact validation checksums `ok`, citation parsed, paper present, PROV-O parsed, RO-Crate `ok`, SHACL conforms. CI run `35546251591` passed for the preceding pushed head. The current head is `5277827` and must be pushed with this checkpoint.

Decision: retain the OpenRouter outputs as `completed_with_provider_statuses`, keep OpenCode Zen/Go and OpenRouter results separate, and do not retry the exhausted account. The Qwen streaming merged artifact is independently complete at `500 ok` under `EXP-20260920-009-selective-escalation/qwen-streaming-final-merged-20260920-010`.

Next atomic action: use the validated Qwen 500-label artifact to regenerate TASK-0010 selective-routing, matched-random, and differential results, then regenerate/check research artifacts and record exact metrics. Do not begin TASK-0002.

### 2026-09-20 — TASK-0010 acceptance complete

EXP-20260920-012 is the completed selective-routing release. Environment: `D:/claude/eval-lab-TASK-0010`, branch `task/TASK-0010-selective-escalation`, Windows PowerShell, Python 3.12.10 from `D:/claude/eval-lab/.venv`, with `PYTHONPATH=$PWD/src`; the dedicated worktree has no `.venv`. The equivalent shared-environment contract and Ruff checks passed, and the source-layout pytest command passed `80 tests`.

The exact replay command, generation command, checksum counts, artifact validator output, and file-level decisions are recorded in the TASK-0010 checkpoint log. Frozen fingerprint remains `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`, with `2,863` threshold-selection records and `2,356` final-evaluation records. The deterministic provider prefix is `500` records. Pinned `typesafe/jev-1.13`, rolling `~typesafe/jev-latest`, and YOLO-Auto `qwen3.8-flash` each have `500/500 ok`; pinned and rolling are separate. The Jev/Qwen differential is `500` comparable with `486` agreements, and the smoke differential is `1/1`.

EXP-012 contains `17` routing policies, matched random controls, Wilson intervals, provider call/latency/usage summaries, benchmark source manifest/splits/checksums, RO-Crate 1.3, PROV-O, SHACL, valid CFF, generated paper tables/figure, completed `paper/main.tex`, reproducibility commands, and limitations. Final local validation: repository contract `OK`; Ruff clean; `80 passed`; research-artifact validation checksums `ok`, citation `parsed`, paper `present`, PROV-O `parsed`, RO-Crate `ok`, SHACL `conforms`.

Decision: mark TASK-0010 complete. OpenRouter EXP-011 remains separate provider-status evidence with HTTP 402 account-funds failures; no credentials or raw responses were committed. Do not begin TASK-0002.

Next atomic action: commit and push the final checkpoint, then inspect CI for the pushed head.

### 2026-09-20 — final CI byte-stability fix

CI run `35555437302` for `282865e` passed contract and Ruff but failed unit tests on Python 3.11 and 3.12 because Windows-generated benchmark metadata had CRLF bytes while the committed checksum manifest was computed over the pre-normalized working bytes. The failing test was `test_benchmark_records_round_trip_and_checksums_are_current`; the mismatch was isolated to the generated benchmark metadata bytes, not the benchmark records or experiment logic.

All checksum-covered text files in the benchmark and EXP-012 were normalized to LF, and both manifests were regenerated from the exact bytes. Local validation now returns `80 passed`, contract `OK`, artifact checksums `ok`, CFF parsed, paper present, PROV-O parsed, RO-Crate `ok`, SHACL `conforms`, and clean diff check. TASK-0010 acceptance artifacts remain complete and TASK-0002 remains unopened.

Next atomic action: commit and push this byte-stability correction, then verify the replacement CI run.

### 2026-09-20 — replacement CI passed

The byte-stability correction is commit `81d3130`. Replacement CI run `35555646443` passed both Python 3.11 and 3.12, including install, repository contract, Ruff, and unit tests. TASK-0010 acceptance remains complete; TASK-0002 remains unopened.

Next atomic action: commit and push this final CI checkpoint, then verify the branch is clean and leave the repository at the completed TASK-0010 state.

### 2026-09-20 — TASK-0010 local metric and paper-schema improvement

Authoritative status: TASK-0001 through TASK-0009 merged; TASK-0010 is in corrective audit at EXP-20260920-012 with EXP-20260920-009 as the planned baseline. Local routing accounting, P1/P2 provider-only policies, required per-policy metrics, paper sections, and PCM notes were added without provider calls. Local gate: repository contract `OK`, Ruff clean, `87 passed`, research-artifact validation checksums `ok` / RO-Crate `ok` / SHACL `conforms`. The next program task remains unopened pending commit and CI verification.

### 2026-09-20 — TASK-0010 corrective audit checkpoint

Grok Build CLI `1.0.40 (eb1a2256660d)` was installed at `C:\Users\pujan\.grok\bin\grok.exe` and used through the authenticated xAI subscription route for a read-only audit followed by local offline edits. No OpenRouter/OpenCode provider call, credential read, `.env` change, commit, or push was made by that audit. The worktree is `D:\claude\eval-lab-TASK-0010` on `task/TASK-0010-selective-escalation`; Python is `3.12.10` from `D:\claude\eval-lab\.venv`; Git is `2.51.2.windows.1`; the expected remote head `50312637a28a71e279387db6293f17b99a11ed10` is an ancestor of the current local continuation.

The audit corrected local-route provider accounting, added explicit P1 `pinned_jev_only` and P2 `qwen_flash_only` policies across the full final pool, and added provider-independent per-policy metrics, uncertainty/support flags, provider-only latency/cost/resource reporting, risk coverage, aggregate/per-domain summaries, focused unit tests, and the required paper/report material. The frozen EXP-012 counts remain threshold-selection `2,863`, final evaluation `2,356`, provider prefix `500`; policy count is now `19`; pinned Jev is `500/500 ok`, rolling Jev is `500/500 ok` as a separate canary, Qwen is `500/500 ok`, and the Jev/Qwen differential is `500` comparable with `486` agreements. Collapsed operating points are labeled descriptive/underpowered where the confidence-supported sample is insufficient; no distinction was fabricated.

Exact local checks:

- `D:\claude\eval-lab\.venv\Scripts\python.exe scripts/check_repo_contract.py` -> `Repository contract OK`.
- `D:\claude\eval-lab\.venv\Scripts\ruff.exe check .` -> `All checks passed!`.
- `$env:PYTHONPATH=\"$PWD\\src\"; D:\claude\eval-lab\.venv\Scripts\python.exe -m pytest -q` -> `87 passed in 3.91s`.
- `$env:PYTHONPATH=\"$PWD\\src\"; D:\claude\eval-lab\.venv\Scripts\python.exe scripts/validate_research_artifacts.py --benchmark benchmark/eval-lab-select-v0.1.0` -> checksums `ok`, citation `parsed`, paper `present`, PROV-O `parsed`, RO-Crate `ok`, SHACL `conforms`.
- `git diff --check` -> clean after LF normalization and removal of the report trailing blank line.

Files changed are `checkpoints/CURRENT.md`, `tasks/TASK-0010-selective-escalation.md`, `scripts/run_selective_escalation.py`, `scripts/generate_research_artifacts.py`, `src/eval_lab/metrics/__init__.py`, new `src/eval_lab/metrics/policy.py`, new `tests/test_selective_policy_metrics.py`, EXP-012 derived results/report/routing/checksum files, and the generated paper/figure/table/limitations/reproducibility files. Benchmark records and frozen EXP-009 provider bytes were preserved. The benchmark fingerprint remains `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`.

Decision: keep the frozen TASK-0009 TF-IDF plus logistic-regression arm D as the primary student, retain pinned and rolling Jev as separate arms, retain Qwen as the secondary provider arm, and finish TASK-0010 from committed offline evidence without substituting Grok. No blocker remains in the local implementation; the next atomic action is to commit this audit, replay/regenerate from the committed code, push the branch, and inspect CI before restoring the task to complete. Do not begin TASK-0002.

### 2026-09-20 — TASK-0010 committed-code replay and local gate

The audited source changes are committed as `833e937` (`TASK-0010: add audited policy metrics and paper generation`), `6e8df8e` (`TASK-0010: normalize offline replay provider outputs`), and `ac220cc` (`TASK-0010: stabilize generated report ending`). The offline replay was then rerun from `ac220cc`; `results.json` records `environment.git_commit=ac220cccfbbe30e2927d94e062c08df22f6e1eee`. No provider call was made during this replay: the pinned Jev, rolling Jev, and Qwen JSONL inputs were the already committed EXP-009 artifacts.

Exact environment: Windows PowerShell, worktree `D:\claude\eval-lab-TASK-0010`, branch `task/TASK-0010-selective-escalation`, Python `3.12.10` from `D:\claude\eval-lab\.venv`, Git `2.51.2.windows.1`, dedicated worktree `.venv` absent, `PYTHONPATH=$PWD\src`. Exact commands and results:

- `D:\claude\eval-lab\.venv\Scripts\python.exe scripts/run_selective_escalation.py --benchmark benchmark/eval-lab-select-v0.1.0 --output experiments/EXP-20260920-012-selective-escalation-qwen-streaming --skip-providers --provider-limit 500 --pinned-predictions experiments/EXP-20260920-009-selective-escalation/provider-pinned.jsonl --rolling-predictions experiments/EXP-20260920-009-selective-escalation/provider-rolling.jsonl --qwen-predictions experiments/EXP-20260920-009-selective-escalation/qwen-streaming-final-merged-20260920-010/predictions.jsonl --experiment-id EXP-20260920-012-selective-escalation-qwen-streaming` -> threshold `2863`, final `2356`, provider `500`; each frozen provider arm `500/500 ok`.
- `D:\claude\eval-lab\.venv\Scripts\python.exe scripts/generate_research_artifacts.py --experiment experiments/EXP-20260920-012-selective-escalation-qwen-streaming --smoke-experiment experiments/EXP-20260920-009-selective-escalation` -> regenerated report, paper, tables, figures, RO-Crate, PROV-O, SHACL, and reproducibility appendix.
- `D:\claude\eval-lab\.venv\Scripts\python.exe scripts/check_repo_contract.py` -> `Repository contract OK`.
- `D:\claude\eval-lab\.venv\Scripts\ruff.exe check .` -> `All checks passed!`.
- `$env:PYTHONPATH=\"$PWD\\src\"; D:\claude\eval-lab\.venv\Scripts\python.exe -m pytest -q` -> `87 passed in 4.30s`.
- `$env:PYTHONPATH=\"$PWD\\src\"; D:\claude\eval-lab\.venv\Scripts\python.exe scripts/validate_research_artifacts.py --benchmark benchmark/eval-lab-select-v0.1.0` -> checksums `ok`, citation `parsed`, paper `present`, PROV-O `parsed`, RO-Crate `ok`, SHACL `conforms`.
- Direct SHA-256 verification -> benchmark `10` entries and EXP-012 `11` entries, zero mismatches; `git diff --check` clean.

The regenerated EXP-012 result retains fingerprint `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`, policy count `19`, pinned/rolling/Qwen `500/500 ok`, and Jev/Qwen differential `500` comparable with `486` agreements. Files changed are the EXP-012 derived results/report/routing/checksum files and generated paper/figure/table/limitations/reproducibility files. Frozen benchmark records and EXP-009 provider inputs remain unchanged. No credentials or `.env` files were read or committed.

Decision: local TASK-0010 acceptance evidence is green and the derived release is ready for its artifact commit. The task remains active until that commit is pushed and CI for the new head is inspected. Next atomic action: commit the regenerated EXP-012 and paper artifacts, push `task/TASK-0010-selective-escalation`, inspect the CI matrix, and then restore TASK-0010 to complete if CI remains green. Do not begin TASK-0002.

### 2026-09-20 — TASK-0010 final acceptance

Status: `complete`. The audited source and derived release are pushed on `task/TASK-0010-selective-escalation` at `c93c445eff384f72c93979c52107c5453e89fcc9`. The commits are `833e937` for policy metrics/paper generation, `6e8df8e` for LF-stable replay outputs, `ac220cc` for report-ending stability, and `c93c445` for the regenerated EXP-012 research release and checkpoint. Draft PR #26 is updated by the branch push.

Exact environment: Windows PowerShell, worktree `D:\claude\eval-lab-TASK-0010`, branch `task/TASK-0010-selective-escalation`, Python `3.12.10` from `D:\claude\eval-lab\.venv`, Git `2.51.2.windows.1`, Grok Build CLI `1.0.40 (eb1a2256660d)` at `C:\Users\pujan\.grok\bin\grok.exe` through the authenticated xAI subscription route. The corrective audit used Grok Build for inspection/local edits only; it made no OpenRouter/OpenCode provider call and no credential or `.env` file was read or committed.

Final local commands and results:

- `D:\claude\eval-lab\.venv\Scripts\python.exe scripts/check_repo_contract.py` -> `Repository contract OK`.
- `D:\claude\eval-lab\.venv\Scripts\ruff.exe check .` -> `All checks passed!`.
- `$env:PYTHONPATH=\"$PWD\\src\"; D:\claude\eval-lab\.venv\Scripts\python.exe -m pytest -q` -> `87 passed in 4.30s`.
- `$env:PYTHONPATH=\"$PWD\\src\"; D:\claude\eval-lab\.venv\Scripts\python.exe scripts/validate_research_artifacts.py --benchmark benchmark/eval-lab-select-v0.1.0` -> checksums `ok`, citation `parsed`, paper `present`, PROV-O `parsed`, RO-Crate `ok`, SHACL `conforms`.
- `git diff --check` -> clean before push.
- GitHub Actions CI run `35559286318` (`https://github.com/Pukujan/Eval-lab/actions/runs/35559286318`) -> success on Python `3.11` and `3.12`; install, repository contract, Ruff, and unit tests all passed. Only non-failing platform deprecation annotations were emitted.

Final frozen evidence: benchmark `EvalLab-Select v0.1.0`, fingerprint `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`, ARC revision `210d026faf9955653af8916fad021475a3f00453`, canonicalization `eval-lab-select-single-v1`, confidence `max(calibrated class probability)`, targets `0.01/0.02/0.05/0.10`, typed System-One `eval-lab-system-one` v0.1.0, and frozen primary student TASK-0009 TF-IDF plus logistic-regression arm D. EXP-012 has `2,863` threshold-selection records, `2,356` final-evaluation records, a deterministic `500`-record provider prefix, `19` routing policies, pinned Jev `500/500 ok`, rolling Jev `500/500 ok` as a separate canary, Qwen `500/500 ok`, and Jev/Qwen differential `500` comparable with `486` agreements. Low-error operating points are labeled descriptive/underpowered when Wilson support is insufficient.

Files delivered include the provider-independent routing core and tests, selective results and matched random controls, Jev/System-One differential, benchmark source manifest/splits/checksums, RO-Crate 1.3 metadata, PROV-O, SHACL shapes, valid CITATION.cff, machine-generated paper tables/figures, completed `paper/main.tex`, reproducibility appendix, limitations/threats-to-validity, and exact reproduction commands. No benchmark records, frozen EXP-009 provider inputs, credentials, or `.env` files were changed or committed.

Decision: TASK-0010 acceptance criteria are satisfied. Keep pinned and rolling Jev separate, keep Qwen as the secondary provider arm, keep Grok Build as an audit/continuity tool rather than replacing the primary student, and leave TASK-0002 unopened. Next atomic action: normal review/triage of PR #26; no new implementation task is authorized by this checkpoint.

### 2026-09-21 — TASK-0011 preregistration

TASK-0010 is complete but PR #26 remains an open draft. A follow-on worktree `D:/claude/eval-lab-TASK-0011-Qwen` was created from TASK-0010 head `4b4356ac36f71ffd69e44f4b44526880addc675f` on branch `task/TASK-0011-multidomain-qwen-holdout`. The new experiment is `EXP-20260921-013-qwen-multidomain-holdout`.

Scope is frozen before new Qwen labels: YOLO-Auto `qwen3.8-flash` streaming over ARC-Challenge, ARC-Easy, GSM8K, selected MIT-licensed MMLU subjects, and the existing four-domain deterministic synthetic fixtures. Original public test partitions are blind holdouts; source-family variants cannot cross splits; objective gold remains answer-key or deterministic-verifier provenance. Qwen confidence is not treated as calibrated probability unless real probabilities/logprobs are returned.

Exact metadata checks: Hugging Face API resolved GSM8K revision `740312add88f781978c0658806c59bc2815b9866` with MIT metadata, MMLU revision `c30699e8356da336a370243923dbaf21066bb9fe` with MIT metadata, and ARC revision `210d026faf9955653af8916fad021475a3f00453` with CC BY-SA 4.0 metadata. No provider call or holdout label evaluation has occurred.

Files added: `tasks/TASK-0011-multidomain-qwen-holdout.md`, `experiments/EXP-20260921-013-qwen-multidomain-holdout/PLAN.md`, `experiment.yaml`, and `README.md`; this checkpoint was updated.

Next atomic action: commit the preregistration and checkpoint, then run a one-record Qwen3.8 Flash smoke with the existing typed streaming adapter. Do not evaluate the blind holdout until source, split, and holdout manifests are committed.\n\n### 2026-09-21 — Qwen availability smoke\n\nThe preregistration is committed through `d27802d` after correcting the required task headings. The local credential check found `C:\Users\pujan\OneDrive\Desktop\configs\.env` and a process credential without printing either value.\n\nExact smoke command:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_qwen_streaming_retry.py --benchmark benchmark/eval-lab-select-v0.1.0 --output experiments/EXP-20260921-013-qwen-multidomain-holdout/smoke-qwen-20260921 --limit 1 --timeout 120 --env-file C:\\Users\\pujan\\OneDrive\\Desktop\\configs\\.env`\n\nResult: `status_counts={"ok": 1}`. The request used YOLO-Auto streaming and returned the expected `qwen3.8-flash` identity. No holdout or bulk labels were requested.\n\nExact local gate after the plan correction: repository contract `OK`; Ruff `All checks passed!`; `87 passed in 3.84s`.\n\nFiles changed: the smoke output under `experiments/EXP-20260921-013-qwen-multidomain-holdout/smoke-qwen-20260921/`; no secret values were written.\n\nDecision: Qwen is available for the planned multidomain run. Next atomic action: build the ARC-Easy, GSM8K, MMLU, existing ARC-Challenge, and synthetic source pool; freeze source metadata, split counts, holdout IDs, and checksums in a new commit before any bulk holdout request.\n\n### 2026-09-21 — multidomain source and holdout freeze\n\nThe source pool was built with `scripts/build_multidomain_holdout.py` from committed code `5d4c6e5`. It resolved and recorded ARC revision `210d026faf9955653af8916fad021475a3f00453`, GSM8K revision `740312add88f781978c0658806c59bc2815b9866`, and MMLU revision `c30699e8356da336a370243923dbaf21066bb9fe`. The frozen record fingerprint is `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`; the blind holdout record-ID fingerprint is `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`.\n\nCounts: `648` public-selection records and `760` blind-holdout records, `1,408` unique record IDs, zero source-family overlap. Public/holdout dataset counts are recorded in `source-manifest.json` and `splits.json`; holdout IDs and the no-label-selection declaration are in `holdout-manifest.json`; all files are covered by `checksums.sha256`.\n\nExact command: `D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/build_multidomain_holdout.py --benchmark benchmark/eval-lab-select-v0.1.0 --output experiments/EXP-20260921-013-qwen-multidomain-holdout --code-commit 5d4c6e5311f566b47276687c423b174501950da3`. The Hugging Face cache warnings were non-failing and no cache was committed.\n\nDecision: source revisions, canonicalization, sample limits, splits, holdout IDs, model route, and metrics are now frozen. The public partition may be scored; the blind holdout must remain unevaluated until after this freeze. Next atomic action: commit this manifest freeze, then run Qwen over the public-selection partition and record provider statuses before the blind holdout request.\n\n### 2026-09-21 — Qwen public partition rate-limit checkpoint\n\nThe frozen source/holdout pool remains unchanged. The first public-selection command was run after the manifest commit:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_multidomain_qwen.py --pool experiments/EXP-20260921-013-qwen-multidomain-holdout --partition public_selection --output experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-20260921 --workers 4 --timeout 120 --env-file C:\\Users\\pujan\\OneDrive\\Desktop\\configs\\.env`\n\nResult: `648` records, `197 ok`, `5 parse_error`, `446 rate_limited`. No failed provider response received a label. The output is retained as a separate provider execution artifact. A follow-up one-record smoke after the bulk request returned `rate_limited: 1`, confirming the provider rate limit was still active.\n\nThe runner now supports an explicit record-ID retry file so only unresolved public records can be retried later. `public-retry-record-ids.txt` contains `451` unresolved record IDs. No blind-holdout request has been made.\n\nDecision: preserve the partial public result and do not spend blind-holdout requests while the provider is rate-limited. Next atomic action: after a verified provider recovery, retry only the `451` public IDs at one worker, merge status-preserving outputs, and run the blind holdout only after public execution is either complete or explicitly checkpointed as provider-blocked.\n\n### 2026-09-21 — public Qwen retry and merge complete\n\nAfter the rate-limited smoke, a recovery smoke returned `ok: 1`. The bounded retry command was:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_multidomain_qwen.py --pool experiments/EXP-20260921-013-qwen-multidomain-holdout --partition public_selection --record-ids-file experiments/EXP-20260921-013-qwen-multidomain-holdout/public-retry-record-ids.txt --output experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-retry-20260921 --workers 1 --timeout 120 --env-file C:\\Users\\pujan\\OneDrive\\Desktop\\configs\\.env`\n\nRetry result: `451` requested records, `442 ok`, `9 parse_error`, zero rate limits. The immutable merge command was:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/merge_multidomain_qwen.py --pool experiments/EXP-20260921-013-qwen-multidomain-holdout --partition public_selection --base experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-20260921 --retry experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-retry-20260921 --output experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-merged-20260921`\n\nThe merged public result is `648` records: `639 ok`, `9 parse_error`, no fabricated labels. The nine parse errors remain unresolved. The frozen source and blind-holdout manifests were not changed.\n\nFiles changed: immutable retry/merged Qwen outputs, recovery smoke, root checksum manifest, and the runner retry-hint code. Next atomic action: run Qwen over the frozen `760`-record `blind_holdout` partition with one worker, preserving all status outcomes and no tuning from holdout labels.\n\n### 2026-09-21 — initial blind-holdout pass\n\nThe frozen blind-holdout command was:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_multidomain_qwen.py --pool experiments/EXP-20260921-013-qwen-multidomain-holdout --partition blind_holdout --output experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-blind-holdout-20260921 --workers 1 --timeout 120 --env-file C:\\Users\\pujan\\OneDrive\\Desktop\\configs\\.env`\n\nResult: `760` records, `438 ok`, `8 parse_error`, `314 rate_limited`. The initial holdout request used only the frozen typed packet; holdout labels were not used for any tuning or selection. `blind-retry-record-ids.txt` contains the `322` unresolved IDs.\n\nDecision: retain the initial holdout pass as immutable evidence and retry only its unresolved IDs after provider recovery. The eight parse errors and any remaining rate limits stay unresolved unless a bounded retry succeeds. Next atomic action: run a one-record recovery smoke, then retry the `322` blind IDs at one worker if the provider accepts requests.\n\n### 2026-09-21 — blind-holdout retry-after blocker\n\nThe one-record recovery smoke command was:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_qwen_streaming_retry.py --benchmark benchmark/eval-lab-select-v0.1.0 --output experiments/EXP-20260921-013-qwen-multidomain-holdout/smoke-qwen-holdout-recovery-20260921 --limit 1 --timeout 120 --env-file C:\\Users\\pujan\\OneDrive\\Desktop\\configs\\.env`\n\nResult: `rate_limited: 1`, with provider `Retry-After: 2587` seconds. The first blind pass remains `438 ok`, `8 parse_error`, `314 rate_limited`; `322` record IDs are preserved for retry.\n\nDecision: TASK-0011 remains active and provider-blocked for the unresolved blind records until the declared retry window expires. No alternative model, OpenRouter route, or hidden-holdout substitution will be used. The public result is complete at `639 ok` and `9 parse_error`; the blind result is partial and must not be presented as a complete multidomain score.\n\nNext atomic action: after the provider retry window, run the `322` IDs from `blind-retry-record-ids.txt` with one worker, merge them with `qwen-blind-holdout-20260921`, then compute the final per-dataset report. No new source, prompt, or model decision is allowed before that retry.

### 2026-09-21 — TASK-0011 offline reporting checkpoint

The public Qwen partition is complete at `639 ok` and `9 parse_error` from `648` records. The blind partition is partial at `438 ok`, `8 parse_error`, and `314 rate_limited` from `760`; `322` unresolved IDs remain in `blind-retry-record-ids.txt`. YOLO-Auto returned `Retry-After: 2587` seconds on the recovery smoke.

The offline report layer now emits per-dataset accuracy, Wilson 95% binomial intervals, balanced accuracy, macro-F1, unresolved rate, latency summaries, and provider status counts. The frozen pool fingerprints remain source `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8` and blind IDs `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`; counts remain `648` public, `760` blind, `1,408` unique, with zero source-family overlap.

Local gate: contract `OK`; Ruff clean; `92 passed in 4.31s`; `git diff --check` clean; experiment checksum manifest `41` entries with `0` mismatches. Files changed are the multidomain runner/report/test, experiment reports/README/checksums, and checkpoint/task logs. No credentials were printed or committed.

Decision: keep the blind partial result explicitly provisional and keep the frozen Qwen route unchanged. Next atomic action: after the retry window, recovery smoke, retry `322` IDs, merge, report, rerun gates, and commit/push the completion checkpoint.

### 2026-09-21 — TASK-0011 complete

TASK-0011 completed EXP-20260921-013. The frozen pool contains `648` public and `760` blind records with source fingerprint `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8` and blind record-ID fingerprint `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`. Public Qwen status is `639 ok`, `9 parse_error`; blind merged status is `754 ok`, `6 parse_error`. Public resolved accuracy is `0.8591549296`; blind resolved accuracy is `0.8448275862` with unresolved rate `0.0078947368`.

The final experiment bundle contains merged predictions, root `results.json`, root `report.md`, per-partition reports, limitations, source/split/holdout manifests, and `56` checksum entries with `0` mismatches. Local validation is contract `OK`, Ruff clean, `92 passed in 4.29s`, and research-artifact validation checksums `ok`, citation parsed, paper present, PROV-O parsed, RO-Crate `ok`, and SHACL conforms.

TASK-0011 is complete. TASK-0012 remains planned only: its independent JevBench audit is committed at `c880215`, but no live Jev benchmark has started.

### 2026-09-21 — TASK-0012 independent Jev benchmark complete

EXP-014 is complete. The frozen independent pool is `648` public-selection plus `760` blind-holdout records, fingerprint `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`, blind ID fingerprint `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`, and typed packet fingerprint `0d07bd8b8b60bd7f0b5b7a5f5819b7d329ea121f686b240e465695b6f6eca1e4`.

Exact live commands are committed in `experiments/EXP-20260921-014-independent-jev-benchmark/commands.md`. Pinned `typesafe/jev-1.13` returned `760 ok`, `684/760` correct (`0.9000`, Wilson `[0.8766, 0.9194]`), balanced accuracy `0.9263`, macro-F1 `0.7483`, p95 `380.2734 ms`, and no native probabilities. Rolling `~typesafe/jev-latest` returned `263 ok`, `2 provider_error`, `495 skipped`, and stopped after two HTTP 503 errors; it is a separate nonrandom canary. Qwen comparison is `637/754` resolved correct (`0.8448`, unresolved `0.0079`); pinned-versus-Qwen agreement is `652/754` (`0.8647`).

The final pinned robustness artifact has `60 ok`: repeatability `1.0`, option-order agreement `1.0`, and rubric-paraphrase agreement `0.9167`. Earlier 503 recovery artifacts remain preserved. No credential or `.env` file was written. Local validation: repository contract `OK`, Ruff clean, `94 passed`, checksums `0` mismatches, and `git diff --check` clean.

Decision: TASK-0012 acceptance is satisfied. JevBench remains contextual evidence only; the independent Eval Lab metric vector is primary. Next atomic action: review TASK-0012; do not begin a dependent task without explicit triage.

### 2026-09-21 — TASK-0015 public matched run complete

The Eval Lab worktree organization is complete: all `18` registered worktrees are
under `D:\\claude\\eval-lab\\.worktrees`, with no `eval-lab-*` sibling directories
remaining directly under `D:\\claude`. TASK-0015 was resumed from the organized
`TASK-0015-bakeoff` worktree without rerunning completed Grok or Luna checkpoints.

EXP-20260921-015 public selection is finalized at `648` matched records per arm.
Direct Grok Build CLI returned `643 ok` and `5 provider_error`; direct Codex Luna
returned `648 ok`; YOLO-Auto Qwen Flash returned `647 ok` and `1 parse_error`. All
three arms used streaming and their required direct-only routes. The finalized files
are under `experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/runs/public-stream-parallel-20260921/`.

The experiment validator passed. Repository contract, Ruff, all `100` tests, and
`git diff --check` passed. No OpenCode or OpenRouter call was used. Grok/provider
failures and the Qwen parse error remain explicit unresolved outcomes; no fallback
labels were added. The blind holdout remains untouched.

Next atomic action: review the public artifact and decide whether to authorize a
separate blind-holdout run; do not alter the frozen pool or public results.

### 2026-09-21 — TASK-0015 complete

EXP-015 is complete from the organized `D:\\claude\\eval-lab\\.worktrees\\TASK-0015-bakeoff`
worktree. The frozen blind holdout attempted all `760` records for all three core
arms with streaming and four workers per arm. Direct Grok Build returned `756 ok` and
`4 provider_error`; direct Codex Luna returned `760 ok`; YOLO-Auto Qwen Flash returned
`442 ok`, `1 provider_error`, and `317 rate_limited`. The public selection remains
separately reported and was not pooled into the primary blind score.

The combined blind artifact is
`experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/runs/blind-stream-parallel-20260921/`;
the experiment root now has `status: completed`, `results.json`, and `report.md`.
Its validator passed, and the final repository gate passed: contract `OK`, Ruff clean,
all tests passing, experiment checksums valid, and `git diff --check` clean. Temporary
parallel arm directories were hash-verified and removed. No OpenCode or OpenRouter
route was used.

Decision: preserve provider failures/rate limits as unresolved execution states and
close TASK-0015 without retries. A retry of Qwen's rate-limited records, if desired,
must be a separately timestamped experiment and cannot modify EXP-015.

Next atomic action: normal review of the committed EXP-015 report; no further provider
execution is required for TASK-0015.

### 2026-09-21 — TASK-0016 Qwen retry preregistration

TASK-0015 is complete and immutable. A new organized worktree
`D:\\claude\\eval-lab\\.worktrees\\TASK-0016-qwen-retry` on branch
`task/TASK-0016-qwen-rate-limit-retry` preregisters EXP-016, a Qwen-only retry of
exactly the `317` blind records that were rate-limited in EXP-0015. The original Qwen
provider error, Grok records, Luna records, prompt, pool, and gold labels are excluded
from the retry.

No new provider call has occurred in TASK-0016. Next atomic action: commit the
preregistration, generate the frozen retry-ID manifest from EXP-0015, then run a
one-record YOLO-Auto recovery smoke before the bulk retry.

### 2026-09-21 — TASK-0016 recovery smoke passed

The TASK-0016 one-record YOLO-Auto smoke passed with `ok: 1`, surfaced
`qwen3.8-flash`, and used the direct streaming route. The shared runner now accepts
`--experiment-id`, so the smoke and future retry artifacts are correctly labeled
`EXP-20260921-016-qwen-rate-limit-retry`. The exact 317-ID manifest remains committed
with SHA-256 `A89635149C2DED6015E897E17D565084D71DB6CD20F66B759E25CF6630C29C15`.

No bulk retry has started. Next atomic action: commit the runner metadata fix and smoke,
then execute the frozen 317-ID Qwen retry without touching EXP-015.

### 2026-09-21 — TASK-0016 Qwen retry complete

EXP-016 retried exactly the `317` EXP-015 Qwen rate-limited blind records. All `317`
returned `ok` through direct YOLO-Auto `qwen3.8-flash` streaming with one worker.
Resolved accuracy is `0.9526813880` with Wilson 95% interval `[0.9234052218, 0.9711175779]`.

The retry is finalized under
`experiments/EXP-20260921-016-qwen-rate-limit-retry/runs/retry-20260921/` and remains
separate from EXP-015. The shared runner and validator now accept explicit experiment
IDs, preserving correct metadata for both experiments. No OpenCode or OpenRouter route
was used, and EXP-015 was not modified.

Next atomic action: run the full repository gate, commit TASK-0016, and leave the
primary EXP-015 result frozen.

### 2026-09-21 — TASK-0017 judge calibration study opened

TASK-0016 is complete and immutable. A new organized worktree
`D:\\claude\\eval-lab\\.worktrees\\TASK-0017-calibration` on branch
`task/TASK-0017-calibration-study` is opened from commit `f446271`.

EXP-017 preregisters a local `Qwen/Qwen3-4B` forced-choice calibration study over
the exact EXP-015 pool. Public-selection records fit one temperature artifact per
judgment mode; blind-holdout records are evaluation-only. Existing direct Grok Build,
Luna, remote Qwen Flash, and pinned Jev outputs are reused offline as immutable
label-only references. No OpenCode or OpenRouter route is allowed.

The machine has a Transformers/PyTorch runtime and an RTX 4060 Laptop GPU, but the
Qwen 4B checkpoint is not currently cached; the next gate is a bounded local
feasibility smoke with explicit runtime/quantization evidence before blind scaling.

Next atomic action: commit the EXP-017 preregistration and local prompt scaffolding,
then run the bounded local Qwen 4B smoke without changing EXP-015 or EXP-014.

### 2026-09-21 — TASK-0017 Qwen 4B feasibility smoke passed

The managed repository environment now has CUDA-enabled PyTorch `2.11.0+cu128`,
CUDA `12.8`, Transformers `5.17.0`, and the RTX 4060 is visible. The declared
one-record local Qwen 4B smoke passed with model revision
`1cfa9a7208912126459214e8b04321603b3df60c`, `cuda:0`, float16, valid probabilities,
and `1/1 ok`; the smoke latency was `4714.69 ms`.

The first system-Python attempt failed before model execution because it used a
CPU-only torch build; it is an environment diagnostic and not a model result. The
local scorer now batches legal-label continuations into one forward pass per record.
The smoke-only temperature artifact is not treated as calibration evidence.

Next atomic action: commit the smoke and batching checkpoint, then run EXP-017
public-selection calibration with the managed CUDA runtime. Do not touch the EXP-015
blind outputs or invoke OpenCode/OpenRouter.

The local runner now checkpoints every Qwen 4B prediction immediately and supports
validated `--resume`; duplicate 4B model copies will not be launched on the 8 GiB
GPU. The next atomic action is to commit that runner checkpoint and start the frozen
public-selection calibration run.
