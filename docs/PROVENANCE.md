# Provenance in Eval Lab: what is actually used

Status as of TASK-0059 (2026-09-24). This page says plainly which provenance
mechanisms produce and check the published numbers, and which ones don't. It is
also the namespace document for the `ev:` terms used in the chart-data JSON-LD
(see [Terms](#terms)).

## What produces the canonical paper's numbers

The paper (`paper/paper.md`, EXP-029) relies on **plain JSON plus SHA-256 hashes
and tests**. Nothing is semantic-web based.

| Mechanism | Where | Checked by |
| --- | --- | --- |
| Per-arm source hashes: every blind prediction file used, with its LF-normalized SHA-256 | `experiments/EXP-20260924-029-consolidated-judge-analysis/results.json` → `arms[*].sources` | `tests/test_judge_comparison_analysis.py` (full re-analysis must equal the committed file) |
| Blind record pool hash | same file, `records.sha256` | same |
| Analysis code commit | EXP-029 `experiment.yaml` → `code_commit`, `results_sha256` | `tests/test_chart_data_export.py` (results.json at `code_commit` must be byte-identical) |
| Figure sources | `paper/figures/benchmark/manifest.json` → `sources[*].sha256`, plus `*.data.json` with the plotted values | `tests/test_chart_data_export.py` |
| Generated tables and prose numbers | `<!-- generated:… -->` blocks in `paper.md` | `tests/test_judge_comparison_analysis.py` (drift and prose-number checks) |
| Per-run records | each run's `results.json` (`run_id`, `created_at_utc`, `requested_model`, pool fingerprints), `checksums.sha256`, per-prediction `judge_id`/`provider_metadata` | experiment tests |

## Chart data export (TASK-0059)

`scripts/export_chart_data.py` writes the data behind the paper's interactive
charts to `paper/data/`:

- `judges-blind-760.json`: the explorer dataset. It contains dimensions, measures,
  entities, observations `(entity, slice, metric) → value, CI, n`, paired
  comparisons, experiments and runs. One entity is one judge arm (one run of one
  judge configuration).
- `charts/<figure>.json`: one file per paper figure, wrapping the figure's
  `*.data.json`.
- `index.json`: every file with its size and SHA-256, for the Design Bakery sync.

Rules:

- **No hand-typed numbers.** Values are copied from EXP-029 `results.json` or
  computed from its integer counts (breakdown-slice coverage and all-record
  accuracy with 95% Wilson intervals). The method is stated in `measures`.
- **Pooling policy.** Nothing is averaged across arms. The only merge is the
  declared EXP-015 + EXP-016 Qwen arm (`derived: true`). `aggregates` is empty
  in this release.
- **Blind holdout.** No record IDs, items or gold labels are exported. The finest
  level is one row per arm/run.
- **Structured settings.** Thinking, output-token cap, context cap, decision
  method, temperature, model family, model ID and public parameter count come
  from `paper/data/sources/arm-metadata.yaml`. Each entry cites evidence files.
  Tests check each entry against the arm's harness text and the recorded
  `provider_metadata`.

Every exported file is **also JSON-LD**. Its `@context` maps only the provenance
keys, to schema.org and W3C PROV-O. Everything else is ignored by JSON-LD
processors. The `provenance` object is a JSON-LD `@nest` containing:

- `wasGeneratedBy`: a `prov:Activity` with the full git commit, a dirty flag
  (outputs excluded), and the commit time as `endedAtTime`. It is associated with
  a `prov:SoftwareAgent`: the exporter at that commit, with its SHA-256.
- `wasDerivedFrom`: `prov:Entity` inputs, each a GitHub blob URL pinned to the
  commit, with `path`, `sha256` and `role`. The dataset's EXP-029 entity is in
  turn derived from every per-arm predictions file and the blind record pool
  (hash only).

**Squash merges.** The recorded commit is the branch commit the export ran on.
After a squash merge, that commit stays reachable through the PR on GitHub but
isn't on `main`. The SHA-256 values are the durable identity: tests recompute
every one, and the export is re-rendered with the recorded git fields and must
match byte for byte.

Validation (all in CI, `.github/workflows/ci.yml`):

| Check | Tool | File |
| --- | --- | --- |
| Whole-file structure: settings enums, hashes, repo-relative paths (no drive letters) | JSON Schema 2020-12 (`jsonschema`) | `schemas/research-chart-data.v1.schema.json` |
| Provenance graph: one activity with a 40-hex commit, dateTime and software agent; every source a commit-pinned IRI with a SHA-256 | SHACL (`pyshacl` over `rdflib` JSON-LD) | `schemas/chart-provenance.shapes.ttl` |
| Re-render equals committed; every recorded hash is current; clean tree; no blind IDs or gold keys; arm metadata consistent | pytest | `tests/test_chart_data_export.py` |
| Exports are current | `scripts/export_chart_data.py --check` | CI step |

To regenerate after changing inputs: commit the input changes first (the
exporter refuses to run on a dirty tree), then run
`uv run --locked python scripts/export_chart_data.py` and commit `paper/data/`.

## What is not used

- **OWL:** no ontology is defined or reasoned over. PROV-O and schema.org terms
  are reused as-is.
- **RDF/SPARQL stores, PROV-JSON, ML-Schema, Croissant:** not used.
- **RO-Crate 1.3 + PROV-O Turtle + SHACL** exist only for the archived TASK-0010
  release `benchmark/eval-lab-select-v0.1.0/`, produced by
  `scripts/generate_research_artifacts.py`. That release is frozen: its
  `provenance.ttl` uses placeholder `https://example.org/eval-lab/` IRIs and
  covers only EXP-012, and its files are checksummed, so it is kept as-is rather
  than regenerated. TASK-0059 decided to **keep and run** its validator:
  `scripts/validate_research_artifacts.py` now runs in CI and in
  `tests/test_chart_data_export.py`. It does not describe the canonical paper.

## Terms

The `ev:` prefix is `https://github.com/Pukujan/Eval-lab/blob/main/docs/PROVENANCE.md#`.

| Term | Meaning |
| --- | --- |
| <a id="schemaVersion"></a>`ev:schemaVersion` | chart-data schema version (`1.0`) |
| <a id="experimentId"></a>`ev:experimentId` | Eval Lab experiment identifier (`EXP-…`) |
| <a id="recordCount"></a>`ev:recordCount` | number of records in the population |
| <a id="gitCommit"></a>`ev:gitCommit` | full 40-hex commit the activity ran on |
| <a id="gitDirty"></a>`ev:gitDirty` | whether non-output files differed from that commit |
| <a id="sha256"></a>`ev:sha256` | LF-normalized SHA-256 of the entity's bytes |
| <a id="path"></a>`ev:path` | repository-relative path |
| <a id="role"></a>`ev:role` | role of the input (e.g. `analysis_results`, `judge_predictions`) |
