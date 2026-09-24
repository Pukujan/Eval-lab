# TASK-0053 — Local decision models on frozen and public benchmarks

## Status

Active — tracked by GitHub issue #47. EXP-027 and EXP-028 are being
preregistered. No model calls or benchmark scoring have started. The requested
MacBook Pro did not answer over Tailscale during setup; machine details and
runner access remain unresolved.

## Objective

Measure the user-provided small, Jev-style decision models one at a time on
the same frozen Eval Lab records, then run them on a small public legal
classification task with explicit labels. Preserve published benchmark claims
as context only; report only results produced from the pinned local runs.

## Goal

Produce a reproducible, one-model-at-a-time comparison of the requested
decision models on Eval Lab's frozen test pool and the pinned LegalBench
Hearsay task, with results and statuses recorded in GitHub.

## Scope

- `checkpoints/CURRENT.md`
- `tasks/TASK-0053-local-decision-models.md`
- `experiments/EXP-20260924-027-local-decision-bakeoff/`
- `experiments/EXP-20260924-028-legalbench-hearsay/`
- `src/eval_lab/judges/local_decision_models.py`
- `src/eval_lab/datasets/legalbench.py`
- `scripts/run_local_decision_bakeoff.py`
- `scripts/build_legalbench_hearsay.py`
- `tests/test_local_decision_models.py`
- `tests/test_legalbench.py`

## Experiment plan

JevBench is the closest existing external harness because it uses typed
choices and native probability outputs. Its public results already include
several requested systems, and its current release includes sealed items, so
it will be used as context rather than a claimed independent replication.
Links: [JevBench](https://github.com/fstandhartinger/jevbench),
[LegalBench Hearsay](https://hazyresearch.stanford.edu/legalbench/tasks/hearsay.html).
The Hearsay task is the second, independently sourced public test.

### EXP-027 — frozen Eval Lab comparison

Use the exact EXP-015 dataset fingerprint, 648 public-selection records, and
760 blind-holdout records with its typed-choice protocol. Keep EXP-014,
EXP-015, and EXP-025 complete and immutable. Run these eight configurations
sequentially, preserving separate raw output directories:

1. SemIf with Qwen3.5-4B
2. Bespoke Nimble-9B
3. Kev-9B
4. Kev-4B
5. Kev-0.8B
6. Laya 421M
7. OpenJev Verdict 1.4
8. original Verdict configuration using the shared weights where applicable

Compare blind accuracy and resolved coverage as primary metrics. Record
balanced accuracy, macro F1, native-probability availability, Brier, NLL, ECE,
latency, and status counts where supported. Fit optional temperature scaling
only from public-selection outputs; retain raw scores and keep the blind
partition out of all model, prompt, and calibration choices. Use the cached
Jev 1.13 result on the identical blind records as a reference where its
protocol is compatible.

### EXP-028 — LegalBench Hearsay

Use the official fixed-label Hearsay task from the pinned source manifest. Its
page reports 100 cases with 5 train and 95 test, while the pinned machine-
readable source contains 5 train and 94 test rows. Keep the source's 94 test
rows exactly as distributed, record this discrepancy, and do not invent the
missing item. Keep LegalBench metrics separate from EXP-027. Do not imply
that this one task represents general legal reasoning.

## Experiment rules

- Keep model configurations, source revisions, prompts, protocol and outputs
  pinned. An unavailable or incompatible model is recorded as blocked with
  reason; do not silently substitute another checkpoint or runtime.
- Record Mac hardware and OS, inference backend, quantization, model revision
  and hashes, per-record status, raw label/probability output, and latency.
- Use only the benchmark's declared answer labels. Invalid output, timeout,
  load failure, or memory exhaustion is a status and is not counted as a wrong
  answer unless a separate operational metric says so.
- Never overwrite completed experiment results. Model or protocol changes
  require a new experiment identity.

## Acceptance criteria

1. Both experiments are preregistered and the LegalBench task source and
   license are recorded before inference.
2. All eligible EXP-027 arms use identical frozen record IDs and protocol;
   each is run one at a time with status-preserving outputs.
3. EXP-028 retains source item IDs, gold provenance, fixed labels, declared
   split, license, and a reproducible fingerprint.
4. Reports include raw outputs or their fingerprints, metrics, latency,
   coverage, statuses, and limits of comparison.
5. Required local and GitHub gates pass, and the checkpoint is merged before
   switching the canonical task branch.

## Checkpoint log

### 2026-09-24 — task opened

Status: experiment setup; no models executed. GitHub issue #47 created.

Completed work: confirmed EXP-025 is complete; identified EXP-015 as the
frozen 1,408-record pool (648 public, 760 blind), and EXP-014 Jev 1.13 as a
compatible reference result. Audit found LegalBench Hearsay is a small,
fixed-label candidate. Its task page states CC BY 4.0 and claims 95 test rows;
the pinned machine-readable source contains 94. The MacBook Pro was
unreachable over Tailscale.

Files changed: this task file and `checkpoints/CURRENT.md`.

Commands run: repository status and model/experiment inventory; no model
inference commands. No tests run in this checkpoint.

Decisions: new model arms use a new experiment ID and cannot alter completed
results; choose an existing public benchmark task with fixed labels rather
than inventing examples.

Unresolved: Mac runner access and hardware, exact upstream model revisions and
runtime compatibility, LegalBench canonical fingerprint, and whether each
model exposes validated native probabilities.

Next atomic action: build and fingerprint canonical Hearsay records from the
pinned source files, then establish Mac runner access before model calls.

### 2026-09-24 — LegalBench source frozen

Status: LegalBench source and canonical test records are frozen; local-model
runner is not implemented; no inference has started. GitHub issue #47 remains
open.

Completed work: pinned the LegalBench dataset revision and its official
Hearsay task documentation; downloaded and hashed the train/test TSVs and
official base prompt; built 94 canonical test records. The published task
page reports 95 test records, but the pinned source contains 94. The frozen
source is used without filling in the missing index. Dataset fingerprint:
`4b516314fd01454972e975d4da11c4f843841e5e20427f95a4bdeb8c67a18650`.

Files changed: `checkpoints/CURRENT.md`, this task file,
`experiments/EXP-20260924-027-local-decision-bakeoff/README.md`,
`experiments/EXP-20260924-027-local-decision-bakeoff/experiment.yaml`,
`experiments/EXP-20260924-027-local-decision-bakeoff/source-pool-fingerprint.json`,
`experiments/EXP-20260924-028-legalbench-hearsay/README.md`,
`experiments/EXP-20260924-028-legalbench-hearsay/experiment.yaml`,
`experiments/EXP-20260924-028-legalbench-hearsay/source-manifest.json`,
`experiments/EXP-20260924-028-legalbench-hearsay/source/`,
`experiments/EXP-20260924-028-legalbench-hearsay/canonical-records.jsonl`,
`src/eval_lab/datasets/legalbench.py`,
`scripts/build_legalbench_hearsay.py`, and `tests/test_legalbench.py`.

Commands run: fetched pinned public TSV/prompt sources, recorded SHA-256 hashes,
built canonical JSONL, ran the workspace-policy check, ran the focused Hearsay
tests (`7 passed`), and ran Ruff on changed Python files (passed).

Decisions: retain all 94 pinned test rows as distributed; keep this legal
classification score separate from EXP-027; use official few-shot base prompt
for all model arms. The model audit found model-specific adapters are needed;
Nimble's documented Apple Silicon setup requires a separate MLX environment,
which conflicts with the one-environment rule.

Unresolved: Mac access and hardware details; adapter/runtime compatibility for
each model; how Nimble can run within project environment policy; calibration
output availability. No benchmark model has run.

Next atomic action: make the MacBook reachable, establish exact model and
runtime pins, and resolve Nimble's runtime environment before adding the
model-specific execution adapters and launching the first sequential run.

## Handoff

Use this file as the task authority. Follow `checkpoints/CURRENT.md` for the
repository-wide next action. Do not run any model until the relevant
experiment preregistration is committed and the Mac runner is available.
