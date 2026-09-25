# TASK-0060: live Eval Lab app — phase 2 (backend, migrations, loader, read API)

## Status

Phase 2 implemented on branch `task/TASK-0060-live-app-backend`. Tracked by
GitHub issue #71, which stays open: phases 3 to 7 remain.

## Goal

Build the read-only backend behind the Eval Lab explorer: a FastAPI service
over a Postgres 17 database holding every committed experiment run and the
paper's frozen chart dataset, rebuilt from git. Phase 2 is the models, the
migrations, the backfill loader and the public read API — no ingest, no
deploy, no frontend.

## Scope

New `live/` folder, following `docs/architecture/live-app.md`:

- `live/src/eval_lab_live/` — `config`, `db`, `models`, `repository`,
  `chartdata`, `loader`, `sanitize`, `api`.
- `live/migrations/` — Alembic `0001_initial` (both schemas) and `0002_roles`
  (grants).
- `live/docker/` and `live/docker-compose.yml` — local Postgres 17 plus the
  API; deploying anywhere is out of scope.
- `live/tests/` — SQLite for everything except the Postgres role module.
- `.github/workflows/ci.yml` — a `live` job, in parallel with the research job.
- `pyproject.toml` / `uv.lock` — a `live` optional dependency group, so the
  core research install is unchanged.

Out of scope: ingest (phase 3), the gravebuster deploy (phase 4), the
design-bakery `/eval-lab` route (phase 5), snapshot freeze/pull (phase 6),
hardening (phase 7).

## Acceptance criteria

- The API serves `research-chart-data` v1 documents, validated against
  `schemas/research-chart-data.v1.schema.json` in tests.
- `live/tests/test_api_matches_paper.py` proves the served
  `eval-lab/judges-blind-760` document equals `paper/data/judges-blind-760.json`
  key for key (except `provenance`, which is stored and served verbatim).
- The public read role `evallab_public_ro` has no access to any per-record
  table, asserted by the server in `live/tests/test_migrations_pg.py`.
- No blind record id or gold label appears in any public response.
- `docker compose up` applies migrations, backfills and serves the API.
- The `live` CI job passes without slowing down or breaking the research job.
- `live/README.md` documents the stack, the data model, the roles, the routes
  and the leakage controls.

## Files changed

New: `live/**` (see Scope), plus `live/scripts/time_backfill.py`.

Modified: `.github/workflows/ci.yml` (added the `live` job), `pyproject.toml`
(optional `live` extra, package discovery), `uv.lock`.

## Checkpoint log

### 2026-09-24: phase 2 backend

Status: implemented, lint/type clean, pushed.

Decisions:

- **Two schemas, three roles.** `live` holds everything the API may serve;
  `private` holds `predictions` and `runner_tokens`. The grants live in the
  Alembic revision `0002_roles`, not the bootstrap script, so a fresh database
  and an existing one end up identical.
- **SQLite test path.** The engine ATTACHes two in-memory databases named
  `live` and `private`, so the models keep their real schema names on both
  backends and no query needs a dialect branch. Only the role module needs a
  real Postgres.
- **Paper match.** `build_dataset_document()` recomputes the document through
  the paper's own code path (`scripts/analyze_judge_comparison.py`,
  `scripts/export_chart_data.py`) and compares it with the committed file
  before writing anything; any difference outside `provenance` aborts the
  load. `provenance` pins commit/dirty/generatedAt and input sha256s, so it is
  stored and served verbatim.
- **Min-slice opt-out.** The architecture's `n < 20` suppression rule would
  drop slices of 8 and 12 records that the papers publish. Added a nullable
  `datasets.min_slice_records`; the frozen dataset sets it to 0, everything
  else keeps the configured threshold. Slice population comes from an internal
  `observations.slice_records` column that is never serialized.
- **Optional dependency group.** `live` is a `[project.optional-dependencies]`
  extra, so `uv sync --extra dev` installs exactly what it did before.

Commands run:

```bash
uv run --locked ruff check live
uv run --locked ruff format --check live
uv run --locked mypy live/src/eval_lab_live
uv run --locked python -m pytest live/tests -q
uv run --locked python -m pytest tests -q
```

Test results: recorded in the checkpoint commit for this task.

Unresolved: the local checkout's `git status --untracked-files=all` takes ~26 s
per call (large untracked tree), and the loader calls it several times, so the
first local `pytest live/tests` run is slow. This is a local-environment cost,
not a code path; CI's checkout is fast. `live/scripts/time_backfill.py` prints
where the time goes.

## Handoff

Phase 3 (ingest) can build on `private.predictions`, `private.runner_tokens`
and `live.ingest_log`, which exist and are granted but unused. Phase 6 owns
`live.snapshots`, which is served but empty. The design-bakery route is tracked
in design-bakery#50.

## Next atomic action

Post the phase 2 summary on #71 and leave it open for phase 3.
