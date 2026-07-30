# ADR-0006 — A degraded, explicitly non-durable local runner

- **Status:** Accepted
- **Date:** 2026-07-30

## Context

Temporal execution needs a server. The Python SDK's `WorkflowEnvironment.
start_local()` downloads the dev-server binary from `https://temporal.download/...`;
the compose path pulls container images. In the sandbox this was built in, **both
are denied by egress policy** (403 at the egress proxy for `temporal.download`, and
for every container registry: Docker Hub, GHCR, and Quay blob/manifest fetches).

That is an environment restriction, not a design problem — but a skeleton that
cannot execute at all in its own build environment cannot be honestly verified.

## Decision

Ship **two execution paths behind one entry point**, `app/runner.py`:

1. **`temporal` (default, primary).** Connects to `TEMPORAL_ADDRESS`, registers the
   `LangGraphPlugin`, starts/uses the worker, and executes
   `CodingEvaluationWorkflow`. This is the real path and the one Compose and CI run.
2. **`local` (degraded).** Compiles the **same** LangGraph graph and calls
   `ainvoke()` directly.

The runner selects `temporal` when a server is reachable and `local` otherwise, and
**stamps the choice into `EvaluationRun.execution_mode` and onto the root span**, so
no artifact can be mistaken for a durable run.

## Why this does not reimplement Temporal

The degraded path adds **no** retry logic, **no** timers, **no** persistence, **no**
recovery, and **no** scheduling. It is one call to `graph.ainvoke()` — plain
LangGraph usage, the library doing its own job. Everything Temporal owns is simply
**absent** in that mode, and absent loudly:

- `ReliabilityDecision.durable_execution` is `False`.
- The reliability report carries a `NON_DURABLE_EXECUTION` caveat.
- `docs/limitations.md` states that `local`-mode results say nothing about crash
  recovery.

Silently degrading would have been the wrong call; a mode flag that propagates into
the artifacts is the honest one.

## Consequences

- Temporal integration tests **skip** (not fail) when no server is reachable, and
  the skip reason names the blocked host so a reader can tell "not verified here"
  from "verified passing".
- In an unrestricted environment `make up && make demo` exercises path 1 and the
  workflow appears in the Temporal UI. In this sandbox, only path 2 was executed —
  recorded as such in the final report.
