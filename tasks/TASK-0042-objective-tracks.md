# TASK-0042 — Objective real-world data tracks

## Status

Active — tracked by GitHub issue #45. EXP-026 is preregistered. The 2026-09-24
GLEIF Golden Copy LEI2 and RR archives have been downloaded to the ignored
`outputs/` source cache; their hashes and retrieval details are recorded in
`experiments/EXP-20260922-026-gleif-objective-track/source-manifest.json`.
The canonical adapter and dataset fingerprint are not yet complete. The Grok
ablation EXP-025 is complete and will remain immutable. SEC EDGAR/XBRL and
CourtListener remain subsequent append-only tracks.

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
GitHub issue #45 tracks the EXP-026 source snapshot and adapter. The dated
LEI2 and RR archives are now downloaded and recorded in the source manifest;
canonical extraction, normalization, adapter, and model scoring remain
unfinished. No model calls have occurred.

## Files in scope

- `tasks/TASK-0042-objective-tracks.md`
- `checkpoints/CURRENT.md`
- `docs/OBJECTIVE_DOMAIN_TRACKS.md`
- `experiments/EXP-20260922-026-gleif-objective-track/`
- `src/eval_lab/datasets/gleif.py`
- `scripts/freeze_gleif_snapshot.py`
- `scripts/build_gleif_dataset.py`
- `tests/test_gleif.py`

## Goal

Prepare auditable objective real-world evaluation tracks after the completed
benchmark comparison, beginning with GLEIF and preserving non-objective
boundaries for SEC and CourtListener.

## Acceptance criteria

The Objective, Scope, Gold and safety rules, and Acceptance sections above are
the acceptance criteria for this preparation checkpoint.

## Checkpoint log

This file and checkpoints/CURRENT.md record the preregistration. Source
archives have been downloaded but are not yet transformed or frozen as a
canonical dataset; no model calls have occurred.

## Handoff

Implement the snapshot freezer and adapter against the downloaded archives,
record the canonical dataset fingerprint, then run public canaries. Do not
score a blind split before the source manifest, split, and adapter artifacts
are committed.

## Checkpoint log

### 2026-09-24 — EXP-026 source archive checkpoint

Status: source archives downloaded; snapshot manifest recorded; adapter and
canonical dataset not yet implemented. No model calls were made.

Files changed: `checkpoints/CURRENT.md`, this task file, and
`experiments/EXP-20260922-026-gleif-objective-track/source-manifest.json`.
The ZIP archives are retained in the ignored local `outputs/` source cache;
the manifest records URLs, archive sizes, SHA-256 hashes, reported CDF versions
and record counts, retrieval date, and CC0 1.0 licensing.

Commands run: source archive inventory; repository workspace-policy check.
Result: workspace policy passed. Full local gates are run by the required
checkpoint publisher before commit. Decision: preserve this dated snapshot
and use it as the input to the adapter. Unresolved: normalized dataset
fingerprint, entity-disjoint split, adapter, and public canary results.

Next atomic action: implement snapshot extraction, deterministic
canonicalization, and entity-disjoint split; then run public canaries only.
