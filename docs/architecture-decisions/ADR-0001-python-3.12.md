# ADR-0001 — Target CPython 3.12

- **Status:** Accepted
- **Date:** 2026-07-30

## Context

The brief allows "Python 3.12 or the current officially supported stable Python
version after verifying compatibility". 3.13 and 3.14 exist. Picking the newest
runtime is only correct if every pinned dependency actually supports it.

## Decision

Target **CPython 3.12.3**, `requires-python = ">=3.12,<3.13"`.

## Evidence

`requires_python` read from PyPI metadata at pin time:

| Package | Declares |
|---|---|
| `temporalio==1.31.0` | `>=3.10` (LangGraph plugin warns below 3.11) |
| `langgraph==1.2.10` | via extra, `>=3.11` for Functional API / `interrupt()` |
| `inspect-ai==0.3.251` | `>=3.10` |
| `arize-phoenix==19.10.0` | `>=3.10,<3.15` |
| `litellm==1.94.0` | `>=3.10,<3.15` |

3.13 would satisfy the declared ranges, but nothing in the skeleton needs a 3.13
feature, and every bump costs a full re-verification of a 6-platform integration.
3.12 is the version with the widest wheel coverage across this exact set.

## Consequences

- The upper bound `<3.13` is deliberate: it makes a runtime bump a conscious,
  reviewed change rather than something that drifts in via a base-image update.
- Revisit when a dependency requires 3.13, not before.
