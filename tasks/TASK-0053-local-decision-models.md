# TASK-0053 — Local decision models on frozen and public benchmarks

## Status

Active — tracked by GitHub issue #47. EXP-027 and EXP-028 are in progress.
The MacBook Pro is reachable over Tailscale SSH. Kev-0.8B has
finished EXP-027 public and blind partitions and EXP-028 Hearsay with all
selected records resolved. Other model arms remain. Hardware is a 2020 MacBook
Pro (MacBookPro17,1), Apple M1, 16 GiB unified memory, macOS 26.4.1. The
fixed-choice adapters and resumable sequential runner are merged; the
string-state correction merged in PR #51. The pinned Kev runtime is installed
externally and passes package checks.

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
- `scripts/report_local_decision_bakeoff.py`
- `scripts/build_legalbench_hearsay.py`
- `tests/test_local_decision_models.py`
- `tests/test_local_decision_report.py`
- `tests/test_legalbench.py`
- `AGENTS.md`
- `D:\\claude\\AGENTS.md`

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

### 2026-09-24 — Mac runner access and model revisions established

Status: both experiments remain preregistered; no model inference has started.

Completed work: connected through the existing `mac-ts` SSH alias and verified
the host with `sw_vers`, `uname`, `system_profiler`, `sysctl`, and `df`. The
host is an Apple M1 MacBook Pro (MacBookPro17,1), 16 GiB unified memory, macOS
26.4.1, and had 22 GiB free disk. Python 3.14.5 and Homebrew are present, but
Python 3.12, uv, Ollama, MLX, PyTorch, Transformers, and Hugging Face Hub are
not available in the shell environment. Tailscale SSH succeeds using the
existing `mac-ts` host alias and account `teresaguajardo`.

Pinned current Hugging Face revisions: Qwen3.5-4B
`851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`; Nimble-9B
`bd792f44ec8e265be861bfcdf4e05967ffe0e858`; Kev-9B
`2629c06a5aeb0feb3b9783bafed17ed8f39ecf5c`; Kev-4B
`1da696f7938f77c4cdf5471e92fd342baff41778`; Kev-0.8B
`54f4f8777356cd5bbbb6c6919c657f26e6f2f6d8`; Laya
`55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`; and Verdict
`8af2496eb63c7fa66d7d234e1f62629380030eb4` (shared checkpoint for Verdict
1.4 and original runtime configuration).

Decisions: the user approved a narrowly scoped exception for model-specific
runtime environments on the Mac, outside any Eval Lab checkout; no Eval Lab
clone or copied project tree will be placed there. Run one model at a time and
record runtime/model revisions. Upstream says Nimble's unquantized 9B weights
alone need about 18 GB, so that arm is incompatible with this 16 GiB host and
will be recorded blocked unless the pinned runtime offers a validated exact
checkpoint path that fits. Other feasibility must be established by bounded
load smokes before benchmark scoring. Laya and Verdict document 512-token
limits, below EXP-027's 4096 cap; record truncation as a per-arm limitation.

Files changed: this task file, `checkpoints/CURRENT.md`, `AGENTS.md`,
`D:\\claude\\AGENTS.md`, EXP-027 `experiment.yaml`, `model-revisions.json`,
and `hardware-and-runtime.json`.

Commands run: workspace-policy check; Tailscale status and ping; SSH probe;
verified Mac hardware/runtime availability; fetched Hugging Face model metadata
for immutable revision SHAs and upstream Git commit SHAs; installed Homebrew
Python 3.12.14 and uv 0.12.18 on the Mac; fetched `origin/main`; synchronized
the task branch to the merged LegalBench checkpoint. No repo tests or model
inference have run after these edits; no benchmark commands have run.

Unresolved: install the approved Mac-side runner runtimes, determine exact
model-specific adapters and tokenization/truncation behavior, then run
one-record feasibility probes. The 22 GiB free-disk measurement should be
rechecked immediately before downloading weights.

Next atomic action: run the full checkpoint gates and publish the runner
implementation before any model call; then install the pinned Kev runtime
outside the checkout and smoke one record.

### 2026-09-24 — local runner implementation

Status: adapters and resumable per-record runner implemented; runner
checkpoint pending; no inference or benchmark scoring has started.

Completed work: added fixed-choice request construction for EXP-027 and
EXP-028; probability validation, retained raw outputs, explicit abstention,
context-limit and per-record failure statuses; adapters for SemIf, Kev, Laya,
and Verdict; a one-model-per-process JSONL runner that fsyncs each prediction
and resumes only missing record IDs. The runner accepts an explicit runner
revision and does not require copying the Eval Lab checkout to the Mac. Added
protocol tests covering gold-label exclusion, label stability, probability
normalization, abstention mass, and inconsistent backend outputs.

Files changed: `AGENTS.md`, `checkpoints/CURRENT.md`, this task file,
EXP-027 `experiment.yaml`, `hardware-and-runtime.json`, and
`model-revisions.json`, `scripts/run_local_decision_bakeoff.py`,
`src/eval_lab/judges/local_decision_models.py`, and
`tests/test_local_decision_models.py`.

Commands run: repository workspace-policy check passed; Ruff lint passed;
focused tests passed (`11 passed`). The first test attempt exposed floating
point representation in a conditional probability assertion; the check now
uses a rounded numeric comparison. No models were called.

Decisions: retain each native vector and reject malformed mass or selected
labels that disagree with its declared-choice argmax. Continue to condition
Verdict's legal-choice probabilities on non-abstention while retaining the
abstention probability. Write each record before reporting progress so an
interrupted arm can resume safely.

Unresolved: verify upstream runtime installation and a one-record Kev-0.8B
smoke; determine whether other model arms fit the host and produce supported
native probability outputs.

Next atomic action: publish the runner implementation after the complete local
gates pass; then install the pinned Kev runtime outside the checkout and smoke
one record.

### 2026-09-24 — runner checkpoint merged

Status: runner and preregistration are merged; no model calls have started.
GitHub issue #47 remains open for execution and reporting.

Completed work: PR #49 merged at `824dfdc0039fa07253a8128be1d00d65a8033dde`.
Required Python 3.11 and 3.12 CI checks passed. The local publisher gates also
passed, including repo contract, workspace policy, Ruff, mypy, full pytest,
and package build. Finalization verified the exact merge, updated issue #47,
audited checkout state, and synchronized canonical `main`. Began a fresh
runtime checkpoint branch from the merged commit. EXP-027 now names the merged
runner revision `aac7576441dc85a990023e2e5264a0ab4730e953`.

Files changed: `checkpoints/CURRENT.md`, this task file, and EXP-027
`experiment.yaml`.

Commands run: checkpoint publisher; required CI checks; PR finalizer; no model
inference or benchmark commands.

Decisions: continue the active TASK-0053 work on a fresh branch after the
runner PR merged. Record the exact merged runner commit in the preregistration
before any model call.

Unresolved: pinned Kev runtime install and Kev-0.8B smoke; per-model hardware
feasibility; full sequential scoring and metrics.

Next atomic action: publish the state serialization correction and runtime
pins; after required CI passes, smoke one EXP-027 public-selection record.

### 2026-09-24 — state protocol correction and Kev runtime prepared

Status: state serialization correction and runtime details are pushed on
`task/TASK-0053-local-model-state-protocol`; pull request pending. No model
weights or benchmark predictions exist.

Completed work: converted EXP-027's structured judgment state into canonical
JSON text so all backends receive the Jev-style string state. Focused tests
pass (`11 passed`). Installed the pinned Kev source revision
`badd506d71399f536a09bba7ad5dd663adb104d2` in a separate Mac Python 3.12
environment with the upstream `serve` extra and Apple Silicon backend.
`uv pip check` and `python -m kev.serve --help` passed. Captured resolved
packages in `kev-runtime-freeze.txt`. No model weights were downloaded and no
inference was performed.

Files changed: `checkpoints/CURRENT.md`, this task file, EXP-027
`experiment.yaml`, `hardware-and-runtime.json`, `model-revisions.json`,
`kev-runtime-freeze.txt`, `src/eval_lab/judges/local_decision_models.py`, and
`tests/test_local_decision_models.py`.

Commands run: Tailscale SSH; pinned `uv pip install`; `uv pip check`; Kev
server help; runtime package freeze; Ruff and focused tests. All passed.

Decisions: serialize typed context to JSON text at the shared adapter boundary;
keep the Mac runtime outside all project checkouts; pin the full Kev package
set before loading weights.

Unresolved: merge the correction and runtime record; confirm Kev-0.8B can load
and return a valid one-record choice; determine feasibility of remaining arms.

Next atomic action: checkpoint Kev-0.8B's predictions and reports, then start
the next feasible pinned model one at a time.

### 2026-09-24 — Kev-0.8B first benchmark runs

Status: Kev-0.8B completed EXP-027 public-selection (648/648), blind holdout
(760/760), and EXP-028 LegalBench Hearsay test (94/94). All records resolved
with `ok` status. EXP-027 and EXP-028 are marked in progress; additional model
arms remain.

Completed work: the one-record EXP-027 smoke loaded Kev-0.8B on the Mac M1
using MLX/BF16 and returned a valid `pass` decision with probabilities
0.7961/0.2039 in 2.26 seconds. Full public and blind runs used the exact
EXP-015 IDs; a local audit confirmed 648 and 760 unique expected IDs. The
LegalBench run returned exactly its 94 frozen test IDs. Preserved raw outputs,
server/runtime metadata, run configs, progress files, and the smoke artifacts.
Generated initial results and reports: blind accuracy 0.5026 (760 resolved,
100% coverage), public accuracy 0.4738, and LegalBench Hearsay accuracy 0.5426
(94 resolved). Calibration and class metrics are split by the EXP-027 single
and pairwise label spaces. Output SHA-256 values are in the `results.json`
summaries.

Files changed: both experiment manifests; EXP-027 raw output directories
`public-predictions/kev-0.8b/`, `blind-predictions/kev-0.8b/`,
`smokes/kev-0.8b-exp027-one-record/`, `results.json`, and `report.md`; EXP-028
`predictions/kev-0.8b/`, `results.json`, and `report.md`; new
`scripts/report_local_decision_bakeoff.py` and
`tests/test_local_decision_report.py`; this task file and `checkpoints/CURRENT.md`.

Commands run: Mac sequential runner for one smoke, 648 public records, 760
blind records, and 94 Hearsay records; local exact-ID/status validation and
SHA-256; initial metrics/report generation; Ruff and focused tests (`14
passed`). All three full runs reported all selected records as `ok`.

Decisions: keep the public smoke in a separate folder from scored outputs;
retain blind holdout as the primary accuracy; compute calibration and
class-balanced metrics within each fixed label space rather than pooling
single and pairwise labels.

Unresolved: finish the remaining feasible model arms, record hardware
infeasibility for Nimble-9B and Kev-9B without downloading oversized weights,
then regenerate aggregate reports and finalize both experiments.

Next atomic action: publish the Kev-0.8B raw predictions and validated reports;
after the checkpoint merges, begin the next feasible model arm sequentially.

## Handoff

Use this file as the task authority. Follow `checkpoints/CURRENT.md` for the
repository-wide next action. Do not run any model until the relevant
experiment preregistration is committed and the Mac runner is available.
