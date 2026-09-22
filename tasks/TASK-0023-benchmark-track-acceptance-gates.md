# TASK-0023 — Benchmark Track Acceptance Gates

## Status

Planning checkpoint. No provider calls, benchmark downloads, benchmark
executions, or experiment mutations are authorized by this task.

## Objective

Define acceptance criteria for six independent benchmark tracks so that each
track can be admitted to Eval Lab only after its data provenance, adapter,
verifier, environment, reproducibility, and audit obligations are explicit.
The tracks are:

1. ARC-AGI-1/2
2. LegalBench objective subset
3. FinanceBench objective subset
4. SWE-bench or DeepSWE
5. OSWorld
6. Humanity's Last Exam (HLE)

Each track is a separate experiment. No blended leaderboard score may combine
these tracks, and no completed experiment may be overwritten.

## Non-negotiable policy

- Deterministic gold must come from an executable/deterministic verifier, a
  trusted benchmark answer key, or an explicitly documented human
  adjudication process. The provenance category is recorded per record.
- A model judge's answer, confidence, preference, rubric score, or consensus
  is an evaluated output, never deterministic gold merely because the model is
  strong. Judge-dependent scores are excluded from deterministic gold and are
  reported in a separate adjudicated or model-supervised track.
- Provider failures, malformed outputs, timeouts, and execution failures are
  separate status values. They are not silently converted into wrong answers.
- Every release retains source problem IDs, dataset revision/commit, license or
  access terms, source URL, split policy, source-family isolation, fingerprint,
  normalization/tolerance rules, runtime versions, and rebuild checksums.
- Direct provider policy is preserved: no OpenCode; no OpenRouter except the
  Jev-only route; Grok only through the direct authenticated xAI `grok` CLI.

## Common acceptance model

Every track must pass all five gates below. A later gate cannot waive an unmet
earlier gate. The task file for the eventual implementation must record the
status, evidence, exact files, commands, test results, decisions, unresolved
questions, and next atomic action at each stopping point.

### Feasibility gate

Accept only when access/licensing and the dataset revision are identified; the
objective-strength tier is assigned per candidate item; the environment and
resource budget are documented; and an implementable scorer/verifier exists.
The feasibility record must state which items are excluded and why.

### Adapter gate

Accept only when a mocked, offline runner emits canonical JSONL records that
retain source IDs and typed inputs/outputs; fingerprints and deterministic
splits are tested; the scorer/verifier has unit tests; and malformed output,
abstention, timeout, and execution failure are represented separately from
incorrect answers. No provider labels are needed for this gate.

### Preregistration gate

Accept only after committing the dataset revision, sample and split, source
family policy, prompt/rubric and packet version, model arms and routes, seed,
context/environment limits, calibration split, primary metrics, exclusion and
stopping rules, and the deterministic-gold policy. Final evaluation labels are
not used to fit calibration or select models.

### Execution gate

Accept only after a bounded smoke validates the adapter and verifier, exact
surfaced model IDs and route metadata are captured, and the frozen pool is run
into a new output directory. Raw normalized predictions or an auditable
fingerprint are retained. No provider route is substituted silently.

### Audit gate

Accept only after answer metrics and calibration metrics are computed from the
frozen outputs; verifier failures and exclusions are inspected; agreement and
consistency checks are reported where applicable; checksums and rebuild steps
are published; and deterministic results are visibly separated from
adjudicated or judge-dependent results. The report must state limitations,
contamination risk, environment assumptions, and unresolved ambiguity.

## Track-specific gates

### 1. ARC-AGI-1/2 — exact structured grid transformation

**Feasibility gate:** Freeze the exact ARC-AGI release/revision and license or
access terms. Classify each item as Tier A only when predicted grids can be
compared by exact cell, shape, and color match; otherwise classify it as Tier B
when a trusted answer key is used. Record task metadata and any alternate
answer representation. Confirm that the selected slice fits the common context
envelope and that structured output parsing is implementable.

**Adapter gate:** Canonicalize task IDs, training examples, test inputs, and
gold test grids without lossy serialization. The verifier must reject malformed
dimensions, invalid colors, extra cells, and missing outputs distinctly, then
perform exact-grid comparison. Unit tests must cover identity, shape changes,
wrong colors, extra/missing cells, and serialization round trips. Keep
source-family/task variants in one split.

**Preregistration gate:** Freeze release, task sample, train/test presentation,
output schema, parser/normalizer, split and family-isolation rule, calibration
records, structured judge packet, metrics, and timeout/output limits. No
human/model judgment may repair an invalid grid for the deterministic score.

**Execution gate:** Run parser/verifier smoke cases and a bounded structured
output smoke before the frozen pool. Preserve model IDs, route metadata,
prompt version, raw normalized grids, parse status, and per-test exact-match
results. Keep test answers unavailable to calibration or prompt selection.

**Audit gate:** Report exact-grid accuracy and per-task failure categories,
including parse, dimension, color, and semantic mismatch. Publish task and
artifact fingerprints, split proof, verifier tests, checksums, and a separate
analysis for any human or model interpretation of ambiguous transformations.

### 2. LegalBench objective subset — rule application/classification/extraction

**Feasibility gate:** Select only tasks with an explicit answer key or a
deterministic normalized label/extraction target. Record task-level provenance,
revision, license/access terms, label ontology, and whether examples are
independent or share a source family. Exclude open-ended legal explanations,
policy judgments, or disputed labels from deterministic gold unless they gain a
documented human-adjudication protocol.

**Adapter gate:** Preserve task name, source item ID, input fields, label set,
and gold provenance. Implement exact label matching and task-specific
normalization only where it is declared and tested; never use a judge to map a
free-form answer to gold during scoring. Tests must cover casing/whitespace,
multi-label ordering where permitted, invalid labels, missing fields, and
task-specific exclusions.

**Preregistration gate:** Freeze the task inventory, revision, label mapping,
source-family split, typed packet, normalization rules, calibration partition,
metrics by task and macro-aggregate, and exclusion list. State whether the
primary result is exact classification/extraction only; explanations and legal
rationales are a separate judge-dependent analysis.

**Execution gate:** Validate one or more records from every included task,
including invalid-output cases, before execution. Preserve task-level model
and route metadata, normalized labels, abstentions, and provider/runtime
statuses. Do not silently replace a task with another legal dataset or label
mapping.

**Audit gate:** Report per-task and macro metrics, label imbalance, unmapped or
excluded records, and provenance coverage. Audit the answer key and any
normalizer against fixtures. Publish separate tables for deterministic labels,
human adjudication, and judge-dependent rationale quality; only the first may
enter the deterministic objective score.

### 3. FinanceBench objective subset — numeric answer and evidence retrieval

**Feasibility gate:** Select items with a frozen numeric answer and explicit
units/period, or with a trusted answer key plus a declared evidence target.
Record source documents, revision/access terms, answer provenance, currency and
rounding conventions, and retrieval boundaries. Exclude free-form financial
explanations from deterministic gold unless evidence quality receives a
separate adjudication protocol.

**Adapter gate:** Canonicalize question, source/document identifiers, numeric
answer, units, currency, time period, and evidence spans/citations. Implement
declared numeric tolerance and unit/currency normalization, with tests for
rounding, signs, percentages, scale suffixes, missing units, non-numeric
answers, and citation/evidence mismatches. A judge must not decide whether an
explanation is “close enough” for the objective label.

**Preregistration gate:** Freeze the item/document revision, retrieval corpus
and allowed context, numeric tolerance, evidence/citation scoring policy,
split and document-family isolation, typed packet, calibration split, metrics,
and exclusions. Define separate primary metrics for numeric correctness and
evidence retrieval; do not merge them into an unqualified explanation score.

**Execution gate:** Run numeric and evidence verifier smoke fixtures, including
unit conversion and missing-citation failures. Preserve model IDs, retrieved
document IDs/spans, normalized numeric outputs, parse status, and route/runtime
metadata. Do not count unavailable source documents or provider errors as
financially incorrect answers.

**Audit gate:** Report numeric exact/tolerance accuracy, evidence precision or
recall under the declared rule, citation failures, and coverage by unit/currency
class. Reconcile every gold answer to its source revision and checksum. Place
free-form explanation quality, if evaluated, in a separately labeled
adjudicated/judge-dependent report.

### 4. SWE-bench or DeepSWE — repository-level code repair

**Feasibility gate:** Choose one named release and task subset, with repository
commits, issue statements, licenses, and environment images or setup commits
identified. Require an executable patch verifier consisting of patch
application plus the benchmark's declared tests, with explicit security and
network policy. Confirm disk, CPU/GPU, runtime, timeout, and parallelism budget;
otherwise defer the track.

**Adapter gate:** Canonicalize instance ID, base commit, issue, repository
revision, patch format, test command, environment image, and test outcome.
Tests must cover clean patch application, no-op/invalid patches, test
collection failures, timeouts, flaky tests, and partial environment setup.
The verifier must distinguish patch failure, infrastructure failure, failing
tests, and passing tests. Any human review of patch quality is non-objective
supplementary evidence.

**Preregistration gate:** Freeze release/subset, base commits, environment
image digest, patch/application policy, test command and timeout, network and
secret policy, split/contamination policy, calibration records, model arms,
and primary pass/fail metrics. Decide in advance how flaky or infrastructure
failed instances are excluded and reported.

**Execution gate:** Rebuild and smoke-test the environment on representative
repositories before the frozen pool. Preserve patch artifacts or secure
fingerprints, base commit, image digest, test logs/status summaries, model IDs,
route metadata, and resource usage. Never rerun a changed environment into an
existing experiment directory.

**Audit gate:** Reproduce patch application and test outcomes from the recorded
commits and image digest; report pass rate, failure categories, timeout and
infrastructure rates, and contamination notes. Keep issue-resolution judgments,
code-quality ratings, and model-judge scores outside deterministic pass/fail
gold unless separately adjudicated.

### 5. OSWorld — computer-use task completion

**Feasibility gate:** Confirm access to the exact task release, application
versions, VM/container images, network policy, and licenses. Require a
replayable isolated VM snapshot and task-specific state assertions or files
that can deterministically verify completion. Defer any task whose success
criterion is only a human impression or an unlogged GUI state.

**Adapter gate:** Canonicalize task ID, initial snapshot/image digest, allowed
apps and network, action/input contract, success assertions, reset procedure,
and timeout. Tests must cover clean reset, successful state transition,
partial completion, wrong state, crash, lost connection, and assertion failure.
The adapter must separate environment failure from task failure and preserve
event/action logs without credentials.

**Preregistration gate:** Freeze task release, VM image and snapshot,
application versions, task sample and split, action/time limits, reset and
retry policy, state assertions, calibration split, model arms/routes, and
primary completion metrics. Human video review or a judge's task-success score
is excluded from deterministic gold unless explicitly adjudicated as a separate
track.

**Execution gate:** Recreate the snapshot and run a bounded end-to-end smoke
with the same isolation, display, input, network, and timeout settings as the
frozen pool. Preserve image digests, surfaced model IDs, action/event logs,
assertion outputs, resets, crashes, and route metadata. Do not treat a missing
VM or GUI service as a task miss.

**Audit gate:** Re-run state assertions from recorded snapshots/logs, report
completion by task family and failure category, and publish image/setup
checksums plus replay instructions. Separate deterministic state completion
from human usability, trajectory quality, or judge-dependent visual ratings.

### 6. Humanity's Last Exam — audited answer-key subset

**Feasibility gate:** Inventory modality, subject, answer type, source revision,
license/access terms, and answer-key status per item. Admit an item to the
deterministic subset only when an audited answer key and a deterministic
normalization rule exist; otherwise classify it as adjudicated/ambiguous and
exclude it from deterministic gold. Record image/audio/document preprocessing
requirements and expert domain dependencies.

**Adapter gate:** Canonicalize item ID, modality, prompt/assets, answer type,
answer key provenance, accepted aliases, and normalization. Tests must cover
exact choice, numeric/string normalization, multiple valid aliases where
explicitly authorized, missing assets, malformed outputs, and unsupported
modalities. No model consensus may create or upgrade an answer key.

**Preregistration gate:** Freeze release, audited key revision, item subset,
asset fingerprints, modality preprocessing, accepted-answer rules, split and
subject-family isolation, typed packet, calibration split, metrics, and
exclusion/adjudication policy. Declare a separate endpoint for items requiring
expert adjudication; it must not be mixed into deterministic accuracy.

**Execution gate:** Validate representative text, image, and other included
modalities offline before a bounded model smoke. Preserve asset/key
fingerprints, normalized answers, parse status, model IDs, route metadata,
context limits, and modality/runtime failures. Do not substitute a judge's
interpretation for a missing key during execution.

**Audit gate:** Reconcile every deterministic item to its audited key and
asset revision; report accuracy by subject, modality, answer type, and
provenance tier. Publish checksums and preprocessing/rebuild instructions.
Report expert adjudication, open-ended explanations, and judge-dependent
scores in a visibly separate table with their uncertainty and limitations.

## Planned deliverables and boundaries

This planning task changes only this task file. Future implementation tasks
must create a new experiment directory under `experiments/` and declare their
files before editing them. They must not download benchmark data, call
providers, or modify EXP-014 through EXP-019 as part of this task.

Expected future evidence, per track, is an adapter contract and tests, a frozen
experiment manifest, smoke/execution outputs, a verifier audit, a report, and
checksums/rebuild instructions. Track status is not complete until all five
track-specific gates are satisfied.

## Validation and checkpoint record

### Completed work

- Read `PROJECT.md`, `checkpoints/CURRENT.md`,
  `docs/EXPERIMENT_PROTOCOL.md`, `docs/BENCHMARK_EXPANSION_ROADMAP.md`, and
  `AGENTS.md`.
- Defined separate feasibility, adapter, preregistration, execution, and audit
  gates for ARC-AGI, LegalBench objective subset, FinanceBench objective
  subset, SWE-bench/DeepSWE, OSWorld, and HLE.
- Recorded objective-gold provenance, verifier strength, environment and
  reproducibility requirements, and the exclusion of judge-dependent scores
  from deterministic gold.
- Preserved the direct-provider policy and the planning-only boundary.

### Exact files changed

- `tasks/TASK-0023-benchmark-track-acceptance-gates.md`

### Commands run

- Read the required repository and design files with PowerShell.
- Listed task filenames to confirm the next task number.
- No provider calls, benchmark downloads, experiment executions, or external
  writes were performed.

### Test results

- `git diff --check` passed with no whitespace errors.
- `git status --short` shows only the new task file.

### Decisions made

- Keep all six benchmark families as separate experiments.
- Treat deterministic execution, trusted answer keys, and explicitly sourced
  adjudication as distinct provenance categories.
- Exclude judge-dependent scores from deterministic gold and report them
  separately.
- Treat environment/infrastructure failures as statuses, not wrong answers.

### Unresolved questions

- The exact dataset revisions, subset inventories, licenses, and environment
  images remain to be selected by future implementation tasks.
- The SWE-bench versus DeepSWE choice remains open until sandbox capacity and
  runtime budget are confirmed.

### Next atomic action

Run final diff/whitespace validation, commit this task file with
`TASK-0023: define benchmark acceptance gates`, and hand off the planning
checkpoint. Do not begin adapter implementation in this task.
