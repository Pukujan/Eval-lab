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