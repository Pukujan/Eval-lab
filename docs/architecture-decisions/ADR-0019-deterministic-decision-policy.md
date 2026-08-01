# ADR-0019 — The decision policy is deterministic; a rubric score is a measurement, not a decision

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

ADR-0009 established the property the whole lab rests on: an incorrect candidate
is **deterministically** rejected, because `app/reliability/gates.py` contains no
model call and imports no model client. Models propose; gates dispose.

Milestone 2 adds versioned calibrated rubric scorers — model-driven measurements
of things no exit code can measure — and a controlled provider boundary to reach
the models behind them. Those scorers are genuinely useful and they are samples
from a distribution. The moment one of them can change an outcome, "deterministically
rejected" stops being true for every run, not just the borderline ones.

## Decision

**The evaluation decision is a pure function of four deterministic inputs:**
intake-validation results, public deterministic check results, the minimal
verifier result (ADR-0016), and the infrastructure-incident set.

Rubric scores are recorded alongside the decision and consulted by nothing that
branches. Specifically, rubric output may never:

- flip an outcome in either direction;
- bypass, satisfy, or substitute for a gate;
- downgrade a `rejected` to an `abstained`, or the reverse;
- contribute to `accepted_for_review`;
- select which checks run, in what order, or against what.

That last one is the least obvious and the most important: **control flow is a
decision.** A scorer that picks the cheap path for a candidate it likes has
decided the outcome, whatever the code around it says.

### Ordering, which this repository has now learned twice

1. **Infrastructure first** (ADR-0012). A broken harness must never be reported
   as a failed candidate. `decide()` already checks this before anything else,
   and `classify_infrastructure_incident()` refuses any kind not on a closed
   enumeration so a coding failure cannot be laundered into an infrastructure
   excuse.
2. **Intake rejection next.** Malformed, tampered, incomplete or inconsistent
   evidence is a rejection of the *evidence* (ADR-0018). It is deterministic, and
   it is not an infrastructure fault — the harness worked; the input was bad.
3. **Observational rejection ahead of abstention.** This is
   `OBSERVATIONAL_GATE_NAMES` in `app/reliability/gates.py`, and it exists
   because of a real bug rather than a design instinct: the duct-tape patch
   originally *abstained* despite an effect counter reading 2, because abstention
   was checked before the gates. Abstention means "we could not tell"; an effect
   counter reading 2 means we could tell. Reporting a measurement as uncertainty
   understates a finding the system genuinely made, which is its own kind of
   dishonesty.
4. **Abstention**, only when nothing was directly observed to be wrong and the
   case could not be established.
5. **`accepted_for_review`**, which authorises nothing.

### Decide from observed behaviour, not from self-description

ADR-0009's rule extends unchanged to a three-repository world. Gates read exit
codes, counters, path sets, and set relations over recorded evidence ids. They do
not read what a candidate calls itself.

- A bundle containing `"verified": true` is a **claim by the producer**, data to
  check, never a finding (`docs/verification-baseline.md`).
- A reviewer statement saying "this looks correct" has the standing of a model
  completion (ADR-0014, ADR-0018).
- The four outcomes are exactly `accepted_for_review`, `rejected`, `abstained`
  and `infrastructure_failure`. `approved`, `correct`, `safe` and
  `production_ready` are forbidden as outcomes and
  `tests/unit/test_outcome_vocabulary.py` keeps them out.

## Alternatives rejected

- **Let a calibrated scorer break ties on borderline candidates.** This is the
  whole failure, arriving through the smallest available door. A tie broken by a
  sample makes the outcome a sample, and the property is lost for every run — you
  cannot tell from an outcome whether it was borderline.
- **Let a scorer route: choose which checks to run, or skip expensive ones.**
  Control flow is a decision, above.
- **Threshold the rubric score and make it a gate.** A threshold makes the score
  load-bearing, and it is still a model output. If numeric threshold material is
  ever wanted in a verdict, it belongs to the verifier, where it is private
  (ADR-0016) — a public threshold on a public rubric is also a public
  optimisation target.
- **Advisory-only, but displayed prominently, trusting humans to discount it.**
  Not a mechanism. The human is the final authority (ADR-0014); handing that
  authority a number with no standing and hoping for correct weighting is
  delegation, not design.
- **Fold intake failures into `infrastructure_failure`, since they are "not the
  candidate's fault".** They are the *evidence's* fault, and the evidence is the
  input. Routing bad input into an infrastructure excuse is exactly what the
  closed incident enumeration refuses, for exactly the same reason.
- **Use a scorer to decide whether to invoke the verifier.** Same objection with
  higher stakes: it lets a model decide which candidates get ground truth applied
  to them.

## Consequences

- **Rubric scores become calibration and comparison data, not decision data.**
  Their quality is measured against gold, not against agreement with outcomes —
  and measuring a scorer by its agreement with a decision it cannot influence is
  a legitimate experiment, whereas letting it influence the decision is not.
- **The policy stays unit-testable with no model, no network and no credential**,
  which is ADR-0009's consequence carried forward intact.
- **The cost is visible and will look wrong case by case.** The system will
  reject or abstain on candidates a good scorer would have accepted, and there is
  deliberately no mechanism by which the scorer wins. Anyone reading individual
  outcomes will find examples that feel like errors. They are the price of the
  outcomes being reproducible.
- **Not established: determinism of the policy is not determinism of its
  inputs.** Public deterministic checks execute code, and a flaky check produces
  different inputs on different runs. This ADR guarantees only that identical
  inputs give an identical outcome. Nothing here makes a flaky check stable, and
  a flaky check is an infrastructure problem, not a candidate problem.
- **Not established: `accepted_for_review` is not correctness.** One fixture, one
  bug class, mock models, no calibration and no benchmark generalisation
  (`docs/limitations.md`). Nothing in Milestone 2 changes that, and the outcome
  vocabulary exists to stop the report from implying otherwise.
