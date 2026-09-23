# TASK-0021 — Benchmark roadmap decomposition

- Status: complete (planning checkpoint)
- Branch: `task/TASK-0021-benchmark-roadmap-decomposition`
- Worktree: `D:\claude\eval-lab\.worktrees\TASK-0021-benchmark-roadmap-decomposition`
- Scope: planning only; no provider calls, benchmark downloads, hidden-test access, or experiment execution
- Depends on: TASK-0019 / EXP-019 and TASK-0020

## Goal

Turn `docs/BENCHMARK_EXPANSION_ROADMAP.md` into an executable sequence of
dependency-ordered tasks. Every implementation task below has its own task
file, branch, worktree, experiment identity, acceptance gate, and handoff.
This file is the decomposition only; it does not authorize execution.

## Non-negotiable invariants

- EXP-014 through EXP-019 are immutable. No task may edit, overwrite, merge
  into, or reuse their result directories as a destination for new output.
- No OpenCode route is authorized.
- Grok may run only through the direct authenticated xAI `grok` Build CLI.
- OpenRouter is allowed only for the Jev arm when Jev is explicitly included;
  it is not a route for Grok, Luna, Sol, Qwen, or any substitute arm.
- A provider failure, timeout, malformed response, rate limit, or execution
  failure is execution metadata, not a benchmark answer.
- Each changed dataset, revision, prompt, rubric, model arm, seed, calibration
  method, or evaluation protocol receives a new experiment ID. Completed
  experiments are never revised in place.
- Eval Lab remains canonical for manifests, canonical records, source-family
  splits, gold provenance, typed judge packets, calibration, metrics, reports,
  checksums, and rebuild instructions. Inspect AI is optional harness
  infrastructure only; its default model grader is never objective gold.
- Benchmark families remain separate reports and experiments. No blended
  leaderboard score may be produced across these tracks.
- Objective gold must identify its provenance: deterministic verifier,
  benchmark answer key, human adjudication, or explicitly marked weak/model
  supervision. A model judgment is never silently promoted to objective gold.
- Every execution task must preserve separate calibration/development/final
  partitions, source-family isolation, malformed-output handling, abstention
  policy, timeout policy, execution-failure policy, surfaced model IDs, route
  metadata, and raw normalized predictions or a verifiable fingerprint.

## Common task, branch, and worktree contract

For every task below, create exactly one task record and one isolated worktree.
Use the corresponding branch and worktree names; do not combine two rows in one
branch or worktree.

```text
branch:  task/TASK-00NN-short-name
worktree: D:\claude\eval-lab\.worktrees\TASK-00NN-short-name
```

Each task file must declare status, dependencies, exact files in scope,
completed work, commands run, test results, decisions, unresolved questions,
next atomic action, and handoff evidence. A dependent task starts only after
its predecessor is accepted and merged (or explicitly recorded as a blocked
planning checkpoint). The task owner commits one coherent checkpoint using
`TASK-00NN: concise checkpoint description` and hands off the commit, task log,
experiment ID/manifest, checksums, and validation results.

No future task may begin final benchmark labels until its adapter gate and
preregistration gate are accepted. Feasibility tasks may inspect public
documentation and local capabilities, but they must not download benchmark
records or run providers unless their own task explicitly reaches an execution
gate after preregistration.

## Dependency-ordered implementation tasks

### Phase 1 — HumanEval: first end-to-end executable-verifier track

#### TASK-0022 — HumanEval feasibility, source freeze, and adapter preregistration

- Branch/worktree: `task/TASK-0022-humaneval-preregistration` /
  `D:\claude\eval-lab\.worktrees\TASK-0022-humaneval-preregistration`
- Depends on: TASK-0020 and TASK-0019
- Scope: identify the permitted HumanEval source revision, license/access terms,
  executable-test policy, sandbox limits, record sample, family split, typed
  judge packet, calibration split, metrics, exclusion rules, and stopping rule.
  Create the new experiment plan/manifest skeleton without provider labels or
  benchmark downloads.
- Acceptance criteria:
  1. The source URL, revision/commit, license/access terms, source-problem-ID
     policy, canonical record schema, and planned dataset fingerprint method are
     explicit.
  2. The executable verifier policy specifies allowed imports, resource/time
     limits, isolation, stdout/stderr handling, test discovery, timeout and
     crash outcomes, and how verifier failures differ from incorrect answers.
  3. The plan freezes calibration/development/final partitions, source-family
     isolation, typed output labels, confidence semantics, metrics, and
     objective-gold provenance before any final run.
  4. The plan lists model arms and route policy without adding an unauthorized
     provider or treating a judge as gold.
  5. Contract checks and plan/schema tests pass; no provider call, benchmark
     download, or EXP-014–019 modification occurs.
- Handoff: TASK-0023 receives the accepted source/policy decision and frozen
  plan commit. If source access, licensing, or sandbox policy is unresolved,
  record the blocker and do not create a final-label task.

#### TASK-0023 — HumanEval canonical adapter and sandboxed verifier

- Branch/worktree: `task/TASK-0023-humaneval-adapter` /
  `D:\claude\eval-lab\.worktrees\TASK-0023-humaneval-adapter`
- Depends on: accepted TASK-0022
- Scope: implement the canonical JSONL adapter, typed code-generation/judge
  packet, deterministic executable scorer, normalized status schema, split and
  fingerprint checks, and mocked/offline runner tests.
- Acceptance criteria:
  1. Every canonical record retains its source problem ID, task type, prompt,
     reference/test metadata, gold provenance, and split assignment.
  2. The verifier runs under the declared isolation/resource policy and returns
     deterministic pass/fail plus explicit timeout, crash, malformed-output,
     and verifier-error statuses.
  3. Unit tests cover correct, incorrect, malformed, timeout, crash, import,
     nondeterminism, and verifier-failure cases without using a provider.
  4. The adapter emits stable fingerprints, checks source-family isolation, and
     rejects schema drift or split leakage.
  5. Optional Inspect AI integration, if used, is an adapter around the Eval Lab
     record/verifier contract and is covered by parity tests; Inspect logs do
     not replace canonical artifacts.
- Handoff: TASK-0024 receives the adapter API, scorer test evidence, exact file
  list, and a mocked end-to-end packet. No live labels are included.

#### TASK-0024 — HumanEval judge packet, execution, and audit report

- Branch/worktree: `task/TASK-0024-humaneval-execution` /
  `D:\claude\eval-lab\.worktrees\TASK-0024-humaneval-execution`
- Depends on: accepted TASK-0023
- Scope: freeze the complete experiment manifest, run only the authorized
  smoke and frozen partitions, retain route/model/status metadata, then produce
  the HumanEval report and checksums as a new experiment.
- Acceptance criteria:
  1. The pre-registration commit precedes final-partition execution and records
     hypothesis, primary comparison, prompt/rubric, model arms, seed, split,
     calibration method, metrics, exclusions, and stopping rule.
  2. Smoke results are separate from final results; the final output contains
     normalized predictions, verifier outcomes, provider statuses, surfaced
     model IDs, latency/cost metadata where available, and checksums.
  3. Calibration fits only on the declared calibration/development data; final
     labels are not used for fitting or selection.
  4. The report separates correctness, calibration, consistency, risk/coverage,
     and execution failures, and states sandbox, contamination, and coverage
     limitations.
  5. The experiment manifest, `results.json`, `report.md`, artifacts, and local
     contract/test/checksum gates pass without changing EXP-014–019.
- Handoff: mark the HumanEval experiment complete only after all completion
  fields in `docs/EXPERIMENT_PROTOCOL.md` are satisfied. TASK-0025 may start
  only from the accepted HumanEval commit and report.

### Phase 2 — ARC-AGI: exact structured-grid verification

#### TASK-0025 — ARC-AGI feasibility, exact-grid adapter, and preregistration

- Branch/worktree: `task/TASK-0025-arc-adapter` /
  `D:\claude\eval-lab\.worktrees\TASK-0025-arc-adapter`
- Depends on: accepted TASK-0024
- Scope: select the ARC-AGI-1/2 revision and permitted subset, freeze grid
  representation and exact-match scorer, define task-family splits, typed
  structured-output packet, calibration partitions, contamination notes, and
  optional harness boundary.
- Acceptance criteria:
  1. Source revision, license/access terms, source task ID, grid encoding,
     answer representation, and fingerprint procedure are frozen.
  2. Exact-grid matching has tests for dimensions, values, empty grids,
     malformed structures, and normalization; no approximate score is used as
     objective correctness.
  3. The plan distinguishes answer-key provenance from deterministic exact-grid
     verification and records any task-level exclusions.
  4. Split/family isolation, typed packet, calibration method, failure handling,
     metrics, and report schema are committed before final execution.
  5. No ARC records, hidden material, provider calls, or prior experiment files
     are modified during this planning/adapter task.
- Handoff: provide TASK-0026 the accepted adapter contract, tests, frozen
  preregistration, and a new experiment ID; do not pool ARC with HumanEval.

#### TASK-0026 — ARC-AGI execution and structured-output audit

- Branch/worktree: `task/TASK-0026-arc-execution` /
  `D:\claude\eval-lab\.worktrees\TASK-0026-arc-execution`
- Depends on: accepted TASK-0025
- Scope: execute the frozen ARC study, compute exact-grid and calibration
  results, audit structured-output failures, and publish the separate report.
- Acceptance criteria:
  1. Execution uses only the frozen revision, packet, partitions, models, and
     routes; any change creates a new experiment ID.
  2. Exact-match outcomes, malformed outputs, timeouts, provider failures, and
     route metadata are separately retained and reported.
  3. Calibration and consistency analyses are split-safe and reproducible.
  4. The complete manifest, normalized predictions, results, report, checksums,
     and rebuild instructions pass local validation.
- Handoff: hand off the immutable ARC report and checksum set to TASK-0027;
  future LegalBench work may cite it but may not merge its scores with it.

### Phase 3 — LegalBench: objective rule-application subset

#### TASK-0027 — LegalBench objective-subset adapter and gold audit

- Branch/worktree: `task/TASK-0027-legalbench-adapter` /
  `D:\claude\eval-lab\.worktrees\TASK-0027-legalbench-adapter`
- Depends on: accepted TASK-0026
- Scope: select only LegalBench tasks with explicit answer keys or deterministic
  normalized labels; audit task-level gold provenance, label semantics, source
  families, contamination risk, and typed packet before preregistration.
- Acceptance criteria:
  1. Each included task has a documented objective-strength tier, answer-key
     source/revision, label map, normalization rule, and exclusion rationale.
  2. Open-ended explanations and judge-dependent items are excluded or placed
     in a separately marked adjudication plan; they cannot enter objective
     accuracy.
  3. The adapter tests exact/normalized matching, missing labels, malformed
     outputs, and source-family split isolation.
  4. The preregistration freezes the sample, splits, packet, calibration,
     models/routes, metrics, and report schema before final labels.
- Handoff: TASK-0028 receives the accepted task inventory, provenance audit,
  adapter tests, and new experiment ID. Unresolved gold ambiguity blocks
  execution rather than being resolved by a model vote.

#### TASK-0028 — LegalBench execution and objective-subset report

- Branch/worktree: `task/TASK-0028-legalbench-execution` /
  `D:\claude\eval-lab\.worktrees\TASK-0028-legalbench-execution`
- Depends on: accepted TASK-0027
- Scope: execute and audit only the frozen objective subset; keep any
  adjudicated/explanatory study separate or unexecuted.
- Acceptance criteria:
  1. The report is per task/family and identifies answer-key provenance,
     normalized-match behavior, unresolved statuses, calibration, and
     contamination limitations.
  2. No free-form legal explanation is scored as objective correctness without
     the separately approved adjudication protocol.
  3. Experiment artifacts, checksums, rebuild instructions, and local gates
     pass; no earlier experiment is altered.
- Handoff: hand off the immutable objective-subset report to TASK-0029 and
  explicitly list any adjudication work that remains out of scope.

### Phase 4 — FinanceBench: numeric/evidence objective subset

#### TASK-0029 — FinanceBench numeric/evidence adapter and preregistration

- Branch/worktree: `task/TASK-0029-financebench-adapter` /
  `D:\claude\eval-lab\.worktrees\TASK-0029-financebench-adapter`
- Depends on: accepted TASK-0028
- Scope: select numeric and evidence-grounded items with auditable sources;
  freeze numeric tolerance, normalized answer format, citation/evidence checks,
  document versions, source IDs, split policy, and a separate plan for free-form
  explanations if adjudication is available.
- Acceptance criteria:
  1. Every item declares answer-key/source provenance, numeric units, tolerance,
     rounding policy, normalization, and evidence/citation requirements.
  2. Numeric correctness and evidence correctness are distinct fields; neither
     is silently inferred from a judge's explanation.
  3. Tests cover numeric edge cases, units, missing evidence, invalid citations,
     malformed output, and source-family leakage.
  4. The preregistration freezes revision, sample, splits, packet, calibration,
     models/routes, metrics, exclusions, and report schema.
- Handoff: TASK-0030 receives the accepted finance adapter and an explicit
  decision on whether the free-form track is deferred. No financial provider
  execution occurs before this handoff is accepted.

#### TASK-0030 — FinanceBench execution and separate numeric/evidence report

- Branch/worktree: `task/TASK-0030-financebench-execution` /
  `D:\claude\eval-lab\.worktrees\TASK-0030-financebench-execution`
- Depends on: accepted TASK-0029
- Scope: run the frozen objective subset and report numeric, evidence, and
  execution outcomes separately; do not merge an adjudicated explanation score.
- Acceptance criteria:
  1. The report includes tolerance-aware numeric metrics, evidence/citation
     metrics, calibration, consistency, unresolved statuses, and limitations.
  2. Free-form explanations are either absent or clearly marked as a separate
     adjudication track with non-objective provenance.
  3. The experiment bundle is complete, checksummed, reproducible, and isolated
     from EXP-014–019 and all other benchmark experiments.
- Handoff: hand off the accepted report to TASK-0031; any source/licensing or
  evidence-verification gap is recorded as a blocker, not papered over.

### Phase 5 — SWE-bench/DeepSWE: repository repair after sandbox capacity review

#### TASK-0031 — SWE-bench/DeepSWE sandbox feasibility and adapter design

- Branch/worktree: `task/TASK-0031-swe-sandbox-feasibility` /
  `D:\claude\eval-lab\.worktrees\TASK-0031-swe-sandbox-feasibility`
- Depends on: accepted TASK-0030
- Scope: choose SWE-bench or DeepSWE only after confirming isolated repository
  execution, patch application, test runtime, resource budget, network policy,
  dataset access, contamination controls, and reproducible environment/image.
- Acceptance criteria:
  1. The selected source revision, task IDs, repository snapshots, license and
     access terms, environment image/setup, and resource limits are documented.
  2. Patch application, repository-test pass/fail, timeout, build failure,
     environment failure, and malformed patch are distinct statuses.
  3. The adapter design preserves task IDs, repository provenance, split/family
     isolation, and deterministic test invocation; no model grader is gold.
  4. A bounded mocked/local verifier test passes without provider labels and
     does not require downloading benchmark data in this planning checkpoint.
- Handoff: TASK-0032 receives the capacity decision and accepted sandbox/API
  design. If capacity or isolation is insufficient, mark this track blocked and
  do not authorize execution or substitute a different benchmark silently.

#### TASK-0032 — SWE-bench/DeepSWE preregistration, execution, and audit

- Branch/worktree: `task/TASK-0032-swe-execution` /
  `D:\claude\eval-lab\.worktrees\TASK-0032-swe-execution`
- Depends on: accepted TASK-0031
- Scope: freeze the repair benchmark experiment, execute within the approved
  sandbox, and publish patch/test evidence with environment metadata.
- Acceptance criteria:
  1. The pre-registration freezes source revision, repository snapshot policy,
     task sample, model arms/routes, prompt, seed, calibration split, metrics,
     timeout/stopping rules, and contamination exclusions.
  2. Each result preserves the generated patch or fingerprint, patch status,
     test command/version, test outcome, environment identity, and failure
     classification.
  3. No repository test failure is converted into a provider error or ordinary
     wrong answer; sandbox/environment failures remain separately auditable.
  4. The final experiment report, checksums, and rebuild instructions pass
     validation and remain separate from all text-only benchmark scores.
- Handoff: hand off the immutable SWE report to TASK-0033. Any environment
  drift requires a new experiment ID rather than an in-place rerun.

### Phase 6 — OSWorld: VM snapshot and state-verifier infrastructure

#### TASK-0033 — OSWorld VM/state-verifier feasibility and preregistration

- Branch/worktree: `task/TASK-0033-osworld-infrastructure` /
  `D:\claude\eval-lab\.worktrees\TASK-0033-osworld-infrastructure`
- Depends on: accepted TASK-0032
- Scope: establish isolated VM snapshots, reset/replay procedure, GUI state
  assertions, task-specific verifier contract, artifact capture, and resource
  policy before any computer-use benchmark run.
- Acceptance criteria:
  1. VM image/version, snapshot identity, reset behavior, network policy,
     secrets policy, screen/input capture, and resource/time limits are frozen.
  2. State assertions are deterministic and tested for success, partial state,
     wrong state, timeout, crash, and verifier/environment failure.
  3. The adapter preserves task IDs, initial/final state evidence, provenance,
     split isolation, typed action/output semantics, and checksums.
  4. The preregistration freezes sample, partitions, packet, model/routes,
     calibration, metrics, exclusions, and stopping rules before execution.
- Handoff: TASK-0034 receives a runnable, isolated verifier harness and frozen
  experiment plan. If snapshot replay or assertion determinism fails, block the
  track rather than report GUI success from manual inspection.

#### TASK-0034 — OSWorld execution and grounded-interaction audit

- Branch/worktree: `task/TASK-0034-osworld-execution` /
  `D:\claude\eval-lab\.worktrees\TASK-0034-osworld-execution`
- Depends on: accepted TASK-0033
- Scope: execute the frozen OSWorld partitions and publish task/state evidence,
  interaction reliability, calibration, and environment-failure analysis.
- Acceptance criteria:
  1. Each task starts from the declared snapshot and records reset, action,
     timeout, final-state assertion, and environment status metadata.
  2. VM failures, GUI/tool failures, provider failures, and incorrect final
     states are separate outcomes.
  3. The experiment bundle contains replay/setup instructions, state evidence or
     fingerprints, normalized predictions/actions, metrics, report, and checksums.
  4. No score is blended with SWE, ARC, or other tracks; limitations cover VM
     nondeterminism, task coverage, and contamination.
- Handoff: hand off the accepted OSWorld report to TASK-0035; preserve every
  failed or unreplayable task as audit metadata.

### Phase 7 — Humanity's Last Exam: answer-key/adjudication-controlled track

#### TASK-0035 — Humanity's Last Exam gold-policy audit and adapter

- Branch/worktree: `task/TASK-0035-hle-gold-policy` /
  `D:\claude\eval-lab\.worktrees\TASK-0035-hle-gold-policy`
- Depends on: accepted TASK-0034
- Scope: audit available answer keys, multimodal inputs, expert metadata,
  licensing/access, item ambiguity, adjudication requirements, and objective
  versus adjudicated subsets; implement only the canonical adapter and tests.
- Acceptance criteria:
  1. Every proposed item is classified as deterministic, answer-key based,
     human-adjudicated, or weak/model-supervised, with provenance and audit
     fields.
  2. Items without a defensible key are excluded from objective accuracy or
     assigned to an explicitly separate adjudication experiment.
  3. Multimodal input/output representation, asset fingerprints, normalization,
     missing-modality handling, and typed packet are tested and frozen.
  4. The preregistration freezes the subset, splits, rubric, adjudication
     protocol if applicable, calibration, metrics, exclusions, model/routes,
     and report schema before labels.
- Handoff: TASK-0036 receives the accepted provenance inventory and adapter.
  Ambiguous or unaudited items remain out of objective gold; no model consensus
  may promote them.

#### TASK-0036 — Humanity's Last Exam execution and separated report

- Branch/worktree: `task/TASK-0036-hle-execution` /
  `D:\claude\eval-lab\.worktrees\TASK-0036-hle-execution`
- Depends on: accepted TASK-0035
- Scope: execute only the frozen audited subset and, if separately authorized,
  the adjudication subset with its own provenance and report.
- Acceptance criteria:
  1. Objective answer-key results and adjudicated results are separate tables,
     metrics, artifacts, and claims.
  2. Multimodal assets, answer keys, adjudication decisions, model/route
     metadata, failures, calibration, and checksums are retained or fingerprinted.
  3. The report states coverage, ambiguity, expert agreement, contamination,
     multimodal limitations, and what cannot be called objective accuracy.
  4. The experiment is complete under the protocol and does not modify any
     prior experiment or create a blended benchmark score.
- Handoff: hand off the immutable HLE report to TASK-0037. If the answer-key or
  adjudication audit is incomplete, close only the adapter checkpoint and keep
  execution blocked.

### Phase 8 — paper and release integration

#### TASK-0037 — Benchmark-track release index and paper integration

- Branch/worktree: `task/TASK-0037-benchmark-paper-integration` /
  `D:\claude\eval-lab\.worktrees\TASK-0037-benchmark-paper-integration`
- Depends on: accepted reports from TASK-0024, TASK-0026, TASK-0028, TASK-0030,
  TASK-0032, TASK-0034, and TASK-0036; any blocked track is explicitly marked
  blocked rather than silently omitted.
- Scope: add track-level release/index references and manuscript sections only
  after each referenced experiment passes its audit gate.
- Acceptance criteria:
  1. Every table/figure traces to a single track's report, predictions/results,
     benchmark/source manifest, model/route metadata, and calibration artifact.
  2. Deterministic, answer-key, adjudicated, and weak/model-supervised results
     are visibly separated; no blended cross-track score is claimed.
  3. Release metadata contains versions, licenses/access terms, checksums,
     rebuild commands, limitations, and immutable experiment references.
  4. A failed or incomplete provider/environment run is represented as status
     metadata and unresolved coverage, never as a fabricated label or score.
  5. Paper/release validation passes and no experiment directory is rewritten.
- Handoff: provide the final release index, paper diff, validation output, and
  exact traceability map for review. Any later benchmark change starts a new
  task and experiment ID; it does not amend a completed track in place.

## Acceptance criteria

Before any task is marked complete, its owner must record:

- task status and exact branch/worktree;
- dependencies and accepted predecessor commit(s);
- exact files changed and confirmation that files outside scope were untouched;
- commands run and their results, including contract, tests, and `git diff --check`;
- experiment ID and manifest status, when an experiment exists;
- dataset revision/license/fingerprint and source-family split evidence;
- gold provenance and verifier/scorer behavior;
- provider/model/route metadata with failures separate from labels;
- calibration split and no-test-leakage evidence;
- checksums and rebuild instructions for completed experiments;
- decisions, unresolved questions/blockers, and one next atomic action.

## Checkpoint log

### 2026-09-21 — roadmap decomposition checkpoint

Status: complete.

Completed work: decomposed the roadmap into dependency-ordered HumanEval,
ARC-AGI, LegalBench, FinanceBench, SWE-bench/DeepSWE, OSWorld, Humanity's
Last Exam, and release-integration tasks. Added one-branch/one-worktree rules,
per-task acceptance criteria, handoff/blocker rules, and cross-task invariants.

Exact files changed: `tasks/TASK-0021-benchmark-roadmap-decomposition.md` only.

Commands run: read `AGENTS.md`, `PROJECT.md`, `checkpoints/CURRENT.md`,
`docs/EXPERIMENT_PROTOCOL.md`, `docs/BENCHMARK_EXPANSION_ROADMAP.md`, and
`tasks/TASK-0020-benchmark-expansion-plan.md`; checked that the target file was
absent before creation. No provider, benchmark, or experiment command was run.

Test results: planning-only document review; no provider execution, benchmark
download, or experiment test run was performed.

Decisions made: HumanEval is first; ARC follows its completed audit; LegalBench
and FinanceBench remain objective subsets; SWE/DeepSWE and OSWorld require
explicit environment gates; HLE requires an answer-key/adjudication audit; the
paper gate follows completed track reports. Existing experiments remain
immutable and routing policy is preserved.

Unresolved questions: exact source revisions, sample sizes, access terms,
hardware/environment budgets, final model arms, and execution dates remain for
the corresponding task's preregistration.

Next atomic action: create TASK-0022 in its own branch/worktree and freeze the
HumanEval source, executable-test policy, split/fingerprint, typed judge packet,
calibration split, and report schema before any final benchmark run.

## Handoff

The next agent must start with TASK-0022, not modify TASK-0020, not update
`checkpoints/CURRENT.md` as part of this task's scope, and not execute a
provider or download benchmark data while implementing this planning
checkpoint. Every later agent must use the task-specific worktree, update its
own task log at each meaningful stopping point, and stop with a written blocker
when a required dependency, verifier, license decision, sandbox, VM, or gold
provenance decision is not accepted.
