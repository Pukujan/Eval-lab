# Project contract amendment 1 — continuous phase execution

**Effective:** 2026-08-01  
**Authorization:** Human instruction in the project session after approval of the one-model, one-fixture experiment.  
**Applies to:** Experiment 1 only, as defined in `docs/EXPERIMENT-1-EXECUTION-PLAN.md`.

This amendment changes the operating cadence of `docs/PROJECT-CONTRACT.md`. It does not weaken repository boundaries, correctness gates, credential rules, verifier isolation, or the prohibition on automatic deployment and production-readiness claims.

## Standing execution authority

Once the exact Experiment 1 scope is frozen in the execution plan, implementation proceeds automatically through its listed phases. A new human approval is not required between ordinary implementation phases.

For each phase, the implementing agent must:

1. make only the changes assigned to that phase;
2. run the phase's fixture checks, unit tests, integration tests, and boundary checks;
3. fix failures that are within the approved scope;
4. record the phase result, changed files, checks run, and remaining risks;
5. advance automatically when every required gate passes.

The user receives phase-result updates, not repeated permission requests.

## What does not pause progression

The following do not require a new approval when they remain inside the frozen plan:

- creating implementation branches;
- editing approved files in Agent-workbench or Eval-lab;
- adding tests and fixtures required by the plan;
- running credential-free tests and mocked integrations;
- opening and merging scoped pull requests after their required checks pass;
- correcting defects found by those checks;
- proceeding from one approved phase to the next.

## Mandatory stop conditions

Work stops and reports the exact blocker only when at least one of these is true:

- a required test or invariant cannot be made to pass without changing approved scope or a frozen public protocol;
- current repository state contradicts the execution plan in a material way;
- a security boundary, credential class, or repository ownership boundary would have to change;
- a live CKFF prerequisite remains unverified at the point a live request is required;
- a requested or resolved model cannot be proven to match the frozen alias selection;
- private verifier access or inference would be required;
- destructive production action, deployment, credential rotation, or automatic acceptance would be required;
- the task would need a new fixture, extra model, calibration, dashboard, benchmark category, or broader Milestone 2 workstream.

An ordinary implementation bug is not a stop condition. It is fixed and retested within the approved phase.

## Live-request rule

All credential-free and mocked phases continue automatically. No live provider request is made until every live-request prerequisite in `docs/PROJECT-CONTRACT.md` is evidenced. If those prerequisites are still missing after the offline path is complete, the project stops only at the live gate and reports the missing evidence precisely.

## Completion rule

Experiment 1 ends after:

- one selected live coding model authors one original patch for the frozen fixture;
- Agent-workbench emits one versioned evidence bundle;
- Eval-lab evaluates that bundle through the approved minimal path;
- the outcome and all phase evidence are presented for human review.

Human review remains the final authority. This amendment does not authorize deployment, production release, a production-readiness claim, or access to private verifier internals.
