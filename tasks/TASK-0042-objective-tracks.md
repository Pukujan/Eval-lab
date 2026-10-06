# TASK-0042 — Objective real-world data tracks

## Status

Complete checkpoint — tracked by GitHub issue #45. EXP-026 is preregistered and
its dataset is now frozen. The 2026-09-24 GLEIF Golden Copy LEI2 and RR archives
are frozen, verified, and extracted; the canonical adapter and dataset builder
emit 1920 objective records (1000 blind holdout + 920 public selection) over an
entity-disjoint 300-entity split. The dataset, split, typed question spec, pool
manifest, and their SHA-256 fingerprints are committed before any blind scoring,
and a 10-record public Jev canary passed (10/10 `ok`). The Grok ablation EXP-025
is complete and remains immutable. SEC EDGAR/XBRL and CourtListener remain
subsequent append-only tracks.

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
GitHub issue #45 tracks the EXP-026 source snapshot and adapter. The dated LEI2
and RR archives are frozen, verified, and extracted; `scripts/freeze_gleif_snapshot.py`
records the snapshot and `scripts/build_gleif_dataset.py` builds the canonical
dataset and comparison pool from it. The 300-entity split is entity-disjoint
(170 calibration / 190 test), 1920 records are emitted (920 public / 1000 blind),
and a 10-record public Jev canary ran clean. The blind split has not been scored.

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

This file and checkpoints/CURRENT.md record the preregistration and the dataset
freeze. Source archives have been frozen, verified, and transformed into the
canonical dataset; a 10-record public canary ran clean and no blind split has
been scored.

## Handoff

The freezer, adapter, dataset builder, split, and fingerprints are committed and
the public canary passed. The next step is to score the public selection and then
the blind holdout through the shared comparison runner
(`scripts/run_fast_jev_arm.py --pool experiments/EXP-20260922-026-gleif-objective-track`),
gated by the EXP-026 stopping rule. Do not modify the completed artifacts; a
changed dataset, prompt, or split needs a new experiment ID.

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

### 2026-10-05 — EXP-026 GLEIF adapter and dataset frozen

Status: the canonical GLEIF adapter and dataset are complete and frozen before
blind evaluation. No blind split has been scored.

Completed work: `scripts/freeze_gleif_snapshot.py` verifies the dated LEI2 and
RR archives by SHA-256 and byte count, extracts them, and records the snapshot
in `frozen-snapshot.json` (extracted CSV names, the 338-column LEI2 header, and
row counts). `src/eval_lab/datasets/gleif.py` provides the canonical adapter:
`GleifEntity`, `iter_entities`, `normalize_lei`, SHA-256 `entity_split`, and the
deterministic claim builders (`status_claims`, `jurisdiction_claims`,
`category_claims`, `registration_date_claims`, `alias_claims`, `parent_claims`).
`scripts/build_gleif_dataset.py` deterministically samples 300 entities and 60
relationships and emits 1920 objective records (1000 blind holdout + 920 public
selection) with `pass`/`fail` gold from the frozen source field
(`deterministic_verifier` provenance, verifier `gleif-registry-facts-v1`). The
300-entity split is entity-disjoint (170 calibration / 190 test), so no LEI
appears on both sides; all families for one entity share its split.

Exact files changed: `experiments/EXP-20260922-026-gleif-objective-track/`
(`source-manifest.json`, `frozen-snapshot.json`, `canonical-records.jsonl`,
`records.jsonl`, `split-manifest.json`, `typed-question-spec.json`,
`pool-manifest.json`, `pool-checksums.sha256`, `experiment.yaml`, `README.md`),
`scripts/freeze_gleif_snapshot.py`, `scripts/build_gleif_dataset.py`,
`src/eval_lab/datasets/gleif.py`, `tests/test_gleif.py`, `checkpoints/CURRENT.md`.

Commands run: `scripts/freeze_gleif_snapshot.py`; `scripts/build_gleif_dataset.py`;
`scripts/run_fast_jev_arm.py --pool experiments/EXP-20260922-026-gleif-objective-track
--partition public_selection --model typesafe/jev-1.13 --limit 10 --workers 4`;
`.venv\Scripts\python.exe -m pytest tests/test_gleif.py -q`; full local gates via
the checkpoint publisher.

Test results: `tests/test_gleif.py` 13 passed; full suite 222 passed; repository
workspace-policy check passed. Public canary: 10/10 `ok`, 0 provider errors,
2.24 s, resolved model `typesafe/jev-1.13-20260917`, native probabilities and
confidence preserved (`gold_not_used_for_provider_request: true`).

Decisions made: sample the frozen snapshot deterministically by seed 260922 and
selection ratio 0.002; dedupe relationships by start node and entities by LEI so
`parent:{start}` and per-entity problem IDs are unique; record the canonical
fingerprint `sha256:1267c92547dc40d9d63c90be241da85361509f812f9cea63246b28f5f4cc8203`
in both the source manifest and pool manifest; advance `experiment.yaml` status
from `preregistered` to `frozen` and fill the previously deferred
`dataset.version`/`fingerprint` (no hypothesis, metric, split, calibration, or
stopping-rule field changed).

Unresolved questions: the blind holdout has not been scored; the shared
comparison runner's blind run and the results/report remain.

Next atomic action: score the public selection and then the blind holdout
through `scripts/run_fast_jev_arm.py`, gated by the EXP-026 stopping rule.
