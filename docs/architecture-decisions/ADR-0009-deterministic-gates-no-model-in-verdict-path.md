# ADR-0009 — No model output is in any verdict path

- **Status:** Accepted
- **Date:** 2026-07-30

## Context

The point of the skeleton is that an incorrect patch is **deterministically**
rejected. Any gate that consults a model to decide pass/fail makes the verdict a
sample from a distribution, and the whole claim collapses.

## Decision

`app/reliability/gates.py` contains **no model call, and imports no model client.**
Every gate is a pure function of observable artifacts:

| Gate | Decides from |
|---|---|
| `build_succeeds` | subprocess exit code |
| `no_test_regression` | visible-test exit codes, before vs after |
| `hidden_tests_pass` | hidden-test exit code |
| `primary_invariant_holds` | the invariant probe's committed-result count |
| `evidence_supports_diagnosis` | set relations over recorded `Evidence` ids |
| `no_prohibited_file_changes` | path set diff against the prohibited manifest |
| `not_symptom_suppression` | **effect-counter** delta, not log-line count |
| `required_artifacts_present` | span ledger + audit-row existence |

Models are confined to *proposing* — hypotheses, probes, repair candidates. Gates
*dispose*. A model can influence what gets tried; it can never influence whether a
trial passed.

## The gate that carries the weight

`not_symptom_suppression` is the one that catches the duct-tape patch, and it is
deliberately not "did duplicate output disappear". The fixture's external effect
handler increments a counter *inside the processing path*. Deduplicating the output
log leaves that counter at 2 for one logical job id. So:

- duct-tape patch → visible tests green, output looks clean, **effect counter = 2**
  → `rejected`.
- known-good patch → duplicate processing never starts, **effect counter = 1** →
  eligible for `accepted_for_review`.

A gate that counted log lines would pass the duct-tape patch. That distinction is
the whole experiment.

## Vocabulary

The only positive outcome is **`accepted_for_review`**. The words `approved`,
`correct`, `safe`, and `production_ready` do not appear as outcomes anywhere in the
codebase, and a test greps for them to keep it that way.

## Consequences

- Gates are unit-testable without any model, network, or credential.
- `abstained` is a first-class outcome, distinct from `rejected`: no surviving
  hypothesis, materially contradictory evidence, or an unestablished causal link
  produce abstention, not a negative verdict.
- `infrastructure_failure` is likewise distinct — a broken harness must never be
  reported as a failed patch.
