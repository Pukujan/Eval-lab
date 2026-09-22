# TASK-0021 — Benchmark expansion roadmap decomposition

## Status

Planned and ready for review. This task is planning-only: it authorizes no
provider calls, benchmark execution, dataset download, hidden-test access, or
modification of existing experiment artifacts.

## Objective

Turn `docs/BENCHMARK_EXPANSION_ROADMAP.md` into a dependency-ordered queue of
implementation tasks that extends Eval Lab with independently auditable
objective benchmark families. The queue preserves Eval Lab as the canonical
research and artifact layer while allowing an optional Inspect AI harness
adapter behind the declared contract.

## Scope and non-negotiable boundaries

- EXP-014, EXP-015, EXP-016, EXP-017, EXP-018, and EXP-019 are immutable. No
  task below may edit, overwrite, relabel, rerun into, or mix outputs with
  those experiments.
- Every changed dataset revision, sample, rubric, prompt, model arm, seed,
  calibration method, or evaluation protocol receives a new experiment ID and
  a new preregistration before final evaluation.
- The benchmark families remain separate. There is no blended leaderboard
  score across HumanEval, ARC, LegalBench, FinanceBench, SWE-bench/DeepSWE,
  OSWorld, or Humanity's Last Exam.
- Eval Lab owns manifests, canonical records, source-family splits,
  provenance, typed judge packets, calibration, deterministic perturbations,
  provider metadata, metrics, checksums, and research reports. Inspect AI may
  supply a task/solver/scorer/sandbox harness only when its outputs are wrapped
  and verified by the Eval Lab adapter contract.
- No OpenCode route is permitted.
- OpenRouter is permitted only for an explicitly scoped Jev arm. It is not a
  route for Grok, Luna, Sol, Qwen, or any other arm.
- Grok may run only through the direct authenticated xAI `grok` Build CLI. A
  route failure is execution metadata, never an answer label or silent
  fallback.
- Luna and Sol, if later included by an experiment's explicit preregistration,
  use the authenticated Codex-subscription route. They are not automatic
  substitutions for another arm.
- Local Qwen and Jev remain separate judge/reference resources and are not
  silently pooled with external-provider labels.
- No credentials, private benchmark material, downloaded datasets, raw
  provider transcripts, or model caches may be committed.

## Dependency-ordered task queue

Each numbered item below is a separate task, branch, worktree, review, and
checkpoint. A task may modify only the files declared in its own task file; if
scope changes, update that task file before editing additional files.

### Foundation and first track

#### TASK-0022 — HumanEval feasibility, source audit, and preregistration

Depends on: TASK-0019 and this decomposition.

Create the HumanEval feasibility record and freeze the intended source revision,
license/access terms, sample policy, executable-test policy, sandbox limits,
typed judge packet, calibration split, metrics, exclusions, stopping rule, and
report schema. Assign the new experiment identity `EXP-020` without creating
provider outputs. Confirm that the selected task set and tests can be handled
without committing benchmark data or hidden material.

Acceptance criteria:

- The preregistration names the exact source revision, source URL, license,
  task/sample fingerprint procedure, split policy, source-family policy, and
  gold provenance as executable-test pass/fail.
- The packet distinguishes generated code, verifier result, provider status,
  malformed output, timeout, sandbox failure, and abstention.
- Calibration/development/final partitions and all primary metrics are frozen
  before any final test execution.
- Sandbox and security assumptions have a bounded, reproducible setup plan.
- No provider is invoked and no benchmark data or hidden test material is
  downloaded or committed.

#### TASK-0023 — HumanEval canonical adapter and deterministic verifier

Depends on: TASK-0022.

Implement the HumanEval source-to-canonical-record adapter, typed code-output
contract, deterministic split/fingerprint machinery, and isolated executable
verifier. The adapter must retain each source problem ID and make execution
failure distinct from an incorrect answer.

Acceptance criteria:

- Adapter tests cover canonical serialization, source IDs, fingerprinting,
  split isolation, output normalization, timeout, malformed code, verifier
  failure, and abstention.
- The verifier runs with explicit resource and filesystem/network policy, and
  tests demonstrate that the policy is applied.
- A mocked or fixture-only runner produces normalized records without a
  provider call.
- The adapter emits provenance and checksums sufficient to rebuild the
  canonical pool; no raw benchmark payload is committed unless separately
  approved by repository policy.

#### TASK-0024 — HumanEval judge packet, route adapters, and audit report

Depends on: TASK-0023.

Add the HumanEval judge packet and provider-neutral execution contract, then
wire only explicitly authorized routes. Preserve direct route metadata and
failure states, and produce an EXP-020 report that keeps executable correctness
separate from calibration and provider reliability.

Acceptance criteria:

- Mock/contract tests cover Jev-only OpenRouter routing, direct xAI Grok Build
  CLI routing, local Qwen routing, and optional direct Codex Luna/Sol routing
  without permitting OpenCode or unauthorized OpenRouter use.
- Any live smoke, if separately authorized after preregistration, records the
  surfaced model ID, command/version, route, status, latency, and checksum;
  it never converts a route failure into an answer.
- Final execution cannot start until the frozen manifest and packet are
  committed, and final artifacts are written to a new EXP-020 directory.
- Report tables contain answer metrics, calibration metrics, verifier failure
  counts, consistency checks, risk/coverage where applicable, and limitations.

### Structured reasoning track

#### TASK-0025 — ARC-AGI feasibility and exact-grid preregistration

Depends on: TASK-0024 adapter/report patterns and TASK-0022's preregistration
gate.

Freeze the ARC-AGI revision, task subset, grid representation, answer format,
exact-match policy, metadata, contamination notes, partitions, and typed judge
packet as `EXP-021`. Decide whether ARC-AGI-1, ARC-AGI-2, or a declared subset is
in scope before any source retrieval.

Acceptance criteria:

- Exact grid equality and representation normalization are specified with
  executable examples and no subjective fallback in the deterministic track.
- Revision, license/access terms, task fingerprint, split/family policy,
  calibration split, and final metrics are frozen.
- Any non-exact or adjudicated extension is explicitly out-of-band and cannot
  enter deterministic accuracy.
- No provider calls or benchmark downloads occur during planning.

#### TASK-0026 — ARC exact-grid adapter and structured-output judge packet

Depends on: TASK-0025.

Implement canonical grid records, exact-grid scorer, structured-output parser,
failure taxonomy, and provider-neutral judge packet. Add mocked harness tests
and an optional Inspect AI adapter only if it passes the Eval Lab wrapper.

Acceptance criteria:

- Tests cover grid shape/value normalization, malformed outputs, exact match,
  source-family splits, fingerprints, timeouts, and abstentions.
- The scorer's gold provenance is benchmark answer key or deterministic exact
  match as declared, never a model judgment.
- The adapter preserves route/model metadata separately from answer labels and
  enforces the same no-OpenCode and Jev-only-OpenRouter policy.
- A new `EXP-021` manifest is required before final execution.

### Audited objective-subset tracks

#### TASK-0027 — LegalBench objective-subset audit and preregistration

Depends on: TASK-0026.

Audit LegalBench tasks and select only tasks with explicit, inspectable gold and
clear labels. Freeze the task-level inclusion/exclusion table, normalization,
source-family split, contamination notes, and `EXP-022` preregistration.

Acceptance criteria:

- Every selected task has a documented gold provenance, answer schema, source
  revision, license/access terms, and deterministic scoring rule.
- Open-ended explanations or judge-dependent criteria are excluded from the
  deterministic subset or placed in a separately labeled adjudication plan.
- The inclusion table, fingerprint method, calibration split, metrics, and
  stopping/exclusion rules are committed before execution.
- The task does not download or commit benchmark material during planning.

#### TASK-0028 — LegalBench adapter, gold audit, and report

Depends on: TASK-0027.

Implement the selected LegalBench canonical adapter, task-level scorer, gold
audit checks, typed packet, and report. Keep each task family separate in
analysis so a strong task does not mask a weak or ambiguous one.

Acceptance criteria:

- Tests cover every selected task schema, normalization, exact labels, missing
  or malformed outputs, split isolation, and provenance validation.
- Report includes per-task and aggregate metrics, with deterministic and any
  adjudicated results visibly separated.
- The runner records route failures independently and enforces the approved
  provider routing policy.
- All final artifacts use new `EXP-022` paths and checksums.

#### TASK-0029 — FinanceBench numeric/evidence subset audit and preregistration

Depends on: TASK-0028.

Select a numeric/evidence subset with explicit answer keys and reproducible
normalization. Freeze numeric tolerance, units, evidence/citation checks,
source revision, partitions, and `EXP-023`. Treat free-form explanations as a
separate adjudication track only if an adjudication protocol is approved.

Acceptance criteria:

- Numeric parsing, units, rounding, tolerance, missing evidence, and citation
  requirements are specified with known-value tests.
- The selected subset has task-level gold provenance and contamination notes.
- Deterministic numeric/evidence metrics cannot be mixed with free-form
  explanation outcomes.
- Preregistration is complete before any final labels or source execution.

#### TASK-0030 — FinanceBench adapter, evidence checker, and report

Depends on: TASK-0029.

Implement canonical numeric/evidence records, answer normalization, evidence
validation, typed packet, failure taxonomy, and separate report sections for
numeric correctness and evidence support.

Acceptance criteria:

- Tests cover tolerance boundaries, units, sign/scale errors, citations,
  malformed answers, abstention, and provider failures.
- Every result links to source record IDs and gold provenance without exposing
  private or hidden benchmark material.
- New `EXP-023` artifacts are checksumed and reproducible; prior experiments
  are untouched.

### Environment-heavy tracks

#### TASK-0031 — SWE-bench/DeepSWE feasibility, sandbox plan, and preregistration

Depends on: TASK-0030 and confirmed sandbox capacity.

Choose SWE-bench or DeepSWE only after evaluating repository snapshots, patch
application, test runtime, environment image, licensing, contamination risk,
and compute budget. Freeze the selected subset and `EXP-024` protocol.

Acceptance criteria:

- The task defines immutable repository/task revisions, patch boundary, test
  command, network/filesystem policy, timeout, resource limits, and failure
  categories.
- Gold is repository-test outcome, not a model or grader judgment.
- A bounded feasibility estimate exists without running the full benchmark.
- Final execution is blocked until the adapter, sandbox, and replay plan pass
  review; no prior experiment is reused as an output directory.

#### TASK-0032 — SWE-bench/DeepSWE patch verifier and execution adapter

Depends on: TASK-0031.

Implement isolated repository checkout, patch application, test execution,
canonical outcome records, typed repair packet, and audit report scaffolding.

Acceptance criteria:

- Fixture repositories test clean patch, rejected patch, partial test failure,
  timeout, environment failure, malformed patch, and abstention.
- Test logs are fingerprinted or summarized under the artifact policy, with
  secrets and unrelated repository data excluded.
- Route metadata and failures remain separate from repository-test labels.
- `EXP-024` cannot be marked complete without replayable environment and
  checksums.

#### TASK-0033 — OSWorld VM/state-verifier feasibility and preregistration

Depends on: TASK-0032 and availability of isolated VM infrastructure.

Freeze the OSWorld task subset, VM image/snapshot, GUI setup, state assertions,
replay policy, interaction timeout, task-specific assertions, and `EXP-025`.

Acceptance criteria:

- Each task has a deterministic or explicitly versioned state verifier and a
  resettable snapshot procedure.
- GUI/environment failures, model abstention, and assertion failures are
  distinct statuses.
- Credentials, personal data, host state, and hidden task material are kept
  out of committed artifacts.
- No execution proceeds without a reproducible VM image/snapshot reference and
  audit trail.

#### TASK-0034 — OSWorld runner, state assertions, and replay report

Depends on: TASK-0033.

Implement the isolated VM runner, action/observation packet, state assertions,
replay checks, and report. Use the same Eval Lab manifest, provenance,
calibration, and route metadata contract as the text tracks.

Acceptance criteria:

- Mock VM or fixture tests cover reset, action timeout, assertion pass/fail,
  environment failure, malformed action, and abstention.
- Replays are deterministic enough to audit, or nondeterminism is measured and
  reported rather than hidden.
- `EXP-025` artifacts are separate from all prior experiments and contain
  checksums/rebuild instructions.

### Expert and multimodal stress track

#### TASK-0035 — Humanity's Last Exam answer-key/adjudication policy

Depends on: TASK-0034.

Audit available answer keys and classify items into deterministic answer-key,
human-adjudicated, and unsupported categories. Freeze the eligible subset,
modality policy, answer normalization, adjudicator protocol, and `EXP-026`
preregistration only after the gold policy is explicit.

Acceptance criteria:

- No item is called objective without a declared answer-key or deterministic
  provenance; adjudicated items are visibly separate.
- Multimodal input handling, accessibility, model context limits, and
  contamination risks are documented.
- Adjudicator selection, blinding, disagreement handling, and stopping rules
  are preregistered for the non-deterministic track.
- The deterministic and adjudicated tracks have separate metrics and reports.

#### TASK-0036 — Humanity's Last Exam adapter, adjudication harness, and report

Depends on: TASK-0035.

Implement the eligible-item adapter, multimodal packet, answer-key scorer,
adjudication workflow, confidence/calibration handling, and limitations report.

Acceptance criteria:

- Tests cover modality/schema handling, answer normalization, answer-key
  scoring, adjudicator blinding and disagreement, malformed output, timeout,
  abstention, and provider failure.
- Model judgments are never silently promoted to gold.
- Deterministic and adjudicated outputs are published as distinct `EXP-026`
  artifacts with provenance and checksums.

## Shared definition of done for every implementation task

Before a task is accepted:

1. Its task file names the exact files it may modify and records status,
   completed work, commands, test results, decisions, unresolved questions,
   and next atomic action.
2. The task uses branch format `task/TASK-NNNN-short-name` and an isolated
   worktree created from the accepted parent checkpoint. Do not share an active
   worktree between tasks.
3. The feasibility/adapter/preregistration/execution/audit gates applicable to
   the track are complete in order.
4. Tests cover schema, provenance, split/fingerprint, scorer/verifier,
   malformed output, timeout, abstention, and provider-failure behavior as
   applicable.
5. Final execution, if authorized, writes only to the task's new experiment
   directory and preserves raw normalized predictions or a documented
   fingerprint of them.
6. Metrics include the applicable accuracy/balanced accuracy/macro F1, Brier,
   NLL, ECE, consistency, risk/coverage, latency, and cost fields; omitted
   fields are explained rather than silently absent.
7. The report states gold provenance, limitations, contamination risk,
   execution status, route/model metadata, and rebuild/checksum instructions.
8. Local contract checks and focused tests pass; no secrets, caches, private
   data, or unapproved benchmark material are committed.
9. The task is committed as one coherent checkpoint with a `TASK-NNNN:` commit
   message and reviewed before its dependent task starts.

## Explicit dependency graph

```text
TASK-0022 -> TASK-0023 -> TASK-0024 -> TASK-0025 -> TASK-0026
                                      -> TASK-0027 -> TASK-0028
                                                   -> TASK-0029 -> TASK-0030
                                                                -> TASK-0031
                                                                -> TASK-0032
                                                                             -> TASK-0033
                                                                             -> TASK-0034
                                                                                          -> TASK-0035
                                                                                          -> TASK-0036
```

The arrows indicate the recommended review order, not permission to execute
providers. Environment-heavy branches may be parallelized only after their
stated prerequisites and shared contract changes are accepted; they still
retain separate experiment IDs and output directories.

## Files changed by this planning task

- `tasks/TASK-0021-benchmark-roadmap-decomposition.md` (this file)

No other file is in scope for TASK-0021. Existing experiment directories,
manifests, reports, checkpoints, source code, and benchmark data remain
unchanged.

## Commands and test results

- Read only the required planning inputs: `PROJECT.md`,
  `checkpoints/CURRENT.md`, `docs/EXPERIMENT_PROTOCOL.md`,
  `docs/BENCHMARK_EXPANSION_ROADMAP.md`, and `AGENTS.md`.
- Inspected repository status before editing; the worktree was clean and on
  the provided detached checkpoint.
- No provider, benchmark, or experiment command was run.
- No test suite was run because this checkpoint changes planning documentation
  only.

## Decisions

- HumanEval is first because its executable verifier supplies the clearest
  end-to-end objective adapter pattern.
- ARC follows HumanEval because exact-grid scoring extends the contract to
  structured outputs without requiring a full interactive environment.
- LegalBench and FinanceBench are gated by task-level gold audits so their
  open-ended or ambiguous portions cannot contaminate deterministic results.
- SWE-bench/DeepSWE and OSWorld are deferred until sandbox, VM, replay, and
  runtime capacity are explicitly demonstrated.
- Humanity's Last Exam is last because its answer-key and adjudication status
  varies by item and modality.
- The proposed experiment IDs are `EXP-020` through `EXP-026`, one per roadmap
  track; they are planning identifiers only and do not create experiment
  artifacts in TASK-0021.

## Unresolved questions

- Which exact HumanEval, ARC-AGI, LegalBench, FinanceBench, SWE-bench/DeepSWE,
  OSWorld, and HLE revisions and subsets will pass their future feasibility
  audits?
- What sandbox and VM implementation is acceptable for code execution and
  GUI/state verification on the available host?
- Which optional Luna/Sol arms, if any, are scientifically necessary after the
  objective adapters are validated?
- What answer-key coverage and adjudicator budget are available for HLE?

## Next atomic action

Review and accept TASK-0021, then create TASK-0022 in its own
`task/TASK-0022-human-eval-feasibility` branch/worktree. TASK-0022 must freeze
the HumanEval source and executable-test policy before any adapter code,
provider smoke, benchmark retrieval, or final execution.
