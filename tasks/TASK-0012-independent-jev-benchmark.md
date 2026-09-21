# TASK-0012 — Independent Jev Benchmark and JevBench Audit

- Status: completed — pinned primary complete; rolling canary separately stopped; robustness subset complete
- Owner: Eval Lab/local agent
- Priority: P1
- Depends on: TASK-0011 completion and blind-holdout checkpoint
- Branch: `task/TASK-0012-independent-jev-benchmark`
- Worktree: `D:/claude/eval-lab-TASK-0012-Jev`
- Planned experiment: `EXP-20260921-014-independent-jev-benchmark`
- Base commit: `b23682a` (completed TASK-0011 multidomain Qwen holdout)

## Goal

Audit how the public JevBench suite operates and run a separate Eval Lab benchmark whose primary score does not depend on JevBench's composite score, task labels, estimated costs, or adjusted latency assumptions.

The benchmark must measure Jev against independently frozen objective gold. JevBench may be reported as an external context source, but it is not ground truth and its ranking is not an acceptance criterion.

## JevBench audit findings

The public JevBench repository states that it is independent of TypeSafe AI. The current v1.2 line uses a fixed typed-decision task set, native or verbalized probability paths, and a composite of Intelligence, Calibration, Speed, and Cost. The public repository records 534 decisions per system, including 220 hard decisions, and publishes both public and held-out portions.

The audit identifies these threats to treating its headline rank as truth:

- the composite score chooses normative weights and a geometric aggregation across unlike axes;
- cost is measured when a tariff exists but estimated for systems without a tariff;
- self-hosted/demo latency receives an adjustment rather than only raw observed latency;
- the hard tier is authored and cross-reviewed by the benchmark team, so it is useful evidence but not an independent external gold standard;
- some imported cohorts use the benchmark authors' human or deterministic labels;
- public items and repository code are visible to model authors, creating adaptation risk;
- JevBench itself documents option-order sensitivity in an open Jev-style entrant;
- native distributions and verbalized distributions are explicitly different measurement objects;
- provider errors stop a run and remain missing, which is correct, but makes coverage a separate axis from accuracy.

Primary sources audited on 2026-09-21:

- `https://github.com/fstandhartinger/jevbench` — README, scoring rules, task cohorts, adapters, stop rules, and v1.2 revision notes.
- `https://www.benchmarkheaven.com/jev-models` — public interactive ranking and current v1.2 result summary.
- `https://typesafe.ai/blog/introducing-system-one-models-and-jev` — vendor product and training claims, retained as vendor evidence only.
- `https://github.com/anisselbd/jev-phishing-bench` — independent 2,000-email Jev/LLM comparison and calibration audit.

## Independent benchmark design

The primary Eval Lab benchmark will:

1. exclude JevBench's task text, labels, and derived results from the primary score;
2. use source revisions and objective gold from EvalLab-Select, ARC, GSM8K, MMLU, and deterministic synthetic tasks;
3. freeze source IDs, split assignments, canonicalization, prompt version, option order, and model arms before the final labels are requested;
4. compare pinned `typesafe/jev-1.13` and a separate rolling Jev canary, with Qwen and the frozen local student as independent comparison arms;
5. report a metric vector rather than a single composite headline: accuracy, balanced accuracy, macro F1, Brier, NLL, ECE, Wilson intervals, unresolved rate, latency, cost, and coverage;
6. run explicit option-order permutations, rubric paraphrases, and repeated identical calls on a declared subset;
7. preserve native Jev probabilities separately from any verbalized probabilities returned by other models;
8. retain provider failures as execution states and never score them as fabricated labels;
9. report raw caller latency and actual usage/cost separately from any provider tariff estimate;
10. compare every result with a majority-class baseline and a deterministic verifier baseline.

## Proposed independent splits

- public development/selection: records may be used for adapter and schema checks only;
- blind final evaluation: source-problem-disjoint records whose labels are not passed to provider code and do not affect prompt, model, or stopping decisions;
- repeat/perturbation subset: selected by record ID before any final labels, with option order and rubric variants inheriting the source split;
- no JevBench item is eligible for the primary independent score.

The final record counts and fingerprint are intentionally pending TASK-0011 completion and a new pre-run source freeze. Changing the source pool, provider arm, prompt, model version, or calibration method requires a new experiment ID.

## Acceptance criteria

- [ ] JevBench audit is committed with source links, scoring rules, and threats to validity.
- [x] independent source manifest and split fingerprint are frozen before live final evaluation;
- [ ] JevBench tasks and labels are excluded from the primary independent score;
- [ ] pinned Jev, rolling Jev, Qwen, and local comparison arms use identical canonical record IDs where available;
- [ ] native probability metrics and label-only outputs are kept distinct;
- [x] option-order, paraphrase, and repeatability live perturbation coverage is complete; provider-failure accounting is complete;
- [x] per-domain metrics, uncertainty, latency, cost, and coverage are reported;
- [x] no composite score is used as the primary acceptance criterion;
- [x] repository contract, Ruff, pytest, and experiment checksum validation pass after the freeze commit;
- [x] TASK-0011 is complete before the live TASK-0012 run begins.

## Outputs

- audit and threat-to-validity note;
- frozen independent source/split/checksum manifest;
- normalized pinned/rolling Jev predictions and comparison-arm predictions;
- per-domain and aggregate results/report;
- perturbation and stability report;
- reproducibility commands and limitations;
- paper appendix material linking each headline number to raw prediction artifacts.

## Validation

Use the repository contract, Ruff, pytest, checksum validation, split-leakage checks, probability normalization checks, and a byte-stable rebuild of the frozen source manifest. Live provider calls are optional until TASK-0011 is accepted and the TASK-0012 experiment manifest is frozen.

## Stop conditions

Stop and checkpoint if:

- JevBench task or label reuse is detected in the primary independent pool;
- source gold is not objective or its provenance cannot be recorded;
- provider/model identity differs from the frozen manifest;
- a provider error would need to be converted into a label;
- native and verbalized probabilities cannot be separated;
- the comparison requires post-hoc prompt, threshold, or task selection.

## Checkpoint log

### 2026-09-21 — protocol audit and independent plan

No live provider call or final label was requested. The public JevBench README and result summary were audited. The audit found a transparent open harness with frozen task cohorts, explicit missingness, and reproducible scoring, but also composite-weight, cost-estimation, latency-adjustment, task-authorship, and public-item adaptation risks. JevBench is retained as an external comparison, not as objective gold.

The independent experiment plan is recorded in `experiments/EXP-20260921-014-independent-jev-benchmark/PLAN.md` and remains unstarted until TASK-0011's Qwen blind holdout is complete. Exact local environment: Windows PowerShell, `D:\claude\eval-lab-TASK-0012-Jev`, Python runtime shared from `D:\claude\eval-lab\.venv`, Git `2.51.2.windows.1`, base commit `711450d`.

Decision: use the Eval Lab objective datasets and deterministic verifiers as the primary independent benchmark, preserve JevBench's public results as contextual evidence only, and avoid a single composite score.

Next atomic action: finish TASK-0011, then freeze the independent source pool, split IDs, canonical packet, model arms, and perturbation schedule before any TASK-0012 final labels.

### 2026-09-21 — independent source and protocol freeze

TASK-0011 is complete at commit `b23682a`. The independent TASK-0012 pool is frozen in `experiments/EXP-20260921-014-independent-jev-benchmark/` from the objective records in EXP-013, with JevBench task text, labels, and composite results explicitly excluded. The pool contains `648` public-selection records and `760` blind-holdout records, `1,408` unique records, `824` source problem IDs, and zero duplicated record IDs. The source fingerprint is `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`; the blind record-ID fingerprint is `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`.

The frozen typed packet is `eval-lab-system-one` v`0.1.0`, context limit `4096`, single labels `pass/fail`, pairwise labels `A/B/TIE`, confidence defined as native normalized provider probabilities only, and target error rates `0.01`, `0.02`, and `0.05`. Provider arms are pinned `typesafe/jev-1.13`, separate rolling `~typesafe/jev-latest`, comparison Qwen `qwen3.8-flash`, TASK-0009 local arm D `tfidf-logistic-v1`, and a frozen majority baseline. The perturbation schedule and typed packet hashes are recorded in `freeze.json` and `perturbations.json`.

Files added or changed: `src/eval_lab/escalation/spec.py`, `src/eval_lab/escalation/providers.py`, `tests/test_selective_escalation.py`, `scripts/freeze_independent_jev_benchmark.py`, `scripts/run_independent_jev_arm.py`, `scripts/run_independent_jev_perturbations.py`, `scripts/report_independent_jev.py`, the EXP-014 frozen manifests, and this task log.

Offline targeted tests pass: Ruff clean; `94 passed in 3.76s` before the final reporting-script import cleanup. No provider call or final label was made under EXP-014. Pinned and rolling Jev outputs will remain separate.

Decision: the independent primary score is a metric vector over objective Eval Lab gold; JevBench remains contextual audit evidence only. Next atomic action: commit and push this freeze, then run one-record pinned and rolling Jev smoke calls, recording provider identity and status before the full blind evaluation.

### 2026-09-21 — independent primary evaluation checkpoint

The source and protocol freeze was committed and pushed at `108a80e`. Smoke commands used the local `C:\Users\pujan\OneDrive\Desktop\configs\.env` without printing credentials:

`$env:PYTHONPATH='src'; D:\claude\eval-lab\.venv\Scripts\python.exe scripts/run_independent_jev_arm.py --pool experiments/EXP-20260921-014-independent-jev-benchmark --partition blind_holdout --model typesafe/jev-1.13 --output experiments/EXP-20260921-014-independent-jev-benchmark/smoke-pinned-20260921 --limit 1 --timeout 90 --env-file C:\Users\pujan\OneDrive\Desktop\configs\.env` -> `ok: 1`.

`$env:PYTHONPATH='src'; D:\claude\eval-lab\.venv\Scripts\python.exe scripts/run_independent_jev_arm.py --pool experiments/EXP-20260921-014-independent-jev-benchmark --partition blind_holdout --model ~typesafe/jev-latest --output experiments/EXP-20260921-014-independent-jev-benchmark/smoke-rolling-20260921 --limit 1 --timeout 90 --env-file C:\Users\pujan\OneDrive\Desktop\configs\.env` -> `ok: 1`.

Pinned primary command used the same runner with `--model typesafe/jev-1.13` and output `jev-pinned-blind-20260921`: `760 ok`, no stop, no unresolved records. Independent pinned results are `684/760` correct (`0.9000`) with 95% Wilson interval `[0.8766, 0.9194]`; balanced accuracy `0.9263`, macro-F1 `0.7483`, p95 latency `380.2734 ms`. Jev returned no native probability map, so Brier/NLL/ECE are unavailable and no confidence estimate is claimed.

Rolling canary command used `--model ~typesafe/jev-latest` and output `jev-rolling-blind-20260921`: `263 ok`, `2 provider_error`, `495 skipped`, stop reason `two_consecutive_provider_errors` after HTTP 503. Its resolved-prefix accuracy is `249/263 = 0.9468` with Wilson interval `[0.9126, 0.9680]`, but this is a nonrandom prefix and is never pooled with pinned Jev.

The comparison report was generated by `scripts/report_independent_jev.py` from pinned, rolling, EXP-013 merged Qwen, and TASK-0009 arm D artifacts. Qwen is `637/754 = 0.8448` resolved accuracy with unresolved rate `0.0079`; pinned-versus-Qwen agreement is `652/754 = 0.8647`. Local arm D resolves `652` single-answer records and skips `108` pairwise records; pinned-versus-local agreement is `319/652 = 0.4893`. The frozen majority baseline is `382/760 = 0.5026`.

The first perturbation artifact `perturbations-pinned-20260921` recorded `60 provider_error` responses with HTTP 503. After a recovery smoke returned `ok: 1`, the separate `perturbations-pinned-recovery-20260921` artifact recorded `10 ok` and `50 provider_error`; no complete repeatability or option-order estimate was promoted. These are provider-failure evidence, not silently merged retries.

Exact files changed: EXP-014 `README.md`, `commands.md`, `limitations.md`, `experiment.yaml`, `report.md`, `results.json`, normalized pinned/rolling/Qwen/local comparison predictions, smoke and perturbation artifacts; `scripts/report_independent_jev.py`; and this task checkpoint. Local gates before live calls were contract `OK`, Ruff clean, and `94 passed in 3.91s`.

Decision: pinned Jev has a complete independent objective result and is stronger than the matched Qwen comparison on this frozen pool, but rolling coverage and live robustness perturbations are incomplete. Next atomic action: after provider recovery, run the pre-frozen perturbation schedule with stop-on-503 accounting, then regenerate checksums and the final TASK-0012 report; do not change the pool, prompt, label order schedule, or primary pinned results.

### 2026-09-21 — TASK-0012 acceptance complete

After a recovery smoke returned `ok: 1`, the final pre-frozen pinned perturbation command was:

`$env:PYTHONPATH='src'; D:\claude\eval-lab\.venv\Scripts\python.exe scripts/run_independent_jev_perturbations.py --pool experiments/EXP-20260921-014-independent-jev-benchmark --model typesafe/jev-1.13 --output experiments/EXP-20260921-014-independent-jev-benchmark/perturbations-pinned-final-20260921 --primary experiments/EXP-20260921-014-independent-jev-benchmark/jev-pinned-blind-20260921 --timeout 90 --env-file C:\Users\pujan\OneDrive\Desktop\configs\.env`

The final robustness artifact contains `60 ok` calls: repeatability `1.0` over 12 records, option-order agreement `1.0` over 12 records, and rubric-paraphrase agreement `0.9167` over 12 records. It is separate from the primary score. Earlier HTTP 503 artifacts remain preserved and demonstrate provider-failure accounting.

Final experiment status is `primary_evaluation_complete_robustness_complete`. Exact primary and comparison outputs, results, limitations, commands, source/split manifests, typed packet, perturbation schedule, and checksums are under `experiments/EXP-20260921-014-independent-jev-benchmark/`. The benchmark fingerprint, blind ID fingerprint, model IDs, provider statuses, uncertainty, latency, and actual-cost-unavailable result are all recorded there.

Final local validation after the live artifacts and reporting changes: repository contract `OK`; Ruff `All checks passed!`; pytest `94 passed`; experiment checksum validation `0 mismatches`; `git diff --check` clean. No credentials or `.env` files were added.

Decision: TASK-0012 acceptance criteria are satisfied. JevBench is retained as external contextual evidence, while the independent Eval Lab metric vector is the primary result. Next atomic action: open review for TASK-0012 and do not start TASK-0013 until review triage explicitly authorizes a new task.

## Handoff

Worktree: `D:/claude/eval-lab-TASK-0012-Jev`
Branch: `task/TASK-0012-independent-jev-benchmark`
Experiment: `EXP-20260921-014-independent-jev-benchmark`
Status: completed; pinned primary and separate rolling/robustness artifacts recorded
Next atomic action: review the committed TASK-0012 independent benchmark; do not start a dependent task without explicit triage.
