# ADR-0005 — Temporal dev server with SQLite, not auto-setup with PostgreSQL

- **Status:** Accepted
- **Date:** 2026-07-30

## Context

Compose must include "Temporal development services and UI" and "any minimal
required database", while the brief explicitly forbids adding PostgreSQL "unless an
official requirement proves they are necessary".

The commonly-copied Temporal compose stack is `temporalio/auto-setup` +
PostgreSQL + a separate `temporalio/ui` container: three services and a forbidden
dependency.

## Decision

Run a single service: **`temporalio/temporal:1.8.1`** (digest
`sha256:59561b9ef060eaeb1f46cb6a1842d6cbdd8a393eb3b6d315ecef5fe2f0b1d7a6`)
executing `temporal server start-dev`.

```
temporal server start-dev \
  --ip 0.0.0.0 --port 7233 \
  --ui-port 8233 --ui-ip 0.0.0.0 \
  --db-filename /data/temporal.db \
  --namespace default
```

This one process provides the frontend, history, matching and worker services, the
**Web UI on 8233**, and SQLite-file persistence on a mounted volume.

So: no PostgreSQL, no separate UI container, persistence still survives a restart —
every requirement met, one service instead of three.

## Consequences

- `start-dev` is a **development** server. It is the right choice for a walking
  skeleton and the wrong choice for production; that is stated plainly in
  `docs/limitations.md` rather than left for a reader to discover.
- SQLite persistence means single-writer. Irrelevant at this scale.
- The Web UI is part of the same container, so the compose healthcheck covers both
  the gRPC frontend (7233) and the UI (8233).
