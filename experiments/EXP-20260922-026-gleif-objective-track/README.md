# EXP-026 — GLEIF objective track

## Status

Dataset frozen. The 2026-09-24 GLEIF Golden Copy snapshot, the 1920-record
canonical dataset (1000 blind + 920 public), the entity-disjoint split, and the
typed question spec are committed. `results.json` and `report.md` are absent
until the scored run; no blind split has been scored.

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
