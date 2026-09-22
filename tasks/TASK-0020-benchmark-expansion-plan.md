# TASK-0020 — Benchmark expansion roadmap and Inspect AI boundary

- Status: complete (planning checkpoint)
- Branch: `task/TASK-0020-benchmark-expansion-plan`
- Scope: durable planning only; no provider calls and no benchmark execution
- Depends on: TASK-0019 / EXP-019 calibration study

## Goal

Record the next benchmark expansion as a durable, auditable roadmap. The roadmap
must explain where Inspect AI can help, which benchmark families are appropriate,
how objective gold and deterministic scoring will be preserved, and how each
future benchmark becomes a separate reproducible experiment.

## Completed work

- Wrote `docs/BENCHMARK_EXPANSION_ROADMAP.md`.
- Recorded an explicit Eval Lab/Inspect AI integration boundary.
- Ranked HumanEval, ARC-AGI, LegalBench, FinanceBench, SWE-bench/DeepSWE,
  OSWorld, and Humanity's Last Exam as separate future tracks.
- Defined the adapter contract, objective-gold rules, experiment gates, and
  proposed implementation order.
- Preserved the current provider policy: Grok only through the direct
  authenticated xAI `grok` CLI; Luna/Sol only through Codex routes when in
  scope; OpenCode is not used; OpenRouter is reserved for the Jev-only route.
- Updated `checkpoints/CURRENT.md` with the new durable next action.

## Invariants

- EXP-014 through EXP-019 remain immutable.
- No model judgment is promoted to objective gold solely because the model is
  large or strong.
- Benchmark families are not collapsed into one score; each has its own
  manifest, scorer/verifier, provenance, and report.
- Provider status is retained as execution metadata, not treated as a research
  outcome for benchmark quality.

## Acceptance criteria

- The benchmark expansion plan is present in a durable repository document.
- Inspect AI's role and limits are explicit.
- Candidate benchmark families have separate objective-strength and execution
  requirements.
- The adapter contract and experiment gates are stated.
- Current routing policy and immutable experiment boundaries are preserved.

## Checkpoint log

### 2026-09-21 — planning checkpoint

Status: complete.

Completed work: wrote the benchmark expansion roadmap, updated the authoritative
repository checkpoint, and recorded the next HumanEval adapter action.

Exact files changed: `docs/BENCHMARK_EXPANSION_ROADMAP.md`,
`tasks/TASK-0020-benchmark-expansion-plan.md`, and `checkpoints/CURRENT.md`.

Commands run: repository contract check, `git diff --check`, and the local test
suite. The first contract check identified missing required task headings; those
headings were added before the final validation.

Test results: final validation is recorded after the heading correction.

Decisions made: Inspect AI is optional infrastructure; Eval Lab remains the
canonical provenance, calibration, and reporting layer. HumanEval is the next
recommended adapter.

Unresolved questions: exact dataset revisions, sample sizes, access terms, and
final model arms belong to the next task's preregistration.

## Handoff

The next agent should create a new HumanEval adapter task rather than expanding
TASK-0020. It must read the repository contract and experiment protocol, freeze
the dataset revision and executable-test policy, and create a new experiment
directory before final benchmark labels are collected.

## Validation

- `git diff --check`
- `python scripts/check_repo_contract.py`
- `PYTHONPATH=src python -m pytest -q`

## Decisions and unresolved items

- Inspect AI is an optional execution/harness backend, not a replacement for the
  Eval Lab canonical schema, preregistration, calibration protocol, immutable
  artifacts, or provenance rules.
- HumanEval is the recommended first implementation track because executable
  tests provide a strong objective verifier and the adapter is comparatively
  contained.
- Exact dataset revisions, licenses/access terms, sample sizes, and final model
  arms remain to be frozen in the next task's preregistration.

## Next atomic action

Create a new task for a HumanEval adapter and preregistration. That task must
freeze the dataset revision, executable-test policy, split/fingerprint, typed
judge packet, calibration split, and report schema before final benchmark runs.
