# EXP-026 — GLEIF objective track

## Status

Preregistered. Source snapshot, canonical records, results, and report are
intentionally absent until the snapshot-freeze checkpoint is committed.

## Research question

Can inexpensive independent judges extract and resolve objective legal-entity
registry facts from a frozen GLEIF snapshot while preserving coverage and
source evidence?

## Primary comparison

Use the same canonical records, context cap, prompt contract, and blind split
for the selected comparison routes. Report accuracy only for resolved legal
labels and keep provider, parse, timeout, and rate-limit statuses separate.

## Stopping rule

Do not score the blind split until the source manifest, snapshot fingerprint,
canonicalization version, split mapping, and public report are committed.
Terminate a provider arm only after its records have terminal status or its
declared recovery budget is exhausted.
