# Live Eval Lab — backend (TASK-0060, phase 2)

The read-only backend behind the Eval Lab explorer: a FastAPI service over a
Postgres 17 database, holding every committed experiment run and the paper's
frozen chart dataset, rebuilt from git.

Phase 2 covers the **models, migrations, the backfill loader and the public read
API**. Ingest (phase 3), the gravebuster deploy (phase 4), the design-bakery
`/eval-lab` route (phase 5), snapshot freeze/pull (phase 6) and hardening
(phase 7) are separate. See `docs/architecture/live-app.md` and issue #71.

## Quick start

```bash
cd live
docker compose up --build
```

That brings up Postgres 17 on `localhost:55432` (not 5432, so a local Postgres
does not clash), applies the Alembic migrations, backfills every committed run,
and serves the API on <http://localhost:8000>:

```bash
curl -s localhost:8000/api/v1/status | jq
curl -s "localhost:8000/api/v1/datasets/eval-lab/judges-blind-760?level=summary" | jq '.entities[0]'
```

Interactive docs: <http://localhost:8000/api/docs>.

Nothing here is deployed anywhere. Phase 4 owns the gravebuster compose file and
the Cloudflare tunnel.

## Layout

```
live/
  src/eval_lab_live/
    config.py       settings (EVALLAB_LIVE_*), cache-header constants
    db.py           engine/session factories; the SQLite test path
    models.py       the two schemas' tables
    repository.py   read-only queries (no SQL outside this module)
    chartdata.py    rows -> research-chart-data v1 documents
    loader.py       backfill from the checkout; the paper-match guard
    sanitize.py     the leakage denylist
    api.py          the FastAPI app and routes
  migrations/       Alembic: 0001 initial schema, 0002 roles and grants
  docker/           Dockerfile, role bootstrap SQL
  docker-compose.yml
  tests/
  scripts/time_backfill.py   phase timing helper
```

## Data model

Two Postgres schemas, and that split is the point.

**`live`** — everything the API may serve: `projects`, `datasets`,
`experiments`, `judges`, `arms` (one per chart-data *entity*), `runs`,
`run_entities`, `metrics`, `dimensions`, `levels`, `observations`,
`aggregates`, `comparisons`, `artifacts`, `activities`, `snapshots`,
`ingest_log`. Nothing in this schema has a column for record text, a prompt, a
gold label or a per-record label — `live/tests/test_leakage.py` asserts that
over the metadata, so "there is nowhere to put a gold label" is checkable rather
than aspirational.

**`private`** — `predictions` (per-record judge output, for recompute and
audits) and `runner_tokens` (hashed ingest tokens, phase 3). The public API role
has **no grant at all** on this schema.

### Roles

| Role | Reach |
| --- | --- |
| `evallab_public_ro` | `USAGE` on `live`, `SELECT` on its tables. No `CREATE`. Nothing on `private`. |
| `evallab_ingest_rw` | DML on both schemas. No DDL. |
| owner (`evallab` in compose) | Owns the objects; runs migrations. |

The grants live in the Alembic revision `0002_roles`, not in the bootstrap
script, so a fresh database and an existing one end up identical. Roles are
created by `live/docker/bootstrap/10-roles.sh` (deployment) or by the test
fixture (CI), because `CREATE ROLE` needs a superuser.

`live/tests/test_migrations_pg.py` connects as `evallab_public_ro` and asserts
that `SELECT` on `private.predictions` is refused *by the server*. That is the
leakage backstop: a bug in a query cannot return per-record rows.

## The API

Everything is `GET`, cookieless, and under `/api/v1`. Chart endpoints return a
`research-chart-data` v1 document — the same shape the papers embed, validated
against `schemas/research-chart-data.v1.schema.json`.

| Route | Returns |
| --- | --- |
| `/api/v1/health` | Liveness only; touches no database, so it stays up during a blip. |
| `/api/v1/version` | Service version, API version, schema version, build commit, and the commit the dataset was exported from. |
| `/api/v1/status` | Run and dataset counts, last run time, the active min-slice threshold. Drives the frontend's offline banner; degrades to `{ok: false}` rather than 500. |
| `/api/v1/projects` | Projects. |
| `/api/v1/datasets` | Dataset summaries (record counts, levels, entity and observation counts). |
| `/api/v1/experiments` | Every `experiments/EXP-*` directory. |
| `/api/v1/judges` | The judge registry, keyed by model **and route**. |
| `/api/v1/metrics` | The measure registry. |
| `/api/v1/datasets/{id}` | The full chart-data v1 document. |
| `/api/v1/datasets/{id}/entities` | Just the entities. |
| `/api/v1/datasets/{id}/observations` | Just the tidy observations. |
| `/api/v1/datasets/{id}/levels` | The five levels. |
| `/api/v1/datasets/{id}/dimensions` | The dimensions. |
| `/api/v1/datasets/{id}/filters` | Facets: every filter value that exists, so the explorer never offers a dead end. |
| `/api/v1/leaderboard` | The document at one level, default `summary`. |
| `/api/v1/explore` | The document under arbitrary filters. |
| `/api/v1/runs`, `/api/v1/runs/{id}` | Every imported run, and one run with its artifacts and entities. |
| `/api/v1/runs/{id}/provenance.jsonld` | PROV-O JSON-LD: the activity, its software agent, its inputs and outputs. |
| `/api/v1/snapshots`, `/api/v1/snapshots/{id}` | Frozen views. Empty until phase 6; the endpoint and its immutable cache header exist now. |
| `/api/docs`, `/api/openapi.json` | Generated docs. |

### Filters and levels

`entity`, `experiment`, `deployment`, `model_family`, `metric`, `slice`,
`slice_value` and `headline` are repeatable query parameters on the document
routes, matched against columns and never interpolated. `level` selects one of
`summary`, `breakdown`, `experiments`, `runs`, `table`; an unknown level is a
400, and a filter that matches nothing is a 404 rather than an empty document.

Two caps protect the database: `max_entities` (200) and `max_observations`
(20 000). Exceeding either is a 400 telling the caller to narrow the query.

### Caching

Documents get `Cache-Control: public, max-age=0, stale-while-revalidate=300`
plus `CDN-Cache-Control: max-age=30` and a `Vercel-Cache-Tag`, so an ingest is
visible within seconds and the CDN can purge by tag. Snapshots get
`max-age=31536000, immutable`. `/health`, `/status` and `/version` are
`no-store`.

## The loader

`python -m eval_lab_live.loader` (or the compose `loader` service) imports the
repository into the database. It is idempotent: re-running updates rows in
place, and `--reset` empties everything first.

It imports two things:

* **Every run.** All 140 `experiments/EXP-*/**/results.json` files become `runs`
  rows, with their partition, per-arm summary, source-pool fingerprints, the
  SHA-256 of every artifact in `checksums.sha256`, and a `run_entities` link to
  the chart entity they feed. 55 of them predate `run_id` and are keyed by their
  repository path. Two more share a `run_id` with another committed run —
  `canary-cb_deepseek_v41_flash-20260922` appears in EXP-023 and EXP-024, and
  `grok_46-typed_schema` twice inside EXP-025, because a runner id is unique
  inside its experiment and not across the repository. Those are re-keyed by
  their run directory too, and the value the runner wrote is kept in
  `runs.source_run_id`, so no run is dropped and nothing is lost.
* **The frozen dataset.** `paper/data/judges-blind-760.json` is recomputed
  through the paper's own code path — `scripts/analyze_judge_comparison.py` and
  `scripts/export_chart_data.py` — and decomposed into `arms`, `observations`,
  `comparisons`, `metrics`, `dimensions` and `levels` rows.

A run id is therefore either the runner's own id or a repository path. The
`/runs/{id}` routes take the whole tail as one path parameter for that reason,
and `/runs` reports `sourceRunId` whenever the two differ.

### Why the API cannot disagree with the paper

`build_dataset_document()` recomputes the document and compares it with the
committed file **before writing anything**. Any difference on any key other than
`provenance` raises `LoadError` and the load aborts. A test
(`live/tests/test_api_matches_paper.py`) then asserts that
`GET /api/v1/datasets/eval-lab/judges-blind-760` equals the committed file, key
for key, and that the served bytes validate against the JSON Schema and the
SHACL provenance shapes.

`provenance` is the one deliberate exception. It records when the export ran,
from which commit, with the SHA-256 of each input at that moment — it is a
description of the frozen export, not a derivable number, and it is not
reproducible from a later checkout. The loader stores the committed block
verbatim and the API serves it unchanged, which is exactly what a paper reader
sees. Everything a chart plots is recomputed from the tables.

## Leakage controls

Four independent controls, all tested:

1. **The database.** Per-record rows are in `private`, which the API's role
   cannot read. Enforced by Postgres, asserted in `test_migrations_pg.py`.
2. **The read model.** No `live` column can hold a record or a label
   (`sanitize.suspicious_columns()` must be empty).
3. **The response shape.** The chart-data `observation` object has
   `additionalProperties: false`, so an extra column cannot ride along — the
   internal `slice_records` column is deliberately absent from it. Every public
   response is also walked against `sanitize.DENYLISTED_KEYS`
   (`gold`, `prompt`, `candidate*`, `answer_key`, `evidence`, `record_id`, …).
4. **The data.** `test_leakage.py` scans every public response body for all 322
   committed blind record ids. Those ids encode the answer class
   (`arc-single:Mercury_7221620:correct`), so leaking one leaks a gold label.

There is deliberately **no per-record endpoint** for any dataset, and no route
name mentions `record`, `gold`, `prediction` or `runner_token`.

### The min-slice rule

Slices whose population is below `EVALLAB_LIVE_MIN_SLICE_RECORDS` (default 20)
are dropped from responses, so filters cannot narrow a blind set down to
individual items. The population comes from an internal
`observations.slice_records` column — the per-observation `n` is a per-entity
resolved count and cannot be used for this. It is a property of the *cell*, not
the row, so an accuracy row and a coverage row for one slice are kept or dropped
together. `overall` slices are never suppressed: the headline numbers are the
point of the API.

The frozen `judges-blind-760` dataset **opts out** (`datasets.min_slice_records
= 0`). All 760 records and their gold labels are already in this public
repository — the architecture doc's Decision 2 records exactly that — so the
rule protects nothing here, while any move of the threshold would start hiding
slices the paper prints (its smallest, "Eval Lab synthetic (4 families)", is 20
records — right at the default). The API must keep agreeing with the paper, so
the opt-out is recorded on the dataset row rather than left to a default: a test
serves the document through an app configured with a threshold of 21 and asserts
the bytes are unchanged. Every other dataset keeps `NULL`, so the configured
threshold applies; phase 3's ingest sets it per dataset.

## Configuration

All settings are read from the environment with the `EVALLAB_LIVE_` prefix
(`eval_lab_live/config.py`); there are no secrets in this repository.

| Variable | Default | Purpose |
| --- | --- | --- |
| `EVALLAB_LIVE_DATABASE_URL` | the read-only role on `localhost:5432` | SQLAlchemy URL. The API must use `evallab_public_ro`. |
| `EVALLAB_LIVE_REPO_ROOT` | the checkout containing this file | Where the loader finds `experiments/` and `paper/data/`. |
| `EVALLAB_LIVE_DEFAULT_PROJECT` | `eval-lab` | Project served by default. |
| `EVALLAB_LIVE_DEFAULT_PROJECT_DATASET` | `eval-lab/judges-blind-760` | Dataset served when a request omits `?dataset=`. |
| `EVALLAB_LIVE_MIN_SLICE_RECORDS` | `20` | Suppression threshold. |
| `EVALLAB_LIVE_MAX_ENTITIES` | `200` | Per-request entity cap. |
| `EVALLAB_LIVE_MAX_OBSERVATIONS` | `20000` | Per-request observation cap. |
| `EVALLAB_LIVE_BUILD_COMMIT` | `unknown` | Reported by `/version` and `/status`. |

## Tests

```bash
uv sync --locked --extra dev --extra live
uv run --locked python -m pytest live/tests -q
```

* `test_api_matches_paper.py` — the paper-match proof, plus schema and SHACL
  validation of the served document.
* `test_api_contract.py` — every route, filter, level and cache header.
* `test_leakage.py` — the four controls above.
* `test_loader.py` — completeness, idempotency, and that a tampered dataset file
  aborts the load.
* `test_migrations_pg.py` — Alembic up/down and role separation. **Skipped**
  without a Postgres:

  ```bash
  EVALLAB_LIVE_TEST_DATABASE_URL=postgresql+psycopg://evallab:evallab@localhost:55432/evallab \
      uv run --locked python -m pytest live/tests/test_migrations_pg.py -q
  ```

Everything except the Postgres module runs on SQLite. The SQLite engine attaches
two in-memory databases named `live` and `private` (`db.create_db_engine`), so
the models keep their real schema names on both backends and no query needs a
dialect branch.

The suite is session-scoped: it backfills a throwaway database once. Locally, if
`git status` in your checkout is slow, that backfill dominates the runtime —
`live/scripts/time_backfill.py` prints where the time goes.

CI runs this in the `live` job of `.github/workflows/ci.yml`, against a
`postgres:17` service container, in parallel with the unchanged research job.

## Phase 2 in one line

The database is a rebuildable projection of git: `alembic upgrade head` plus
`python -m eval_lab_live.loader` reproduces, from the committed artifacts, a
database whose API output is the paper's own document.
