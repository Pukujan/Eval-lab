# TASK-0011 — Qwen Multidomain Evaluation and Blind Holdouts

- Status: completed — public and blind multidomain Qwen results finalized
- Owner: Luna/local agent
- Priority: P0
- Depends on: TASK-0010 acceptance in PR #26
- Branch: `task/TASK-0011-multidomain-qwen-holdout`
- Worktree: `D:/claude/eval-lab-TASK-0011-Qwen`
- Planned experiment: `EXP-20260921-013-qwen-multidomain-holdout`
- Base evidence commit: `4b4356ac36f71ffd69e44f4b44526880addc675f`

## Goal

Measure whether YOLO-Auto `qwen3.8-flash` is reliable across multiple objective task families and unseen public holdouts. Extend the TASK-0010 evidence without modifying or overwriting completed experiments.

TASK-0010 calibrated the frozen TASK-0009 local TF-IDF/logistic-regression student on the EvalLab-Select benchmark. It did not calibrate a universal judge across datasets, and it did not establish Qwen confidence calibration. This task addresses that gap with a new experiment ID.

## Frozen provider route

- Provider: YOLO-Auto
- Base URL: `https://yolo-auto.com/v1` unless the local environment declares `YOLO_AUTO_BASE_URL` or `QWEN_API_URL`
- Model: `qwen3.8-flash`
- Credential: `YOLO_AUTO_API_KEY` (fallback names may be read locally by the runner but never written to artifacts)
- Transport: one record per streaming request, `temperature=0`, thinking disabled, typed JSON/label response
- Provider errors, rate limits, parse errors, and model identity mismatches remain unresolved; no fallback label is allowed

## Dataset families

The initial preregistered pool is objective-only and source-family disjoint:

1. Existing EvalLab synthetic fixtures covering arithmetic, multiple-choice, structured-output, and code/output verification. Synthetic records used for training/calibration must not appear in the holdout.
2. `allenai/ai2_arc`, config `ARC-Challenge`, revision `210d026faf9955653af8916fad021475a3f00453`, license `CC BY-SA 4.0`, reusing the frozen TASK-0010 canonicalization as the replication anchor.
3. `allenai/ai2_arc`, config `ARC-Easy`, pinned to the resolved revision recorded during adapter execution and covered by the source manifest.
4. `openai/gsm8k`, config `main`, revision `740312add88f781978c0658806c59bc2815b9866`, license `MIT`, with deterministic answer normalization and executable arithmetic verification where possible.
5. `cais/mmlu`, selected preregistered subject configs spanning knowledge, math, science, and reasoning, revision `c30699e8356da336a370243923dbaf21066bb9fe`, license `MIT`. The subject list is frozen before any holdout labels are inspected.

A candidate source with unresolved licensing or non-objective gold is excluded and documented rather than silently included.

## Split and holdout policy

- Source problem IDs, not derived record IDs, determine splits.
- Training/dev/calibration records are used only for adapter checks, prompt/schema checks, and any calibration that is actually supported by the prediction format.
- Original public test splits and a disjoint source-family slice are the blind holdout. Holdout gold is not read for prompt, model, threshold, dataset, or stopping decisions.
- Correct/wrong or position-swapped variants inherit the source problem's split and never cross the holdout boundary.
- The holdout manifest stores source IDs, revisions, and checksums; it does not expose labels to provider-runner code.
- No record is duplicated or resampled to reach a target count. Report the legitimately available counts by dataset and split.

## Qwen confidence and calibration boundary

The provider route is primarily a label evaluation. Qwen self-reported confidence is not accepted automatically as a probability. Brier, NLL, ECE, and risk/coverage are reported only when the provider returns verifiable probabilities/logprobs or when a separately declared local forced-choice Qwen scoring arm supplies them. Otherwise the report records explicit unavailability and does not claim calibrated Qwen confidence.

## Primary comparisons

- Qwen accuracy, balanced accuracy, macro F1, and unresolved rate by dataset/domain.
- Public development/calibration results versus blind holdout results.
- Position-swap and rubric-paraphrase consistency where the canonical task supports those transformations.
- Latency mean/median/p95, calls per 1,000, provider status counts, and reported usage/cost when supplied.
- TASK-0010 ARC-Challenge Jev pinned results as a historical comparator only; Jev and Qwen remain separate model arms.

## Required artifacts

- `experiments/EXP-20260921-013-qwen-multidomain-holdout/PLAN.md`
- frozen `experiment.yaml`, source manifest, split/holdout manifest, and checksums before holdout evaluation;
- deterministic adapters/builders for every included source;
- normalized Qwen predictions retaining raw provider status and model identity;
- `results.json`, `report.md`, per-domain tables, and limitations;
- tests for canonicalization, source-family leakage, holdout isolation, provider error handling, and output parsing;
- exact reproduction commands without credentials and a credentialed live command template;
- checkpoint updates recording counts, fingerprints, Qwen availability, and the next atomic action.

## Acceptance criteria

- [x] preregistration and source/license/revision manifest committed before holdout labels are evaluated;
- [x] at least ARC-Challenge plus two additional objective dataset families are evaluated, if their metadata and retrieval are available;
- [x] synthetic four-domain records are included without source-family leakage;
- [x] Qwen streaming smoke succeeds or is explicitly checkpointed as provider-blocked;
- [x] public and blind holdout results are separate and reproducible;
- [x] no provider/model judgment is promoted to objective gold;
- [x] per-dataset accuracy, balanced accuracy, macro F1, unresolved rate, latency, and provider status are reported;
- [x] probability calibration is reported only when supported by actual probability/logprob evidence;
- [x] repository contract, Ruff, pytest, and artifact validation pass;
- [x] TASK-0010 remains immutable and TASK-0002 is not started.

## Checkpoint rule

At each stopping point record exact environment, files changed, commands, dataset counts, source revisions, fingerprints, Qwen model/provider status, decisions, blockers, and the next atomic action. Never overwrite EXP-20260920-012 or any completed experiment.

## Next atomic action

TASK-0011 is complete. The next program action is the separately planned TASK-0012 JevBench audit and independent benchmark, which must freeze its own source pool before any live Jev call.

## Checkpoint log

### 2026-09-21 — preregistration committed

The preregistration and experiment plan were committed in `1fdd2fc` before any Qwen call. The repository contract then identified the missing required task headings `## Checkpoint log` and `## Handoff`; this checkpoint records the correction. No provider labels or holdout labels exist yet.

## Handoff

Worktree: `D:/claude/eval-lab-TASK-0011-Qwen`
Branch: `task/TASK-0011-multidomain-qwen-holdout`
Experiment: `EXP-20260921-013-qwen-multidomain-holdout`
Next atomic action: commit the contract-heading correction, rerun contract/Ruff/pytest, then run a one-record Qwen3.8 Flash smoke. Keep the blind holdout unevaluated until its source and split manifests are frozen and committed.\n\n### 2026-09-21 — Qwen availability smoke\n\nThe preregistration is committed through `d27802d` after correcting the required task headings. The local credential check found `C:\Users\pujan\OneDrive\Desktop\configs\.env` and a process credential without printing either value.\n\nExact smoke command:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_qwen_streaming_retry.py --benchmark benchmark/eval-lab-select-v0.1.0 --output experiments/EXP-20260921-013-qwen-multidomain-holdout/smoke-qwen-20260921 --limit 1 --timeout 120 --env-file C:\\Users\\pujan\\OneDrive\\Desktop\\configs\\.env`\n\nResult: `status_counts={"ok": 1}`. The request used YOLO-Auto streaming and returned the expected `qwen3.8-flash` identity. No holdout or bulk labels were requested.\n\nExact local gate after the plan correction: repository contract `OK`; Ruff `All checks passed!`; `87 passed in 3.84s`.\n\nFiles changed: the smoke output under `experiments/EXP-20260921-013-qwen-multidomain-holdout/smoke-qwen-20260921/`; no secret values were written.\n\nDecision: Qwen is available for the planned multidomain run. Next atomic action: build the ARC-Easy, GSM8K, MMLU, existing ARC-Challenge, and synthetic source pool; freeze source metadata, split counts, holdout IDs, and checksums in a new commit before any bulk holdout request.\n\n### 2026-09-21 — multidomain source and holdout freeze\n\nThe source pool was built with `scripts/build_multidomain_holdout.py` from committed code `5d4c6e5`. It resolved and recorded ARC revision `210d026faf9955653af8916fad021475a3f00453`, GSM8K revision `740312add88f781978c0658806c59bc2815b9866`, and MMLU revision `c30699e8356da336a370243923dbaf21066bb9fe`. The frozen record fingerprint is `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`; the blind holdout record-ID fingerprint is `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`.\n\nCounts: `648` public-selection records and `760` blind-holdout records, `1,408` unique record IDs, zero source-family overlap. Public/holdout dataset counts are recorded in `source-manifest.json` and `splits.json`; holdout IDs and the no-label-selection declaration are in `holdout-manifest.json`; all files are covered by `checksums.sha256`.\n\nExact command: `D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/build_multidomain_holdout.py --benchmark benchmark/eval-lab-select-v0.1.0 --output experiments/EXP-20260921-013-qwen-multidomain-holdout --code-commit 5d4c6e5311f566b47276687c423b174501950da3`. The Hugging Face cache warnings were non-failing and no cache was committed.\n\nDecision: source revisions, canonicalization, sample limits, splits, holdout IDs, model route, and metrics are now frozen. The public partition may be scored; the blind holdout must remain unevaluated until after this freeze. Next atomic action: commit this manifest freeze, then run Qwen over the public-selection partition and record provider statuses before the blind holdout request.\n\n### 2026-09-21 — Qwen public partition rate-limit checkpoint\n\nThe frozen source/holdout pool remains unchanged. The first public-selection command was run after the manifest commit:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_multidomain_qwen.py --pool experiments/EXP-20260921-013-qwen-multidomain-holdout --partition public_selection --output experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-20260921 --workers 4 --timeout 120 --env-file C:\\Users\\pujan\\OneDrive\\Desktop\\configs\\.env`\n\nResult: `648` records, `197 ok`, `5 parse_error`, `446 rate_limited`. No failed provider response received a label. The output is retained as a separate provider execution artifact. A follow-up one-record smoke after the bulk request returned `rate_limited: 1`, confirming the provider rate limit was still active.\n\nThe runner now supports an explicit record-ID retry file so only unresolved public records can be retried later. `public-retry-record-ids.txt` contains `451` unresolved record IDs. No blind-holdout request has been made.\n\nDecision: preserve the partial public result and do not spend blind-holdout requests while the provider is rate-limited. Next atomic action: after a verified provider recovery, retry only the `451` public IDs at one worker, merge status-preserving outputs, and run the blind holdout only after public execution is either complete or explicitly checkpointed as provider-blocked.\n\n### 2026-09-21 — public Qwen retry and merge complete\n\nAfter the rate-limited smoke, a recovery smoke returned `ok: 1`. The bounded retry command was:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_multidomain_qwen.py --pool experiments/EXP-20260921-013-qwen-multidomain-holdout --partition public_selection --record-ids-file experiments/EXP-20260921-013-qwen-multidomain-holdout/public-retry-record-ids.txt --output experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-retry-20260921 --workers 1 --timeout 120 --env-file C:\\Users\\pujan\\OneDrive\\Desktop\\configs\\.env`\n\nRetry result: `451` requested records, `442 ok`, `9 parse_error`, zero rate limits. The immutable merge command was:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/merge_multidomain_qwen.py --pool experiments/EXP-20260921-013-qwen-multidomain-holdout --partition public_selection --base experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-20260921 --retry experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-retry-20260921 --output experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-merged-20260921`\n\nThe merged public result is `648` records: `639 ok`, `9 parse_error`, no fabricated labels. The nine parse errors remain unresolved. The frozen source and blind-holdout manifests were not changed.\n\nFiles changed: immutable retry/merged Qwen outputs, recovery smoke, root checksum manifest, and the runner retry-hint code. Next atomic action: run Qwen over the frozen `760`-record `blind_holdout` partition with one worker, preserving all status outcomes and no tuning from holdout labels.\n\n### 2026-09-21 — initial blind-holdout pass\n\nThe frozen blind-holdout command was:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_multidomain_qwen.py --pool experiments/EXP-20260921-013-qwen-multidomain-holdout --partition blind_holdout --output experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-blind-holdout-20260921 --workers 1 --timeout 120 --env-file C:\\Users\\pujan\\OneDrive\\Desktop\\configs\\.env`\n\nResult: `760` records, `438 ok`, `8 parse_error`, `314 rate_limited`. The initial holdout request used only the frozen typed packet; holdout labels were not used for any tuning or selection. `blind-retry-record-ids.txt` contains the `322` unresolved IDs.\n\nDecision: retain the initial holdout pass as immutable evidence and retry only its unresolved IDs after provider recovery. The eight parse errors and any remaining rate limits stay unresolved unless a bounded retry succeeds. Next atomic action: run a one-record recovery smoke, then retry the `322` blind IDs at one worker if the provider accepts requests.\n\n### 2026-09-21 — blind-holdout retry-after blocker\n\nThe one-record recovery smoke command was:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_qwen_streaming_retry.py --benchmark benchmark/eval-lab-select-v0.1.0 --output experiments/EXP-20260921-013-qwen-multidomain-holdout/smoke-qwen-holdout-recovery-20260921 --limit 1 --timeout 120 --env-file C:\\Users\\pujan\\OneDrive\\Desktop\\configs\\.env`\n\nResult: `rate_limited: 1`, with provider `Retry-After: 2587` seconds. The first blind pass remains `438 ok`, `8 parse_error`, `314 rate_limited`; `322` record IDs are preserved for retry.\n\nDecision: TASK-0011 remains active and provider-blocked for the unresolved blind records until the declared retry window expires. No alternative model, OpenRouter route, or hidden-holdout substitution will be used. The public result is complete at `639 ok` and `9 parse_error`; the blind result is partial and must not be presented as a complete multidomain score.\n\nNext atomic action: after the provider retry window, run the `322` IDs from `blind-retry-record-ids.txt` with one worker, merge them with `qwen-blind-holdout-20260921`, then compute the final per-dataset report. No new source, prompt, or model decision is allowed before that retry.

### 2026-09-21 — offline metric/report completion while provider is rate-limited

The frozen pool remains unchanged: source records fingerprint `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`, blind record-ID fingerprint `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`, `648` public-selection records, `760` blind-holdout records, `1,408` unique records, and zero source-family overlap. Source revisions remain ARC `210d026faf9955653af8916fad021475a3f00453`, GSM8K `740312add88f781978c0658806c59bc2815b9866`, and MMLU `c30699e8356da336a370243923dbaf21066bb9fe`.

Added `scripts/report_multidomain_qwen.py` and extended `scripts/run_multidomain_qwen.py` to report per-dataset accuracy, Wilson 95% binomial intervals, balanced accuracy, macro-F1, unresolved rate, latency summaries, and provider status counts. Added an offline regression test covering these metrics. The public report was regenerated from the immutable merged predictions: `639/648` resolved, `549` correct, accuracy `0.8591549296`, unresolved rate `0.0138888889`. The blind partial report remains explicitly provisional: `438/760` resolved, `364` correct, accuracy `0.8310502283` among resolved records, unresolved rate `0.4236842105`, with `314` rate-limited and `8` parse-error records.

Exact offline commands:

`$env:PYTHONPATH='src'; D:\claude\eval-lab\.venv\Scripts\ruff.exe check scripts/run_multidomain_qwen.py scripts/report_multidomain_qwen.py tests/test_multidomain.py` -> `All checks passed!`.

`$env:PYTHONPATH='src'; D:\claude\eval-lab\.venv\Scripts\python.exe -m pytest -q tests/test_multidomain.py` -> `5 passed in 0.60s`.

`$env:PYTHONPATH='src'; D:\claude\eval-lab\.venv\Scripts\python.exe scripts/report_multidomain_qwen.py --partition public_selection --input experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-merged-20260921 --output experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-report-20260921` -> report generated.

`$env:PYTHONPATH='src'; D:\claude\eval-lab\.venv\Scripts\python.exe scripts/report_multidomain_qwen.py --partition blind_holdout --input experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-blind-holdout-20260921 --output experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-blind-partial-report-20260921` -> report generated.

Environment: Windows PowerShell, worktree `D:\claude\eval-lab-TASK-0011-Qwen`, branch `task/TASK-0011-multidomain-qwen-holdout`, Python `3.12.10` from `D:\claude\eval-lab\.venv`, Git `2.51.2.windows.1`, Qwen model `qwen3.8-flash` via YOLO-Auto streaming. No credential values were printed or written. The report explicitly records probabilities/logprobs as unavailable; no Qwen self-reported confidence is treated as calibration.

Files changed: `scripts/run_multidomain_qwen.py`, `scripts/report_multidomain_qwen.py`, `tests/test_multidomain.py`, experiment README, public/partial report outputs, this task log, and `checkpoints/CURRENT.md`. Decision: retain public and blind partial evidence as immutable, preserve the explicit provider blocker, and do not present the blind partial accuracy as a final multidomain score.

Next atomic action: after the recorded `Retry-After: 2587` window, run the recovery smoke, retry the `322` IDs in `blind-retry-record-ids.txt`, merge with `qwen-blind-holdout-20260921`, regenerate the final report, run the full contract/Ruff/pytest/checksum gates, and commit/push the completion checkpoint.

### 2026-09-21 — TASK-0011 offline reporting checkpoint

Environment: Windows PowerShell, worktree `D:\claude\eval-lab-TASK-0011-Qwen`, branch `task/TASK-0011-multidomain-qwen-holdout`, Python `3.12.10` from `D:\claude\eval-lab\.venv`, Git `2.51.2.windows.1`. Qwen provider remains YOLO-Auto streaming, model `qwen3.8-flash`; no credential values were printed or committed.

The frozen experiment pool is unchanged at source fingerprint `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8` and blind record-ID fingerprint `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`. It contains `648` public-selection and `760` blind-holdout records, `1,408` unique records, and zero source-family overlap. Public Qwen is `639 ok`, `9 parse_error`, accuracy `0.8591549296` over resolved records. Blind Qwen is partial at `438 ok`, `8 parse_error`, `314 rate_limited`; the `322` unresolved IDs remain in `blind-retry-record-ids.txt`. The latest provider recovery smoke reported `Retry-After: 2587` seconds.

Files changed: `scripts/run_multidomain_qwen.py`, new `scripts/report_multidomain_qwen.py`, `tests/test_multidomain.py`, experiment README, public/partial report directories, experiment checksum manifest, this task log, and `checkpoints/CURRENT.md`. The report now includes per-dataset accuracy, balanced accuracy, macro-F1, unresolved rate, latency, provider status counts, and Wilson 95% binomial intervals. Qwen probabilities/logprobs remain unavailable; no confidence calibration claim is made.

Exact commands and results:

- `D:\claude\eval-lab\.venv\Scripts\python.exe scripts/check_repo_contract.py` -> `Repository contract OK`.
- `D:\claude\eval-lab\.venv\Scripts\ruff.exe check .` -> `All checks passed!`.
- `$env:PYTHONPATH='src'; D:\claude\eval-lab\.venv\Scripts\python.exe -m pytest -q` -> `92 passed in 4.31s`.
- `git diff --check` -> clean; line-ending warnings are Git normalization notices only.
- Experiment checksum verification -> `41` entries, `0` mismatches.

Decision: commit this offline reporting checkpoint and keep TASK-0011 active. Do not substitute OpenRouter, Jev, Grok, Luna, local Qwen, or any other provider for the frozen Qwen holdout. Do not use the blind partial score as a final score.

Next atomic action: after the declared retry window, run the one-record recovery smoke; if accepted, retry the `322` unresolved blind records with one worker, merge with `qwen-blind-holdout-20260921`, regenerate the final report/checksums, rerun the full gates, and commit/push the completion checkpoint.

### 2026-09-21 — TASK-0011 final acceptance

Status: `completed`. Environment: Windows PowerShell, worktree `D:\claude\eval-lab-TASK-0011-Qwen`, branch `task/TASK-0011-multidomain-qwen-holdout`, Python `3.12.10` from `D:\claude\eval-lab\.venv`, Git `2.51.2.windows.1`. Provider route was YOLO-Auto streaming with model `qwen3.8-flash`; credential values were never printed or committed.

The frozen source fingerprint is `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`; blind record-ID fingerprint is `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`. Counts are `648` public-selection records and `760` blind-holdout records, `1,408` unique records, and zero source-family overlap. Public status is `639 ok`, `9 parse_error`; public resolved accuracy is `549/639 = 0.8591549296`. Blind retry status is `316 ok`, `6 parse_error`; merged blind status is `754 ok`, `6 parse_error`; blind resolved accuracy is `637/754 = 0.8448275862`, Wilson 95% interval `[0.8172424225, 0.8689169238]`, unresolved rate `0.0078947368`.

Exact live commands:

- `$env:PYTHONPATH='src'; D:\claude\eval-lab\.venv\Scripts\python.exe scripts/run_qwen_streaming_retry.py --benchmark benchmark/eval-lab-select-v0.1.0 --output experiments/EXP-20260921-013-qwen-multidomain-holdout/smoke-qwen-holdout-recovery-2-20260921 --limit 1 --timeout 120 --env-file C:\Users\pujan\OneDrive\Desktop\configs\.env` -> `ok: 1`.
- `$env:PYTHONPATH='src'; D:\claude\eval-lab\.venv\Scripts\python.exe scripts/run_multidomain_qwen.py --pool experiments/EXP-20260921-013-qwen-multidomain-holdout --partition blind_holdout --record-ids-file experiments/EXP-20260921-013-qwen-multidomain-holdout/blind-retry-record-ids.txt --output experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-blind-retry-20260921 --workers 1 --timeout 120 --env-file C:\Users\pujan\OneDrive\Desktop\configs\.env` -> `322` requested, `316 ok`, `6 parse_error`.
- `$env:PYTHONPATH='src'; D:\claude\eval-lab\.venv\Scripts\python.exe scripts/merge_multidomain_qwen.py --pool experiments/EXP-20260921-013-qwen-multidomain-holdout --partition blind_holdout --base experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-blind-holdout-20260921 --retry experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-blind-retry-20260921 --output experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-blind-merged-20260921` -> `760` records, `754 ok`, `6 parse_error`.
- `$env:PYTHONPATH='src'; D:\claude\eval-lab\.venv\Scripts\python.exe scripts/finalize_multidomain_qwen.py --public experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-report-20260921 --blind experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-blind-report-20260921` -> completed root `results.json` and `report.md`.

Files changed: new finalizer script, root experiment results/report/limitations, merged blind/retry/recovery artifacts, experiment README/manifest/checksums, this task log, and `checkpoints/CURRENT.md`. The report includes per-dataset accuracy, balanced accuracy, macro-F1, unresolved rate, latency, provider status, and Wilson intervals. Qwen probabilities/logprobs were unavailable, so no Qwen confidence calibration is claimed. TASK-0010 and its artifacts remain immutable.

Exact validation results:

- `D:\claude\eval-lab\.venv\Scripts\python.exe scripts/check_repo_contract.py` -> `Repository contract OK`.
- `D:\claude\eval-lab\.venv\Scripts\ruff.exe check .` -> `All checks passed!`.
- `$env:PYTHONPATH='src'; D:\claude\eval-lab\.venv\Scripts\python.exe -m pytest -q` -> `92 passed in 4.29s`.
- `$env:PYTHONPATH='src'; D:\claude\eval-lab\.venv\Scripts\python.exe scripts/validate_research_artifacts.py --benchmark benchmark/eval-lab-select-v0.1.0` -> checksums `ok`, citation `parsed`, paper `present`, PROV-O `parsed`, RO-Crate `ok`, SHACL `conforms`.
- Experiment checksum verification -> `56` entries, `0` mismatches; `git diff --check` clean apart from Git line-ending normalization notices.

Decision: TASK-0011 acceptance criteria are satisfied. The next task is planned TASK-0012, which must use an independent Eval Lab source pool and must not use JevBench's tasks, labels, composite score, or estimated operational metrics as primary evidence.

Next atomic action: push this final TASK-0011 checkpoint, then freeze EXP-0014's independent source IDs, splits, typed packet, pinned/rolling Jev arms, comparison arms, and perturbation schedule before any live Jev call.
