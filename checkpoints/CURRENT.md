# Current Repository Checkpoint

## Authoritative status

TASK-0001 through TASK-0009 are merged. TASK-0010 is under corrective release audit: EXP-20260920-012-selective-escalation-qwen-streaming is the completion replay, and EXP-20260920-009-selective-escalation remains the planned baseline. The next program task remains unopened pending TASK-0010 commit and CI verification.

## Program state

TASK-0001 local bootstrap is complete.
TASK-0002 through TASK-0009 implementation is merged; TASK-0009 merged in PR #24. TASK-0010 local acceptance evidence is complete in the EXP-20260920-012 completion replay, with the corrective metrics and paper audit awaiting commit and CI verification.

The program is extended with TASK-0007 through TASK-0009 to fully use the user's existing model subscriptions/resources after the measurement foundation is complete.

## Main objective

TASK-0009 is complete. TASK-0010 selective escalation/research release is in corrective audit; the next program task remains unopened.

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

No new program task is open. Complete the TASK-0010 corrective audit at EXP-20260920-012, then leave the next program task unopened pending review.

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
