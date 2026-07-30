# ADR-0002 — Temporal owns durability; LangGraph owns the investigation graph

- **Status:** Accepted
- **Date:** 2026-07-30

## Context

Temporal and LangGraph overlap on paper. LangGraph ships checkpointers, retry
policies on nodes, and interrupt/resume. Temporal ships durable execution, retries,
timers, and recovery. Running both without a boundary produces two competing
sources of truth about "what has already happened" — the exact failure the brief
forbids ("LangGraph must not recreate Temporal persistence, retries, timers, or
recovery").

## Decision

Use the **official Temporal LangGraph plugin** (`temporalio.contrib.langgraph`,
shipped inside `temporalio==1.31.0` behind the `langgraph` extra) as the single
seam between them.

- LangGraph defines **shape**: the bounded investigation graph, its state, its
  transitions, its conditional edges.
- Temporal provides **execution guarantees**: every node that does real work is
  declared `metadata={"execute_in": "activity"}`, so the plugin runs it as a
  Temporal Activity and Temporal — not LangGraph — supplies the retry policy,
  the `start_to_close_timeout`, cancellation, and the replayable history.
- The only checkpointer permitted is `InMemorySaver`, and only where LangGraph
  structurally demands one. Temporal's history *is* the durable record.

## Alternatives rejected

- **LangGraph alone with a SQLite checkpointer.** Reimplements Temporal's recovery
  story badly, and the brief explicitly assigns recovery to Temporal.
- **Temporal alone, hand-rolling the investigation state machine as activities.**
  Reimplements LangGraph's graph traversal and conditional routing. Also loses the
  ability to run the same graph outside Temporal for fast unit tests.
- **A hand-written node→activity adapter.** This is the single most tempting piece
  of custom code in the project and it is exactly what the official plugin already
  is. Writing it would violate "do not recreate functionality already provided by
  the selected platforms".

## Consequences

- Every node must carry `execute_in`; the plugin refuses to default it. Enforced by
  a test that walks the graph and asserts each node declares it.
- The plugin is **experimental** (its own README says so). Recorded as a known
  limitation; the mitigation is that the graph is also directly invocable, so a
  plugin regression degrades the durability story without destroying the skeleton.
- Node functions must be serialisation-friendly, because their state crosses the
  activity boundary through Temporal's payload converter.
