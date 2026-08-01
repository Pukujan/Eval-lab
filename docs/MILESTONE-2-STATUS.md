# Milestone 2 status — Durable Evidence Evaluation Pipeline

Consolidated tracker. One document, updated as workstreams land. Frozen contracts
live in [`END-STATE-CONTRACT.md`](END-STATE-CONTRACT.md) and
[`MILESTONE-2-ACCEPTANCE.md`](MILESTONE-2-ACCEPTANCE.md); those are the default
authority for implementation decisions, not this file.

**Nothing is merged to the repository default branch. No live CKFF workflow has
been dispatched. No private verifier access has occurred.**

## Baseline

| | |
|---|---|
| Integration branch | `milestone-2/integration` |
| Merged CKFF connectivity base | `a4001ef48079ec8105b702f4750224ef4792d926` |
| Task 2B scaffold | `0588f48437fbe1723ed6189787dad404658de2ae` |
| Task 2A frozen baseline | `verification/task-2a-baseline.json` (unchanged) |
| Default branch | `claude/reliability-walking-skeleton-31b6a2` — **not** a merge target for this milestone |

## Frozen protocol versions

| Protocol | Version | Owner |
|---|---|---|
| `evidence-intake` | `1.0.0` | Eval-lab |
| `evallab-outcome` | `1.0.0` | Eval-lab |
| `verifier-envelope` | `1.0.0` | jointly frozen public boundary |
| `jobspec-reference` | `1.0.0` | Eval-lab (references Agent-workbench's JobSpec by digest) |

A protocol change requires a new version. An existing version is never silently
reinterpreted.

## Workstreams

| WS | Name | Branch | Owner | Current commit | Status |
|---|---|---|---|---|---|
| 1 | Contract and protocol | `milestone-2/ws1-contracts`, `milestone-2/ws1-adrs` | coordinator + agents | `2407056`, `0df41f8` — both merged | **complete: interfaces frozen** |
| 2 | Durable orchestration | `milestone-2/ws2-orchestration` | unassigned | — | not started |
| 3 | Evidence intake and isolation | `milestone-2/ws3-intake` | unassigned | — | not started |
| 4 | Public evaluator | `milestone-2/ws4-evaluator` | unassigned | — | not started |
| 5 | CKFF provider | `milestone-2/ws5-ckff-provider` | unassigned | — | not started |
| 6 | Verifier boundary | `milestone-2/ws6-verifier-boundary` | unassigned | — | not started |
| 7 | Integration | `milestone-2/ws7-integration` | coordinator | — | not started |

Workstream 1 freezes interfaces before parallel implementation begins. Workstreams
2–6 may then proceed in parallel. Workstream 7 is the sole owner of cross-cutting
files and is the only one that resolves conflicts.

## File ownership

**Two workstreams must never edit the same file.** Parallel agents work only
through isolated git branches and worktrees. A workstream that needs a change in
another's file requests it; it does not make it.

| Path | Owner |
|---|---|
| `contracts/schemas/**` | WS1 |
| `contracts/fixtures/**` | WS1 |
| `contracts/README.md` | WS1 |
| `docs/END-STATE-CONTRACT.md` | WS1 (coordinator) |
| `docs/MILESTONE-2-ACCEPTANCE.md` | WS1 (coordinator) |
| `docs/AGENT-WORKBENCH-HANDOFF.md` | WS1 (coordinator) |
| `docs/VERIFIER-BOUNDARY.md` | WS1 (coordinator) |
| `docs/architecture-decisions/ADR-0014..0020` | WS1 |
| `tests/unit/test_contract_fixtures.py` | WS1 |
| `app/workflows/evaluation_pipeline.py` | WS2 |
| `app/workflows/approval.py` | WS2 |
| `app/activities/evaluation/**` | WS2 |
| `tests/integration/test_pipeline_durability.py` | WS2 |
| `app/intake/**` | WS3 |
| `tests/unit/test_evidence_intake.py` | WS3 |
| `tests/unit/test_intake_containment.py` | WS3 |
| `app/evaluator/**` | WS4 |
| `tests/unit/test_public_checks.py` | WS4 |
| `tests/unit/test_rubric_boundary.py` | WS4 |
| `app/models/ckff_client.py` | WS5 |
| `app/models/alias_snapshot.py` | WS5 |
| `app/models/sequential_plan.py` | WS5 |
| `.github/actions/ckff-smoke/**` | WS5 |
| `.github/workflows/ckff-connectivity.yml` | WS5 |
| `.github/workflows/task-2b-sequential-evaluation.yml` | WS5 |
| `scripts/prepare_task_2b_run.py` | WS5 |
| `tests/unit/test_task_2b_scaffold.py` | WS5 |
| `tests/unit/test_ckff_smoke_redirects.py` | WS5 |
| `app/verifier/**` | WS6 |
| `tests/unit/test_verifier_boundary.py` | WS6 |
| `app/domain/schemas.py` | **WS7 only** |
| `app/reliability/gates.py` | **WS7 only** |
| `app/evidence/**` | **WS7 only** |
| `app/runner.py` | **WS7 only** |
| `pyproject.toml`, `Makefile`, `docker-compose.yml` | **WS7 only** |
| `.github/workflows/ci.yml`, `durable-stack-verification.yml` | **WS7 only** |
| `scripts/build_completion_manifest.py`, `export_evidence_bundle.py` | **WS7 only** |
| `docs/MILESTONE-2-STATUS.md` | **WS7 only** |

Everything not listed defaults to WS7.

## Reuse, not rewrite

Reused as-is: Temporal infrastructure and the Compose stack; the evidence exporter
and completion manifest; redaction utilities; traceability components; pytest
infrastructure; Promptfoo and Inspect AI integrations; Phoenix tracing; the CKFF
connectivity action; the Task 2B frozen-snapshot implementation; existing domain
objects where compatible.

Working Phase 1 and Task 2A components are **not** rewritten to fit another
framework. Durability and orchestration stay with Temporal — no custom scheduler,
queue, retry framework or state machine.

## Acceptance progress

Inventory and identifiers are in
[`MILESTONE-2-ACCEPTANCE.md`](MILESTONE-2-ACCEPTANCE.md). Nothing is claimed
complete here until it is demonstrated by a passing automated test.

| Group | Items | Complete | Blocked |
|---|---|---|---|
| A — evidence intake | A1–A10 | 0 | 0 |
| B — containment | B1–B8 | 0 | 0 |
| C — public evaluation | C1–C4 | 0 | 0 |
| D — durability | D1–D8 | 0 | 0 |
| E — verifier boundary | E1–E5 | 0 | 0 |
| F — outcome discipline | F1–F5 | 0 | 0 |
| G — regression | G1–G4 | 4 (currently green at baseline) | 0 |

## Contract changes

None. The contract was frozen at version 1.0.0 on 2026-08-01 and has not moved.

Any change requires a written ADR, impact analysis across Agent-workbench /
Eval-lab / verifier boundary / fixtures / existing evidence, changed acceptance
tests, protocol-version analysis, and explicit coordinator approval. Reinterpreting
an existing schema version to avoid creating a new one is not permitted.

## Unresolved security and ownership decisions

| # | Decision | Owner | Notes |
|---|---|---|---|
| S1 | `CKFF_API_KEY` classification | human | Whether the stored secret is the restricted evaluation key rather than a production master/admin credential. Not determinable from this repository, and never established by inspecting a value. |
| S2 | `CKFF_BASE_URL` value | human | Must read exactly `https://litellm-eval-production.up.railway.app`. Public configuration, safe to read in repository settings. |
| S3 | Sanitized validator artifact | infrastructure session | Required before any live request. Must show `__canary_invalid` failing fast. |
| S4 | `private-study-log` App scope | human | Attached to a session earlier; the standing instruction is that the App stays restricted to `Pukujan/Eval-lab`. Detaching is a GitHub settings change. |
| S5 | Frontier classification | human | Ambiguous aliases in the eventual frozen snapshot are escalated, not decided by a workstream. |

## External dependencies

| Dependency | Needed for | Status |
|---|---|---|
| Sanitized CKFF validator artifact | live gate | not supplied |
| Evaluation-service deployment/config identifier | frozen snapshot | not supplied |
| Ordered evaluation-service alias inventory | frozen snapshot | not supplied |
| Agent-workbench real evidence bundle | end-to-end with real data | not required for CI (fixtures stand in) |
| Eval-lab-verifier availability | live verifier path | not required for CI (mock stands in) |

## Integration status

Workstream 1 is complete and merged into `milestone-2/integration`: four frozen
contract documents, seven ADRs (0014–0020), four JSON Schemas at version `1.0.0`,
and sixteen fixtures (3 valid, 13 hostile) with a manifest naming the exact
expected rejection reason for each hostile case. Suite green at 739 passed,
3 skipped, with lint, format, types and security clean.

Interfaces are frozen, so workstreams 2–6 may now start in parallel.

Nothing merged to the default branch; no live workflow dispatched; no private
verifier access; `agent3/task-2b-scaffold` remains blocked until its live
preconditions are evidenced.

### Known gaps recorded rather than papered over

Three ADR requirements are deliberately written as requirements, not as
descriptions of working code, because the code does not exist yet. Each maps to an
open acceptance item:

| Gap | ADR | Acceptance item |
|---|---|---|
| Archive extraction ceilings (size, member count, expansion ratio) | 0018 | B4 |
| Run-scoped verifier query budget — policy, not yet enforcement | 0016 | E3 |
| Durable approval wait — mechanism chosen, no run has exercised it | 0017 | D7 |

Six properties cannot be expressed in JSON Schema at all and are owned by the
intake and evaluator workstreams instead, listed in `contracts/README.md`: the
manifest digest binding the document; declared digests matching real bytes;
"nothing undeclared and no symlink" in a materialised bundle (a filesystem
property); attempt-index ordering and retry-budget arithmetic; test-count
reconciliation; and gate ordering plus attestation digest binding.

One honest limit on the outcome schema: `rationale` and `caveats` are free prose,
so no schema can stop someone *writing* a correctness claim. What it does
guarantee is that no *field* can express one — the enum has four values and
`additionalProperties: false` blocks smuggling. Prose discipline stays with
`tests/unit/test_outcome_vocabulary.py`.
