# TASK-0011 — Qwen Multidomain Evaluation and Blind Holdouts

- Status: active
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

- [ ] preregistration and source/license/revision manifest committed before holdout labels are evaluated;
- [ ] at least ARC-Challenge plus two additional objective dataset families are evaluated, if their metadata and retrieval are available;
- [ ] synthetic four-domain records are included without source-family leakage;
- [ ] Qwen streaming smoke succeeds or is explicitly checkpointed as provider-blocked;
- [ ] public and blind holdout results are separate and reproducible;
- [ ] no provider/model judgment is promoted to objective gold;
- [ ] per-dataset accuracy, balanced accuracy, macro F1, unresolved rate, latency, and provider status are reported;
- [ ] probability calibration is reported only when supported by actual probability/logprob evidence;
- [ ] repository contract, Ruff, pytest, and artifact validation pass;
- [ ] TASK-0010 remains immutable and TASK-0002 is not started.

## Checkpoint rule

At each stopping point record exact environment, files changed, commands, dataset counts, source revisions, fingerprints, Qwen model/provider status, decisions, blockers, and the next atomic action. Never overwrite EXP-20260920-012 or any completed experiment.

## Next atomic action

Commit this preregistration and checkpoint. Then run a one-record YOLO-Auto Qwen3.8 Flash smoke using the frozen typed specification. Do not build or evaluate the blind holdout until the smoke result and source manifest are recorded.

## Checkpoint log

### 2026-09-21 — preregistration committed

The preregistration and experiment plan were committed in `1fdd2fc` before any Qwen call. The repository contract then identified the missing required task headings `## Checkpoint log` and `## Handoff`; this checkpoint records the correction. No provider labels or holdout labels exist yet.

## Handoff

Worktree: `D:/claude/eval-lab-TASK-0011-Qwen`
Branch: `task/TASK-0011-multidomain-qwen-holdout`
Experiment: `EXP-20260921-013-qwen-multidomain-holdout`
Next atomic action: commit the contract-heading correction, rerun contract/Ruff/pytest, then run a one-record Qwen3.8 Flash smoke. Keep the blind holdout unevaluated until its source and split manifests are frozen and committed.\n\n### 2026-09-21 — Qwen availability smoke\n\nThe preregistration is committed through `d27802d` after correcting the required task headings. The local credential check found `C:\Users\pujan\OneDrive\Desktop\configs\.env` and a process credential without printing either value.\n\nExact smoke command:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_qwen_streaming_retry.py --benchmark benchmark/eval-lab-select-v0.1.0 --output experiments/EXP-20260921-013-qwen-multidomain-holdout/smoke-qwen-20260921 --limit 1 --timeout 120 --env-file C:\\Users\\pujan\\OneDrive\\Desktop\\configs\\.env`\n\nResult: `status_counts={"ok": 1}`. The request used YOLO-Auto streaming and returned the expected `qwen3.8-flash` identity. No holdout or bulk labels were requested.\n\nExact local gate after the plan correction: repository contract `OK`; Ruff `All checks passed!`; `87 passed in 3.84s`.\n\nFiles changed: the smoke output under `experiments/EXP-20260921-013-qwen-multidomain-holdout/smoke-qwen-20260921/`; no secret values were written.\n\nDecision: Qwen is available for the planned multidomain run. Next atomic action: build the ARC-Easy, GSM8K, MMLU, existing ARC-Challenge, and synthetic source pool; freeze source metadata, split counts, holdout IDs, and checksums in a new commit before any bulk holdout request.\n\n### 2026-09-21 — multidomain source and holdout freeze\n\nThe source pool was built with `scripts/build_multidomain_holdout.py` from committed code `5d4c6e5`. It resolved and recorded ARC revision `210d026faf9955653af8916fad021475a3f00453`, GSM8K revision `740312add88f781978c0658806c59bc2815b9866`, and MMLU revision `c30699e8356da336a370243923dbaf21066bb9fe`. The frozen record fingerprint is `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`; the blind holdout record-ID fingerprint is `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`.\n\nCounts: `648` public-selection records and `760` blind-holdout records, `1,408` unique record IDs, zero source-family overlap. Public/holdout dataset counts are recorded in `source-manifest.json` and `splits.json`; holdout IDs and the no-label-selection declaration are in `holdout-manifest.json`; all files are covered by `checksums.sha256`.\n\nExact command: `D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/build_multidomain_holdout.py --benchmark benchmark/eval-lab-select-v0.1.0 --output experiments/EXP-20260921-013-qwen-multidomain-holdout --code-commit 5d4c6e5311f566b47276687c423b174501950da3`. The Hugging Face cache warnings were non-failing and no cache was committed.\n\nDecision: source revisions, canonicalization, sample limits, splits, holdout IDs, model route, and metrics are now frozen. The public partition may be scored; the blind holdout must remain unevaluated until after this freeze. Next atomic action: commit this manifest freeze, then run Qwen over the public-selection partition and record provider statuses before the blind holdout request.\n\n### 2026-09-21 — Qwen public partition rate-limit checkpoint\n\nThe frozen source/holdout pool remains unchanged. The first public-selection command was run after the manifest commit:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_multidomain_qwen.py --pool experiments/EXP-20260921-013-qwen-multidomain-holdout --partition public_selection --output experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-20260921 --workers 4 --timeout 120 --env-file C:\\Users\\pujan\\OneDrive\\Desktop\\configs\\.env`\n\nResult: `648` records, `197 ok`, `5 parse_error`, `446 rate_limited`. No failed provider response received a label. The output is retained as a separate provider execution artifact. A follow-up one-record smoke after the bulk request returned `rate_limited: 1`, confirming the provider rate limit was still active.\n\nThe runner now supports an explicit record-ID retry file so only unresolved public records can be retried later. `public-retry-record-ids.txt` contains `451` unresolved record IDs. No blind-holdout request has been made.\n\nDecision: preserve the partial public result and do not spend blind-holdout requests while the provider is rate-limited. Next atomic action: after a verified provider recovery, retry only the `451` public IDs at one worker, merge status-preserving outputs, and run the blind holdout only after public execution is either complete or explicitly checkpointed as provider-blocked.\n\n### 2026-09-21 — public Qwen retry and merge complete\n\nAfter the rate-limited smoke, a recovery smoke returned `ok: 1`. The bounded retry command was:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_multidomain_qwen.py --pool experiments/EXP-20260921-013-qwen-multidomain-holdout --partition public_selection --record-ids-file experiments/EXP-20260921-013-qwen-multidomain-holdout/public-retry-record-ids.txt --output experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-retry-20260921 --workers 1 --timeout 120 --env-file C:\\Users\\pujan\\OneDrive\\Desktop\\configs\\.env`\n\nRetry result: `451` requested records, `442 ok`, `9 parse_error`, zero rate limits. The immutable merge command was:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/merge_multidomain_qwen.py --pool experiments/EXP-20260921-013-qwen-multidomain-holdout --partition public_selection --base experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-20260921 --retry experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-retry-20260921 --output experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-public-merged-20260921`\n\nThe merged public result is `648` records: `639 ok`, `9 parse_error`, no fabricated labels. The nine parse errors remain unresolved. The frozen source and blind-holdout manifests were not changed.\n\nFiles changed: immutable retry/merged Qwen outputs, recovery smoke, root checksum manifest, and the runner retry-hint code. Next atomic action: run Qwen over the frozen `760`-record `blind_holdout` partition with one worker, preserving all status outcomes and no tuning from holdout labels.\n\n### 2026-09-21 — initial blind-holdout pass\n\nThe frozen blind-holdout command was:\n\n`D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_multidomain_qwen.py --pool experiments/EXP-20260921-013-qwen-multidomain-holdout --partition blind_holdout --output experiments/EXP-20260921-013-qwen-multidomain-holdout/qwen-blind-holdout-20260921 --workers 1 --timeout 120 --env-file C:\\Users\\pujan\\OneDrive\\Desktop\\configs\\.env`\n\nResult: `760` records, `438 ok`, `8 parse_error`, `314 rate_limited`. The initial holdout request used only the frozen typed packet; holdout labels were not used for any tuning or selection. `blind-retry-record-ids.txt` contains the `322` unresolved IDs.\n\nDecision: retain the initial holdout pass as immutable evidence and retry only its unresolved IDs after provider recovery. The eight parse errors and any remaining rate limits stay unresolved unless a bounded retry succeeds. Next atomic action: run a one-record recovery smoke, then retry the `322` blind IDs at one worker if the provider accepts requests.
