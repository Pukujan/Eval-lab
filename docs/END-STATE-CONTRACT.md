# End-state contract — FROZEN

**Contract version: 1.0.0. Frozen 2026-08-01.**

This document defines who owns what across three repositories and one human, and
which protocols they exchange. It is frozen: changing it requires a written ADR,
an impact analysis across Agent-workbench, Eval-lab, the verifier boundary, the
fixtures and existing recorded evidence, changed acceptance tests, a
protocol-version analysis, and explicit coordinator approval. A subagent may not
change it silently.

Nothing in this contract claims Eval-lab proves correctness or production safety.
It cannot, and every mechanism below is shaped by that.

## Why the split exists

A system that can read its own hidden tests is measuring itself. That is not a
hypothetical concern here: Task 2A's own security review found that the party
producing the evidence was also the party grading it, which is why the evidence
exporter refuses to write `verified: true` in anything it authors and why the
verifier lives in a repository nobody on the implementation side can read.

The split is therefore not an organisational convenience. It is the only thing
making any of the resulting numbers worth reading.

## Ownership

### Agent-workbench

Owns the production of work.

| Owns | Detail |
|---|---|
| JobSpec | Receives the real JobSpec. **Agent-workbench owns its format.** |
| Execution | Runs the coding agent in an isolated environment |
| Lifecycle | Worktree, container and session lifecycle for producing work |
| Visible tests | Runs them; records **initial and final** visible-test results |
| Artifacts | Produces candidate artifacts |
| Evidence | Produces the versioned evidence bundle |
| Record-keeping | Attempt lineage, retries, redaction, provenance, operational failures |

**Never receives:** private verifier tests, private oracle information, holdouts,
mutation suites, thresholds, or private verifier reports.

**Agent-workbench reviewer output is untrusted evidence only.** It is a
measurement to be validated, never an acceptance decision. Eval-lab treats a
reviewer's "this looks correct" exactly as it treats a model's completion: text
that has no authority over control flow.

### Eval-lab

Owns the evaluation.

| Owns | Detail |
|---|---|
| Intake schema | The public evidence-intake schema |
| Validation | Schema version, required fields, hashes, provenance, JobSpec correspondence, artifact completeness |
| Rejection | Incomplete, inconsistent, malformed or tampered evidence |
| Public checks | Deterministic checks, run in isolation |
| Scoring | Versioned calibrated rubric scorers |
| Provider boundary | Model comparisons through one controlled adapter |
| Verifier boundary | Invokes the sealed verifier through a narrow protocol |
| Decision | The deterministic evaluation decision policy |
| Outcome | Emits only supported Eval-lab outcomes |

**Never claims** to have proved full correctness or production safety.

Supported outcomes are exactly these four, and no others:

| Outcome | Means |
|---|---|
| `accepted_for_review` | Every deterministic gate passed. **A human should look.** Not `approved`, not `correct`, not `safe`, not `production_ready`. |
| `rejected` | At least one deterministic gate failed |
| `abstained` | Eval-lab declined to judge. This is **not** a claim the work is wrong |
| `infrastructure_failure` | The harness failed. This says **nothing** about the work |

The words `approved`, `correct`, `safe` and `production_ready` are forbidden as
outcomes, and the outcome schema rejects them.

### Eval-lab-verifier

Owns the ground truth, exclusively:

hidden tests · hard-gold references · protected holdouts · private mutations ·
evaluator mutation suites · private oracle logic · private threshold material ·
detailed private reports.

It returns **only a minimal versioned result or attestation**. Eval-lab and
Agent-workbench must not access its repository or internals, and must not attempt
to infer hidden-test detail from its responses. See
[`VERIFIER-BOUNDARY.md`](VERIFIER-BOUNDARY.md) and ADR-0016.

### Human

Final authority, on all of:

- accepting work;
- authorising repository writes;
- approving deployment;
- production release;
- changing security boundaries;
- changing the frozen contracts;
- accepting risks or exceptions.

**Eval-lab must never automatically merge, deploy, or declare production
readiness.** No outcome it can emit authorises any of those.

## Canonical protocol ownership

| Protocol | Version | Owner | Consumer |
|---|---|---|---|
| JobSpec format | (Agent-workbench's own) | Agent-workbench | referenced by digest only |
| `jobspec-reference` | `1.0.0` | Eval-lab | how Eval-lab names a JobSpec without holding it |
| `evidence-intake` | `1.0.0` | Eval-lab | Agent-workbench produces against it |
| `evallab-outcome` | `1.0.0` | Eval-lab | humans and downstream readers |
| `verifier-envelope` | `1.0.0` | **jointly frozen** public boundary | Eval-lab ↔ verifier |

Rules, frozen:

1. Agent-workbench produces evidence against a **pinned released** evidence-schema
   version. Eval-lab validates **that exact version**.
2. A protocol change requires a **new version**. An existing version is never
   silently reinterpreted — not to fix a bug, not to add a field, not to relax a
   constraint.
3. Existing recorded evidence stays interpretable under the version it was
   produced against. The cost is that old validators are kept, and that cost is
   accepted deliberately.
4. Verifier internals remain private even though the envelope is public. The
   envelope says what may cross the boundary, not what happens behind it.

## The terminal demonstration

Milestone 2 is complete when this runs end to end:

```
Agent-workbench-compatible evidence fixture or real evidence bundle
  → durable Eval-lab Temporal workflow
  → evidence intake and schema validation
  → hash and JobSpec correspondence verification
  → isolated public deterministic checks
  → versioned rubric-scoring boundary
  → optional controlled CKFF scorer invocation
  → protected verifier request boundary
  → minimal verifier attestation returned
  → deterministic Eval-lab decision policy
  → versioned evaluation report and evidence manifest
  → human review required
```

The mandatory CI demonstration runs **without paid credentials**, using
deterministic provider and verifier test adapters. The live CKFF path is
separately gated and manual-only.

## Fixtures come before implementation

Public valid and hostile fixtures exist so Eval-lab development never depends on
Agent-workbench being finished, and so every rejection path has a target before
anyone writes the code that is supposed to hit it. They live in
`contracts/fixtures/` with a manifest naming, for each hostile fixture, the exact
rejection reason expected.

## What is deliberately not built

Not in Eval-lab, at any point in this milestone: Agent-workbench execution
features; a coding-agent runtime; a custom scheduler, queue or container engine;
hidden tests; hard-gold logic; private verifier behaviour; automatic merging or
deployment; unrestricted repository execution; production-gateway benchmarking;
silent retries; cross-model fallback; model substitution; automatic reruns of
failed model attempts; leaderboards before calibration and experiment contracts
are frozen; a second live provider adapter before the first passes the complete
lifecycle; and any claim that Eval-lab proves correctness or production safety.

## Related documents

- [`MILESTONE-2-ACCEPTANCE.md`](MILESTONE-2-ACCEPTANCE.md) — what must be demonstrated
- [`AGENT-WORKBENCH-HANDOFF.md`](AGENT-WORKBENCH-HANDOFF.md) — the producer's side
- [`VERIFIER-BOUNDARY.md`](VERIFIER-BOUNDARY.md) — the sealed boundary
- [`MILESTONE-2-STATUS.md`](MILESTONE-2-STATUS.md) — live progress
- ADR-0014 … ADR-0020 — the decisions behind this contract
