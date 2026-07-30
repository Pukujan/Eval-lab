# ADR-0012 — A missing observability artifact is an infrastructure failure, not a rejection

- **Status:** Accepted
- **Date:** 2026-07-30
- **Supersedes:** part of ADR-0009 (gate composition)

## Context

Task 1 made `required_artifacts_present` one of eight **rejection** gates. So a run
whose spans never reached the collector produced:

```
outcome: rejected
rationale: Rejected by 1 gate(s): required_artifacts_present.
```

That sentence is wrong in a way that matters. Nothing about a dropped span implies
anything about the patch. The system reported a coding verdict it had not reached,
and a reader skimming outcomes would count it against the candidate.

Task 2A adds more ways for the harness — not the patch — to fail: an unreachable
Temporal server, an unreachable Phoenix, an activity that times out, a worker that
dies without a replacement, a corrupt evaluation artifact. Every one of them needs
the same treatment.

## Decision

**Three-way classification, checked in this order.**

| Condition | Outcome |
|---|---|
| Harness error, Temporal unavailable, Phoenix unavailable, missing mandatory trace, worker failure without recovery, corrupt evaluation artifact, activity timeout | `infrastructure_failure` |
| Build failure, test regression, hidden-test failure, invariant violation, prohibited file change, symptom suppression, unsupported diagnosis | `rejected` |
| No surviving hypothesis, materially contradictory evidence, mechanism not tied to the repair | `abstained` |
| All gates pass and the harness is sound | `accepted_for_review` |

Concretely:

1. `required_artifacts_present` is **removed from `REJECTION_GATES`** and lives in
   `INFRASTRUCTURE_GATES`. It still runs, and its result still appears in
   `gate_results` — it just routes to a different outcome.
2. `GateContext.infrastructure_incidents` carries incidents the caller observed.
3. `decide()` checks infrastructure **first**, before any patch verdict.
4. A missing artifact still **blocks acceptance**. It is not downgraded to a
   warning; it simply stops claiming the patch is at fault.

## The guard that makes this safe

Moving failures into an "it's the infrastructure's fault" bucket is exactly the
mechanism by which a system stops reporting real defects. So the bucket is
closed, not open:

```python
class InfrastructureIncident(StrEnum):
    TEMPORAL_UNAVAILABLE = "temporal_unavailable"
    PHOENIX_UNAVAILABLE = "phoenix_unavailable"
    MISSING_MANDATORY_TRACE = "missing_mandatory_trace"
    WORKER_FAILURE_WITHOUT_RECOVERY = "worker_failure_without_recovery"
    CORRUPT_EVALUATION_ARTIFACT = "corrupt_evaluation_artifact"
    ACTIVITY_TIMEOUT = "activity_timeout"
    HARNESS_ERROR = "harness_error"
```

`classify_infrastructure_incident()` **raises** on any kind not in that enum.
`hidden_tests_failed` cannot be classified as infrastructure, because it is not on
the list and there is no free-text path. `tests/unit/test_failure_classification.py`
asserts the refusal.

The patch-level gate results are still attached to an `infrastructure_failure`
decision, so a reader can see every measurement that was taken. What they cannot
do is mistake those measurements for a verdict — the rationale says explicitly
that no patch verdict was reached.

## Consequences

- An explicit `EXECUTION_MODE=temporal` that cannot reach a server is now an
  incident rather than a silent fallback to the degraded local runner. Asking for
  durability and not getting it must not look like getting it.
- Phoenix configured but unreachable is an incident: tracing that was requested
  and did not happen leaves the run without its mandatory artifacts.
- `auto` mode falling back to local remains a documented **caveat**, not an
  incident — nobody asked for a guarantee there.
- Four terminal outcomes remain reachable and distinct; a test enumerates all
  four to keep it that way.
