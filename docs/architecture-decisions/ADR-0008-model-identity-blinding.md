# ADR-0008 — Model identity blinding via a physically separate privileged store

- **Status:** Accepted
- **Date:** 2026-07-30

## Context

Solver, critic, verifier and comparison roles must see only pseudonyms. Real
vendor/model mappings live in a privileged audit store, must never reach a prompt or
an agent tool, and ordinary workflow components must be *provably* unable to read
them.

"Provably" rules out the usual approach — one database with a convention that some
tables are off-limits. A convention is not a boundary.

## Decision

**Two SQLite files, two access classes, no shared handle.**

| Store | File | Contains | Reachable from |
|---|---|---|---|
| Agent-accessible | `var/audit.db` | Evaluation runs, hypotheses, evidence, probe results, decisions — all keyed by **pseudonym only** | Workflow, graph nodes, activities, scorers, reports |
| Privileged | `var/privileged.db` | `AnonymousModelIdentity` → `PrivilegedModelIdentity` (vendor, real model id, endpoint) | `app/storage/privileged.py` **only** |

Enforcement, in order of strength:

1. **Separate files.** The agent-accessible connection is opened against
   `audit.db`. The mapping table does not exist in that file, so a leak requires
   opening a different database — not a forgotten `WHERE` clause.
2. **A capability object, not a global.** `PrivilegedIdentityStore` must be
   constructed with an explicit `PrivilegedAccess` token. Workflow code has no way
   to mint one; the eval harness constructs it outside the workflow boundary.
3. **Read-only, URI-mode connections** (`file:...?mode=ro`) for every reader that
   only needs lookups.
4. **Egress redaction.** `app/models/blinding.py::assert_blinded` scans any
   outbound prompt payload for vendor tokens and real model ids and raises
   `IdentityLeakError` before the request leaves. Applied to prompts *and* to span
   attributes.

## Randomisation

Per `EvaluationRun`: pseudonyms are `secrets.token_hex`-derived (`model-<8 hex>`),
regenerated per run, and candidate order is shuffled with a **run-seeded**
`random.Random(run_seed)` — reproducible for a given run id, unpredictable across
runs. Response structures are normalised so a vendor cannot be fingerprinted from
response shape.

## What this does *not* defend against

A caller that already has filesystem access can open `privileged.db` directly. This
is a *code-structure* boundary within one trust domain, not a multi-tenant security
boundary. Recorded as **T-2** in the threat model. Making it a real boundary needs
OS-level separation (separate uid, or the store behind an RPC), which is deferred.

## Consequences

- Tests assert the negative: workflow-visible surfaces expose no vendor string, and
  the agent-accessible connection genuinely cannot resolve a pseudonym.
- Reputation-based routing is explicitly **not** implemented (out of scope).
