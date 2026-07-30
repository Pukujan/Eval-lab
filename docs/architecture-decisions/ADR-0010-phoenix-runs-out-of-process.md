# ADR-0010 — Phoenix runs out-of-process; the app carries only the OTLP client

- **Status:** Accepted
- **Date:** 2026-07-30

## Context

`arize-phoenix==19.10.0` is a full server: FastAPI, GraphQL, SQLAlchemy, Alembic,
a React build. Installing it into the application environment drags that entire
closure alongside `temporalio`, `langgraph`, `litellm` and `inspect-ai`, and the
resolver then has to satisfy all of them at once.

## Decision

Split the trace **producer** from the trace **store**.

- **Application environment** gets only the light client side:
  `arize-phoenix-otel==0.16.1`, `opentelemetry-sdk==1.44.0`,
  `opentelemetry-exporter-otlp-proto-http==1.44.0`,
  `openinference-instrumentation-langchain==0.1.68`.
- **Phoenix server** runs in its own container
  (`arizephoenix/phoenix:version-19.10.0`), or, where containers are unavailable,
  its own virtualenv (`.venv-phoenix`) started by `scripts/serve_phoenix.sh`.

The only coupling is OTLP over HTTP to `:6006/v1/traces`. That is a wire protocol,
not a shared dependency graph.

## Persistence

Verified from `phoenix/config.py` in the pinned version:

```
PHOENIX_WORKING_DIR=/data
PHOENIX_SQL_DATABASE_URL=sqlite:////data/phoenix.db
PHOENIX_PORT=6006
PHOENIX_GRPC_PORT=4317
```

SQLite-backed and volume-mounted, which is what "persistent local storage" requires.
`PHOENIX_ENABLE_PROMETHEUS` is left off — Prometheus is on the prohibited list.

## Consequences

- The app can be installed, type-checked and unit-tested without Phoenix present at
  all; tracing degrades to a no-op exporter when `PHOENIX_ENDPOINT` is unset.
- Because export is fire-and-forget, the `required_artifacts_present` gate checks
  our **own in-process span ledger** rather than trusting that the collector
  received anything. A dropped span must not silently satisfy an artifact gate.
- We write no trace storage and no trace UI — the explicit prohibition. Phoenix owns
  both.
