# ADR-0013 — Inline workers use a run-scoped task queue

- **Status:** Accepted
- **Date:** 2026-07-30

## Context

Two kinds of worker poll for coding-evaluation work:

- the **long-lived Compose worker**, running inside `rws-worker`, and
- an **inline worker** started by `execute_investigation_workflow()` for the
  duration of a single run.

Both originally polled `reliability-walking-skeleton`.

The investigation's activities are filesystem-bound. `execute_probes` runs a probe
inside a working copy whose absolute path is carried in the workflow state. When
the inline worker runs on the host, that path is a host path — and Temporal will
hand the activity to *whichever* worker polls first.

If the containerised worker won, it would receive a path that does not exist in
its filesystem. The probe would fail, and the failure would surface as a broken
evaluation rather than as what it was: two workers disagreeing about what the
filesystem looks like. Intermittent, environment-dependent, and very easy to
misdiagnose as flakiness in the fixture.

This was found while wiring Task 2A's CI, before it caused a wrong result.

## Decision

`execute_investigation_workflow()` derives a **run-scoped task queue**:

```python
def run_scoped_task_queue(settings, run_id) -> str:
    return f"{settings.temporal_task_queue}-{run_id}"
```

The inline worker registers on that queue and the workflow is started on it, so
the only worker that can be given an activity referring to a working copy is the
worker that created it.

The long-lived Compose worker keeps polling the shared queue and continues to
serve workflows started externally — which is what `make up` and the CI
task-queue-describe check exercise.

## Alternatives rejected

- **Mount the working copies into the container.** Couples the host and container
  filesystems and only works when both are on the same machine. Fixes the symptom
  and leaves the ambiguity.
- **Stop running the Compose worker.** Removes the very thing Task 2A is meant to
  demonstrate.
- **Make activities re-resolve paths.** Guesswork about which filesystem you are
  on, in the middle of a probe. No.

## Consequences

- Each inline run creates a short-lived task queue. Temporal handles this fine —
  queues are cheap and implicit — but a queue listing shows one entry per run.
- Container and host runs are both safe, so the evaluation can execute inside the
  worker container (exercising container DNS on the real path) or on the host.
- The shared-queue worker registration remains observable via
  `temporal task-queue describe`, which is what CI checks.
