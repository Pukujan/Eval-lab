# TASK-0022 — HumanEval adapter and preregistration

## Status and authority

**Status:** EXP-020 planning-policy checkpoint complete; executable
preregistration, adapter implementation, and final evaluation blocked/pending.

This file is the planning checkpoint for the next benchmark track in
`docs/BENCHMARK_EXPANSION_ROADMAP.md`. The present checkpoint authorizes no data
download, provider call, candidate execution, or final benchmark run. The future
implementer must commit a frozen experiment manifest before any final evaluation.
EXP-014 through EXP-019 remain immutable. Eval Lab owns canonical records,
provenance, splits, calibration, and reports; Inspect AI may be an optional
execution harness only if its outputs pass the same adapter contract.

## Goal

Build a reproducible HumanEval adapter that turns pinned Python problems and
candidate completions into canonical single-candidate judge records. Determine
correctness with the pinned executable tests inside an isolated sandbox. Freeze
the dataset, candidate pool, typed judge packet, splits, verifier, model routes,
calibration plan, and analysis before a final test run. Deliver adapter and
verifier tests, a small offline smoke, a committed preregistration, artifact
checksums, and rebuild instructions. Final provider labels and headline results
belong to a later execution checkpoint after the freeze.

## Source revision and access policy

- Source: [OpenAI HumanEval](https://github.com/openai/human-eval), including
  `data/HumanEval.jsonl.gz` and the upstream evaluator. Pin the repository to
  commit `6d43fb980f9fee3c892a914eda09951f772ad10d` (read-only
  `git ls-remote` resolution of `refs/heads/master` on 2026-09-21). Never use a
  floating `master` or an unrecorded package version in a frozen run.
- The upstream repository [states MIT terms](https://github.com/openai/human-eval/blob/6d43fb980f9fee3c892a914eda09951f772ad10d/LICENSE).
  Before retrieval, verify those terms cover the exact dataset file and record
  its source URL, revision, license text/digest, retrieval time, compressed
  SHA-256, decompressed canonical-row SHA-256, and row count. Fail closed on a
  changed license, missing file, duplicate `task_id`, or unexpected schema.
- Download only from the pinned official source when implementation begins.
  Keep the raw archive in a local ignored cache; do not commit benchmark rows,
  hidden/private material, generated code with sensitive content, or credentials.
  Commit only manifests, code, fixture data written for tests, and hashes unless
  a later explicit publication policy permits redistribution.
- Record contamination limits: HumanEval is public and may occur in model
  training data. Do not call the result an uncontaminated generalization test.

## Canonical record and candidate identity

Use the existing `SourceRecord`, `JudgeRecord`, `GoldLabel`, and
`JudgePrediction` types in `src/eval_lab/schema.py`; add an adapter-specific
strict metadata model only where necessary. One upstream row maps to one
`SourceRecord`:

| Field | Required value |
| --- | --- |
| `source_id`, `source_problem_id` | Stable `HumanEval/<n>` task ID, retained verbatim. |
| `domain`, `source_dataset`, `split` | `code`, `openai/human-eval`, deterministic assigned split. |
| `prompt` | Exact upstream function signature and docstring, with its SHA-256. |
| `reference_answer` | Structured local verifier reference: `entry_point`, test digest, and canonical-solution digest; do not place tests or the solution in judge packets. |
| `source_metadata` | Source commit, archive/row digests, adapter version, Python/runtime image digest, and source-family key. |

Each candidate completion maps to one `JudgeRecord` with `mode=single`,
`candidate_a` equal to the exact completion bytes decoded as UTF-8,
`candidate_b=null`, the problem prompt, a versioned binary-correctness rubric,
the parent `source_problem_id`, and the parent's split. `record_id` is a stable
hash of source revision, task ID, candidate-source manifest digest, candidate
index, completion digest, and adapter version. Keep candidate index and raw
completion digest in adapter metadata. Reject duplicate IDs and any candidate
whose parent problem is absent. Do not silently strip code fences, repair
imports, normalize whitespace, or append hidden solution text. Any declared
normalization becomes a new versioned arm.

`GoldLabel.label` is `PASS` or `FAIL` only after a valid verifier result;
`provenance=executable_test`, `verifier_id` identifies the frozen verifier and
runtime image, and `evidence` contains test-suite digest, completion digest,
exit category, duration, and sandbox status. A model judgment, reference
solution, or upstream sample score alone cannot create objective gold. Retain
verifier-indeterminate candidates separately; never serialize a guessed label.

## Executable verifier and sandbox gate

- Reproduce the upstream composition exactly: `prompt + completion + test +
  check(entry_point)` for the pinned row. Validate entry point and test fields
  before execution. Check source/test digests at load time. The upstream
  [execution code](https://github.com/openai/human-eval/blob/6d43fb980f9fee3c892a914eda09951f772ad10d/human_eval/execution.py)
  explicitly says its reliability guard is **not** a security sandbox.
- Do not execute untrusted completions in the host Python process or rely on
  the upstream guard for isolation. Use a disposable Linux container or VM per
  candidate, with pinned image digest and Python version, non-root user,
  read-only input mount, writable ephemeral scratch, no network, no host secret
  or workspace mounts, dropped capabilities, seccomp, process/file/output
  limits, and bounded CPU, memory, and wall time. Document exact limits and
  image build before freeze; a smoke must prove egress and host-file access are
  blocked. If this isolation is unavailable, stop before executing candidates.
- Capture structured outcomes: `passed`, `assertion_failed`, `syntax_error`,
  `runtime_error`, `candidate_timeout`, `sandbox_error`, and
  `verifier_internal_error`. A healthy sandbox's test failure or candidate
  timeout is `FAIL`; a sandbox crash, missing tests, image mismatch, or verifier
  error is indeterminate and excluded from correctness denominators. Preserve
  diagnostic counts without exposing unbounded stdout/stderr. Re-run only
  indeterminate infrastructure outcomes under a preregistered fixed retry
  rule; never tune timeouts after looking at final labels.
- Test the verifier with hand-written pass, assertion fail, syntax fail,
  infinite loop, filesystem/network attempt, and sandbox failure fixtures.
  Confirm the same candidate gets the same label and evidence digest on replay.

## Split and fingerprint policy

HumanEval supplies no train/dev/calibration/test partition for this study.
After retrieving and validating the pinned source, sort distinct task IDs by
`SHA-256("humaneval-v1|20260921|" + task_id)` with task ID as tie-breaker.
Assign the first 20% (floor) to development, the next 20% (floor) to
calibration, and the remainder to final test. With 164 source tasks this gives
32 dev, 32 calibration, and 100 test; assert the observed count at freeze and
record the actual counts. No source problem or derived candidate family may
cross splits. Development is for packet/rubric and adapter choices;
calibration is for fitting a prespecified calibrator/abstention threshold;
test is evaluation-only. No train split is needed unless a later task explicitly
adds model training under a new experiment ID.

Freeze and commit: ordered task-ID lists and their SHA-256 digests; source
archive, decompressed rows, candidate-pool, canonical-source JSONL,
judge-record JSONL, and packet-protocol digests; adapter, verifier, runtime,
rubric, and split-policy versions. Hash canonical UTF-8 JSON with sorted keys,
fixed separators, and LF records. A changed source row, candidate, split,
prompt, rubric, seed, verifier, runtime, or calibration method requires a new
experiment ID; never overwrite a completed experiment.

## Typed judge packet and prediction contract

The judge predicts whether one exact completion passes the frozen tests.
Freeze a versioned JSON packet with `task_type="python_function_correctness"`,
`language="python"`, `task_id`, `problem_prompt`, `candidate_completion`,
`rubric_version`, `allowed_labels=["PASS","FAIL"]`, and `protocol_version`.
The packet excludes tests, canonical solution, gold, verifier diagnostics,
split assignment, and any post-verification hint. A structured response must
contain one legal label and either a finite probability distribution over both
labels summing to one or an explicit `probability_unavailable` marker. Store
raw scores if supplied. Validate with `JudgePrediction`; preserve `judge_id`,
actual surfaced model ID, provider route, prompt/protocol version, latency,
token usage, and execution status as metadata. Report probability-bearing and
label-only arms separately for calibration metrics.

Provider policy is fixed: no OpenCode. OpenRouter is allowed only for an
explicit Jev arm; it is never a fallback for another provider. Grok runs only
through the direct authenticated xAI `grok` Build CLI. Local Qwen and other
arms need their own explicitly frozen direct route and model ID. No provider
is silently substituted after a failure. Freeze the exact included arms,
candidate-generation source and parameters, prompt text, model revisions,
seed(s), context cap, per-record cost/time budget, retry policy, and stopping
rule in the experiment manifest before provider execution.

## Malformed output and timeout policy

- Missing/empty/non-UTF-8 candidate payload, wrong task ID, duplicate
  candidate key, or malformed transport is `invalid_candidate` with no gold.
  Valid Python text that raises a syntax or runtime error is verifier `FAIL`.
- A malformed judge response is `parse_error`; provider timeout, rate limit,
  and provider error have separate execution statuses. They carry no ordinary
  wrong-answer label and remain in attempted-record and coverage counts.
  If the shared enum needs a distinct timeout state, extend it in the future
  implementation rather than disguising timeout as `FAIL`.
- Candidate execution timeout in a healthy pinned sandbox is verifier `FAIL`
  with an explicit timeout subcategory. Sandbox timeout/crash before a reliable
  candidate outcome is indeterminate. Report both counts separately.
- Predeclare exclusions and retry limits; preserve first-attempt status and
  any later attempt IDs. Never let a retry silently replace a frozen result.

## Preregistration and report schema

Create a fresh `experiments/EXP-YYYYMMDD-NNN-humaneval-.../` following
`docs/EXPERIMENT_PROTOCOL.md` when implementation starts. Before final test,
commit its manifest and plan with hypothesis, primary comparison, exact
source/candidate fingerprints, split membership, packet and verifier versions,
model routes, calibration method, metric definitions, exclusion/retry rules,
and stopping rule. The primary unit is a candidate decision; cluster
uncertainty intervals by source task so multiple completions do not masquerade
as independent problems. Predefine how many completions per task and which
candidate generator supplied them. Do not use final test labels for selection,
prompt design, temperature fitting, or threshold tuning.

Required `results.json`/report fields: source and candidate manifests,
dataset/runtime/verifier/packet hashes, arm route and surfaced model IDs,
per-split attempted/valid/invalid/indeterminate counts, verifier outcome
counts, provider status counts, raw predictions or their checksummed artifact
paths, and calibration artifact trained solely on calibration IDs. For each
arm, report accuracy, balanced accuracy, macro F1, Brier, NLL, ECE, selective
risk/coverage, coverage at a frozen error target, latency, and cost per 1,000
attempted decisions where inputs permit. Mark probability metrics unavailable
for label-only outputs. Report primary test estimates and clustered intervals,
dev/calibration diagnostics separately, class prevalence, and an explicit
public-benchmark contamination limitation. If code-generation pass@k is later
included, declare it as a separate generation metric with a valid sample
count and estimator; never call judge accuracy pass@k. Do not blend HumanEval
into a cross-domain leaderboard score.

## Implementation scope

TASK-0023 is authorized to modify exactly these paths for the offline
HumanEval adapter/verifier checkpoint:

- `src/eval_lab/datasets/humaneval.py`
- `src/eval_lab/datasets/__init__.py`
- `src/eval_lab/verifiers/humaneval.py`
- `src/eval_lab/verifiers/__init__.py`
- `tests/test_humaneval.py`
- `tasks/TASK-0022-humaneval-adapter-design.md`

No shared schema change, script, checkpoint, experiment artifact, benchmark
cache, provider output, result/report, or final-label artifact is in scope.
The implementation must use only hand-written fixtures and mock sandbox
responses. It must not retrieve HumanEval, execute candidate code, invoke a
provider, or claim a real sandbox proof. EXP-014 through EXP-019 are
immutable.

## Acceptance criteria

Acceptance requires:

1. Pinned source/license/access evidence and exact fingerprints; deterministic
   split map with source-family isolation and byte-stable canonical JSONL.
2. Strict source/judge/packet validation, no test or answer leakage to packet,
   explicit executable-test provenance, and stable record IDs.
3. A sandbox isolation demonstration plus offline verifier fixtures and tests
   for pass, fail, syntax error, timeout, invalid input, and infrastructure
   failure. No host execution of untrusted candidate code.
4. Mock provider contract and one-record local/offline smoke; normalized
   predictions preserve execution states and route metadata. A live provider
   smoke is allowed only after preregistration and route freeze, and is not
   required to establish the adapter contract.
5. A committed experiment preregistration before final test use; calibration
   fits calibration only, and tests reject split or test-label leakage.
6. A report validator enforcing the stated metric/status schema, checksum
   coverage, rebuild steps, and limitations. Run focused tests, repository
   contract checks, lint, and `git diff --check`; record exact outcomes here.

## Checkpoint log

### 2026-09-21 — TASK-0023 scope and blocker checkpoint

- **Status:** implementation not started; scope checkpoint committed on
  `task/TASK-0023-humaneval-adapter` in the dedicated worktree
  `D:/claude/eval-lab-TASK-0023`. No adapter or verifier code is being claimed
  complete.
- **Completed:** declared the exact TASK-0023 implementation file scope above;
  read the required repository/design and EXP-020 planning artifacts; created
  the isolated worktree. EXP-014 through EXP-019 remain untouched.
- **Exact files changed:** `tasks/TASK-0022-humaneval-adapter-design.md`
  only. The authorized but not-yet-created implementation paths are
  `src/eval_lab/datasets/humaneval.py`, `src/eval_lab/datasets/__init__.py`,
  `src/eval_lab/verifiers/humaneval.py`,
  `src/eval_lab/verifiers/__init__.py`, and `tests/test_humaneval.py`.
- **Commands run:** `git worktree add D:/claude/eval-lab-TASK-0023 -b
  task/TASK-0023-humaneval-adapter HEAD`; named document and EXP-020 reads;
  source/test inventory inspection; no provider, network retrieval,
  benchmark execution, candidate execution, or sandbox invocation.
- **Test results:** no implementation tests were run because no implementation
  exists at this checkpoint. `git diff --check` is the only validation for
  this task-log-only commit.
- **Decisions:** keep the checkpoint fixture-only and offline; do not modify
  shared schema, scripts, checkpoints, experiment artifacts, results, reports,
  or final labels. The adapter will use existing canonical schema types and a
  mock-only verifier boundary when implementation resumes.
- **Blocker:** Docker Desktop's Linux engine is unavailable, and WSL2 is not a
  demonstrated sandbox. The real sandbox proof remains unresolved; no
  untrusted candidate code may execute. This checkpoint therefore records
  scope/blocker state only and does not authorize a bypass.
- **Next atomic action:** implement the declared offline HumanEval adapter and
  verifier with hand-written fixtures/mocks, including canonical JSONL,
  stable IDs/fingerprints, split-family isolation, normalization, and explicit
  malformed/timeout/crash/import/verifier-error plus sandbox-unavailable
  statuses; then run focused tests and the repository merge gate.

### 2026-09-21 — EXP-020 source audit and policy skeleton

- **Status:** planning checkpoint complete in
  `D:/claude/eval-lab/.worktrees/TASK-0022-preregistration` on
  `task/TASK-0022-humaneval-preregistration` from `main` `2ee94f7`.
  EXP-020 is `planning_only_blocked`, not a completed experiment or final-test
  preregistration. TASK-0021 dependency is present at `7ea5bb6`.
- **Completed:** read-only official source/revision/license/access audit;
  executable-test, split, typed packet, gold, failure, sandbox, calibration,
  provider and reporting policies; machine-readable manifest and checksum/
  rebuild skeleton. No data retrieval, candidate execution, provider call or
  final label occurred. EXP-014–019 and `checkpoints/CURRENT.md` untouched.
- **Exact files changed:** this task file;
  `experiments/EXP-20260921-020-humaneval-preregistration/README.md`,
  `experiment.yaml`, `plan.md`, `checksums.sha256`, `rebuild.md`.
- **Commands run:** named contract/document reads; `git status`, `git log`,
  `git worktree list/add`, `git ls-remote` official repository; read-only
  GitHub pinned-tree API, pinned-license GET/hash and archive HEAD; `docker
  version`, `wsl --status`; `rg` on contract/tests; PowerShell `Get-FileHash`;
  Python YAML parse/assertions; `python scripts/check_repo_contract.py`;
  `python -m pytest -q tests/test_repo_contract.py
  tests/test_program_contract.py tests/test_schema.py` (first without, then
  with `PYTHONPATH=src`); `ruff check .`; `git diff --check`.
- **Test results:** repository contract OK; first focused test collection
  failed (`ModuleNotFoundError: eval_lab`) without `PYTHONPATH`; rerun with
  `PYTHONPATH=src` passed 20 tests in 1.04s. Ruff clean; YAML parsed with
  blocked/null gates asserted; four planning checksums matched; diff check
  clean (Git line-ending conversion warning only). No verifier or candidate
  smoke was run.
- **Decisions:** pin upstream commit
  `6d43fb980f9fee3c892a914eda09951f772ad10d`; root MIT license digest
  `bcba3de214851cce46ed5af42d6698044616eeace887c3231bc7a20474ab639e`;
  archive Git blob `998d25196e17af24daf9b6cb3a975fe752528e46`
  and HEAD 200/44,877 bytes are metadata, **not** an archive SHA-256 or row
  audit. No redistribution. Sandbox and exact tests are mandatory for gold;
  provider policy remains no OpenCode, OpenRouter Jev only, Grok direct xAI
  `grok` CLI only.
- **Blockers/unresolved:** Docker Desktop Linux engine unavailable (missing
  named pipe); WSL2 Ubuntu alone is not sandbox proof. Image digest, limits,
  isolation probes, archive/row fingerprints, actual split membership,
  candidate source/count, exact arms/models, calibration estimator, retry
  cap and primary comparison remain unset. Recheck pinned terms at retrieval.
  No final-label artifact or final test is permitted on this checkpoint.
- **Next atomic action:** in a separately accepted implementation checkpoint,
  prove isolated sandbox behavior with hand-written fixtures, then implement
  adapter/verifier tests and obtain authorized pinned-source fingerprints;
  fill and commit all remaining manifest gates before any provider/final run.

### 2026-09-21 — EXP-020 planning scope opened

- **Status:** active in `D:/claude/eval-lab/.worktrees/TASK-0022-preregistration`
  on `task/TASK-0022-humaneval-preregistration`, based on `main` `2ee94f7`.
- **Completed:** expanded the allowed-file list above before creating EXP-020.
- **Exact files changed so far:** this task file only.
- **Commands run:** read the named project/task/protocol/roadmap files;
  `git status`, `git log`, `git worktree list`, `git worktree add`, read-only
  official-source `git ls-remote`, GitHub tree metadata query, raw-license
  hash, archive HEAD request, `docker version`, and `wsl --status`.
- **Test results:** no benchmark, provider, or candidate tests run; source
  metadata and environment probes only. Repository checks remain pending.
- **Decisions:** EXP-020 is a planning-only skeleton; no final-label artifacts.
- **Unresolved:** Docker Linux engine is unavailable; sandbox proof and exact
  runtime image/limits remain an execution gate.
- **Next atomic action:** record the source audit and preregistration policy in
  the allowed EXP-020 skeleton, then run repository checks.

### 2026-09-21 — planning specification

- **Completed:** specified source pin/access gate, canonical records, sandbox
  verifier, split and fingerprints, typed packet, calibration discipline,
  failure semantics, reporting, smoke tests, and acceptance criteria.
- **Exact files changed:** `tasks/TASK-0022-humaneval-adapter-design.md` only.
- **Commands run:** read `AGENTS.md`, `PROJECT.md`, `checkpoints/CURRENT.md`,
  `docs/EXPERIMENT_PROTOCOL.md`, and `docs/BENCHMARK_EXPANSION_ROADMAP.md`;
  inspected `src/eval_lab/schema.py` and the ARC adapter for type alignment;
  checked worktree status; ran read-only `git ls-remote` for the upstream pin.
  No dataset retrieval, provider call, candidate execution, or experiment edit.
- **Test results:** initial repository contract check found four missing
  required task headings; headings were corrected. Final
  `python scripts/check_repo_contract.py` returned `Repository contract OK`;
  `git diff --cached --check` passed. Implementation tests were not run
  because no code was changed.
- **Decisions:** 20/20/60 problem-family split; binary `PASS`/`FAIL` objective
  gold from isolated executable tests; separate infrastructure and provider
  states; direct provider policy as stated above.
- **Unresolved questions:** exact container image digest and resource limits,
  candidate source/count, included judge arms, calibration estimator, and
  experiment ID must be chosen and frozen at implementation preregistration
  before final test. Source license applicability must be verified at retrieval.
- **Next atomic action:** open a dedicated implementation checkpoint, verify
  source access/licensing and sandbox availability, update this file with exact
  implementation paths and experiment ID, then build the offline adapter and
  tests before any provider or final benchmark run.

## Handoff

Begin with the next atomic action above. Read this task and the minimum design
documents named in `AGENTS.md`; preserve the pinned source and provider rules.
Record each implementation checkpoint, exact changed paths, commands, test
results, decisions, blockers, and next action in this file. Do not infer an
experiment result or permission to execute untrusted code from this plan.
