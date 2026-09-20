# Current Repository Checkpoint

## Program state

TASK-0001 local bootstrap is complete.
TASK-0002 through TASK-0006 planning was accepted in PR #11.

The program is extended with TASK-0007 through TASK-0009 to fully use the user's existing model subscriptions/resources after the measurement foundation is complete.

## Main objective

Continue with TASK-0002 as the next implementation gate.

## Model-access decisions

- Jev baseline uses exact model id `jev-1.13-free`; no automatic paid fallback.
- Qwen3.8 Flash authoritative automated path is YOLO-Auto:
  - base URL `https://yolo-auto.com/v1`
  - model `qwen3.8-flash`
  - environment variable `YOLO_AUTO_API_KEY`
  - user reports the credential is already configured locally
- SuperGrok should be actively used through supported subscription OAuth/OpenCode integration.
- ChatGPT Luna/Sol should be actively used through reproducible audit-batch handoffs, not treated as OpenAI API access.
- OpenCode free general models should be enumerated and benchmarked in a bounded representative set.

## Next task

TASK-0006 — Lightweight Local Judge Baseline (#10)

## Queued foundation

- TASK-0003 — Jev Free Baseline (#7)
- TASK-0004 — Metrics and Calibration (#8)
- TASK-0005 — ARC-Challenge Adapter (#9)
- TASK-0006 — Lightweight Local Judge (#10)

## Queued extension

- TASK-0007 — External Judge and Teacher Bakeoff (#12)
- TASK-0008 — Verified Teacher Hard Negatives (#13)
- TASK-0009 — Small Judge Training Pilot (#14)

## External conditions

Jev may remain rate-limited; this is an execution state and does not block the rest of the program.

GitHub Actions runner scheduling remains infrastructure-only until runners are assigned; local validation remains authoritative.

## Next atomic action

TASK-0006 is active in dedicated worktree `D:\claude\eval-lab-TASK-0006` on branch `task/TASK-0006-lightweight-local-baseline`, starting from accepted `main` merge commit `644202fbdd49a3735775ae1c55d1e621de1044d6`.

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

Commit `6452bc8` records the calibrated experiment outputs and `b0202e2` records the final local gate. TASK-0006 is pushed in PR [#21](https://github.com/Pukujan/Eval-lab/pull/21). Next atomic action: merge PR #21 after the local merge gate, update local `main`, and only then create the TASK-0007 worktree. Do not start TASK-0007 until TASK-0006 is accepted and merged.
TASK-0005 is pushed in PR [#19](https://github.com/Pukujan/Eval-lab/pull/19) at commit `d8f038d1725ffcc1121bc0381ae6cabad2e4136b`.

Next atomic action: merge PR #19 after the local merge gate, update local `main`, and only then create the TASK-0006 worktree.
