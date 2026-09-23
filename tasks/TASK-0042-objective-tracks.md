# TASK-0042 — Objective real-world data tracks

## Status

Prepared and preregistered; no live source fetch or model scoring has been
started. EXP-026 is the first executable track and uses GLEIF. SEC EDGAR/XBRL
and CourtListener are specified as subsequent append-only tracks.

## Objective

Extend the benchmark study beyond the frozen synthetic/typed pool using
public records whose claims can be checked against source data or deterministic
verifiers. Preserve the distinction between facts a source reports and claims
that require expert interpretation.

## Scope

- GLEIF first: LEI identity, status, names, dates, entity resolution, and
  parent/relationship records.
- SEC EDGAR/XBRL next: filing metadata, CIK/accession matching, typed facts,
  units and periods, arithmetic reconciliation, and evidence-span extraction.
- CourtListener next: opinion/docket metadata, chronology, citation lookup,
  quote attribution, and retrieval-plus-evidence tasks.
- Contract maintenance: add the required handoff headings to historical
  TASK-0040/TASK-0041 files and root results/report artifacts for completed
  EXP-025 so the repository-wide merge gate passes.
- Every source snapshot, license/access note, retrieval time, revision, and
  SHA-256 fingerprint must be committed before a blind run.
- Entity-disjoint or case-disjoint splits are mandatory. Generated aliases
  inherit the source entity split.

## Gold and safety rules

- Source facts are gold only for what the source explicitly records.
- Deterministic parsers and arithmetic verifiers outrank model judgments.
- Legal holdings, materiality, legal conclusions, and financial truth claims
  require expert adjudication or remain explicitly non-objective.
- No credentials, private filings, live legal advice, trading decisions, or
  cyber exploitation are in scope.
- Cybersecurity follow-on work is defensive only: refusal adherence, secret
  handling, prompt-injection resistance, sandbox-boundary compliance, and
  non-destructive simulated commands.

## Acceptance

1. EXP-026 GLEIF preregistration is committed before source retrieval.
2. A frozen source manifest records the GLEIF snapshot, revision, license,
   retrieval time, and fingerprint.
3. The adapter produces canonical records with source_problem_id, gold
   provenance, entity-disjoint split, and deterministic verification.
4. Provider failures remain execution statuses.
5. No legal or financial interpretation is promoted to objective gold without
   the required expert provenance.

## Checkpoint

Created the cross-domain protocol in docs/OBJECTIVE_DOMAIN_TRACKS.md and the
GLEIF preregistration in experiments/EXP-20260922-026-gleif-objective-track/.
No external data was fetched and no model calls were made. Next atomic action:
freeze a GLEIF source snapshot and implement the canonical adapter in a new
checkpoint before any blind scoring.

## Goal

Prepare auditable objective real-world evaluation tracks after the completed
benchmark comparison, beginning with GLEIF and preserving non-objective
boundaries for SEC and CourtListener.

## Acceptance criteria

The Objective, Scope, Gold and safety rules, and Acceptance sections above are
the acceptance criteria for this preparation checkpoint.

## Checkpoint log

This file and checkpoints/CURRENT.md record the preregistration and the fact
that no live source fetch or model call has occurred.

## Handoff

Freeze the GLEIF snapshot in a new atomic checkpoint before implementing or
running any adapter. Do not score a blind split from a moving API.
