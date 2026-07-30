# ADR-0003 — Pydantic v2 is the one schema-validation library

- **Status:** Accepted
- **Date:** 2026-07-30

## Context

The brief requires runtime-validated, versioned schemas and "one documented
schema-validation library". Candidates: Pydantic v2, attrs+cattrs, msgspec,
dataclasses + jsonschema.

## Decision

**`pydantic==2.13.4`**, used for all 15 domain schemas and nothing else.

Reasons that are specific to this stack rather than general preference:

1. Temporal ships **first-party Pydantic support** — `temporalio.contrib.pydantic.
   pydantic_data_converter` — so domain models cross the workflow/activity boundary
   without a hand-written converter. With msgspec or attrs we would write that
   converter ourselves, which is custom code in a place the platform already covers.
2. LangGraph state and LiteLLM both already sit in a Pydantic-shaped ecosystem, so
   there is no second validation dialect in the process.
3. JSON Schema generation is built in, and Promptfoo's deterministic assertions
   validate mock-model output against exactly those generated schemas — one
   definition, two consumers, no drift.

## Conventions

- Every schema carries an explicit `schema_version: Literal[1]` field. Versioned
  means versioned in the payload, not just in the file.
- `model_config = ConfigDict(extra="forbid", frozen=True)`. Unknown fields are an
  error, not a shrug — evidence records that silently absorb junk are worthless.
- Sequence fields are `tuple[...]`, because Pydantic's `frozen=True` is shallow and
  a frozen model holding a mutable `list` is not actually immutable.

## Consequences

- `extra="forbid"` means a model that invents a field fails loudly at the boundary.
  That is the intent: it is how a malformed hypothesis becomes a caught error
  instead of a silently dropped one.
- Schema evolution requires bumping the `Literal` and writing a migration; there is
  no implicit tolerance.
