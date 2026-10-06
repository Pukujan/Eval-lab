# TASK-0071 — Classifier viewer API contract and dynamic-update path

## Status

Active — tracked by GitHub issue #99. Planning in progress; no implementation
merged yet. Follows TASK-0070 (issue #95, merged), which shipped the static
viewer.

## Objective

Give the EXP-032 classifier viewer a real, versioned read API contract and a
polling path that makes dynamic data updating provable, without contradicting
the repository's existing live-app policy. Today the viewer fetches committed
JSON once and never updates, so the "api contracts for dynamic data updating"
half of the originating request is undelivered.

## Scope

- A stdlib-only, read-only HTTP server (`scripts/serve_classifier_viewer.py`)
  serving a versioned `viewer-api.v1` contract.
- Machine-readable schemas under `schemas/viewer-api/`; a human contract in
  `docs/VIEWER_API.md`.
- A derived `revision` (content hash over served artifacts) and a cheap
  revision endpoint the viewer polls.
- A frontend data-source abstraction so the static snapshot and the API share
  one parsing path, plus revision-driven refetching.
- Tests that make the dynamic-update claim falsifiable, including a live-server
  contract test and a browser test asserting the UI updates without a reload.

## Gold and safety rules

- The API is read-only and aggregate-only. It must not serve per-record rows
  for the `blind_holdout` partition, per `docs/architecture/live-app.md` §11
  ("No per-record endpoint exists for blind partitions") and §15 ("No per-record
  blind drilldown, ever"). Confirmed with the user on 2026-10-06.
- No new Python dependency; the server uses the standard library only.
- No `node_modules` in the checkout; the frontend source stays outside it.
- No credentials, tokens, or secrets are committed or printed.
- No completed experiment artifact is modified; EXP-026 stays untouched.

## Acceptance

1. A versioned read API is documented and implemented; every response carries
   an `apiVersion` field and the server sends an API-version header.
2. The API is read-only and aggregate-only: no per-record rows for the
   `blind_holdout` partition are served.
3. `revision` is derived from artifact content: unchanged artifacts produce an
   identical revision, and a changed artifact produces a different one.
4. The viewer polls the revision endpoint and reflects a new eval run without a
   page reload, demonstrated by an automated browser test.
5. The committed static snapshot equals the API response for the same revision.
6. No new Python dependency; no `node_modules` in the checkout; existing CI
   gates stay green (`check_repo_contract.py`, `check_workspace_policy.py`,
   `ruff`, `mypy`, `pytest`, `export_chart_data.py --check`,
   `run_telemetry.py --check`).

## Files in scope

- `tasks/TASK-0071-viewer-api-contract.md`
- `checkpoints/CURRENT.md`
- `src/eval_lab/viewer_api.py` (new: pure contract logic, mypy-checked)
- `scripts/serve_classifier_viewer.py` (new: stdlib HTTP surface)
- `schemas/viewer-api/` (new: `revision.v1.schema.json`,
  `experiment-summary.v1.schema.json`)
- `docs/VIEWER_API.md` (new)
- `tests/test_viewer_api.py` (new)
- `tests/test_viewer_polling_e2e.py` (new)
- `site/gleif-classifier/` (rebuilt static assets only)

## Goal

Answer the practical question the viewer currently cannot: is the published
classifier result live, and does it tell the reader when it has gone stale?

## Acceptance criteria

The Objective, Scope, Gold and safety rules, and Acceptance sections above are
the acceptance criteria for this task.

## Checkpoint log

### 2026-10-06 — issue filed; planning

Status: issue #99 filed; task file written; branch created. The plan is being
produced by the planner sub-agent. No implementation merged.

Read-only findings that shaped the plan:

- `docs/architecture/live-app.md` (TASK-0060, issue #71) already designs a
  read-only `/api/v1` whose chart endpoints return `research-chart-data.v1`
  documents, and states the no-per-record-blind rule. This task conforms to
  that design rather than inventing a parallel one; it does not implement the
  `live/` backend, Postgres, ingest, or Cloudflare work, which remains
  plan-only and blocked on that doc's own decisions.
- The static bundle under `site/gleif-classifier/` is the sanctioned deployment
  for paper figures ("`export_chart_data.py` from git is the canonical route
  for paper figures"), so the API is additive, not a replacement.

Next atomic action: receive the final plan, then implement the server, schemas,
and doc; refactor the viewer data builder; then the frontend data-source
abstraction and polling.

### 2026-10-06 — implemented; dynamic update demonstrated in a browser

Status: all six acceptance criteria met. Not yet published.

The API is a **subset of `docs/architecture/live-app.md` that runs today against
committed artifacts**. It is read-only, aggregate-only, and conforms to that
document's no-per-record-blind rule rather than inventing a parallel design. It
does not implement the `live/` backend, Postgres, ingest, or the Cloudflare
Tunnel; those remain plan-only.

Completed work:

- **Pure logic** in `src/eval_lab/viewer_api.py` (mypy-checked, under
  `files = ["src/eval_lab"]`), mirroring the TASK-0062 `telemetry.py` split.
  `revision` is SHA-256 over the literal `"viewer-api.v1"` plus, for each path in
  sorted order, the path and the SHA-256 of its LF-normalized bytes. The file set
  is the union of the API face (`paper/data/gleif-classifier.json` + the six
  `paper/data/classifier-charts/*.json`) and the static-only face
  (`site/gleif-classifier/data/items.json`, the table's source). `inputsRevision`
  hashes the upstream EXP-032 artifacts and never drives UI invalidation.
- **HTTP surface** in `scripts/serve_classifier_viewer.py`: stdlib
  `ThreadingHTTPServer` only, no new dependency. GET/HEAD; `405` with `Allow` for
  writes; `X-Viewer-Api-Version: viewer-api.v1` on **every** response including
  errors and static files; `no-store` on `/api/v1/revision`; strong ETag +
  `If-None-Match`→`304` on the experiment summary and the served documents;
  static bundle rooted at `site/gleif-classifier/` with `resolve()` +
  `is_relative_to` traversal defense; `--root`/`--host`/`--port` and a repeatable
  `--allow-origin` that echoes the origin with `Vary: Origin`.
- **Aggregate-only, structurally.** There is no per-record API route and no
  wildcard under `/api/v1` that can reach one; `/api/v1/records…` returns an
  explicit `403`. The viewer's 2142-row table keeps loading the committed static
  `items.json`, which TASK-0070 acceptance criterion 5 already made public.
- **Schemas** under `schemas/viewer-api/` (draft 2020-12, `additionalProperties:
  false`, 64-hex revision patterns), validated against the live payloads.
- **`docs/VIEWER_API.md`**: the contract table, the revision derivation, the
  aggregate-only exposure paragraph, and the §8 cache conventions adapted for a
  non-CDN same-origin server (why `immutable` would be wrong here: these export
  paths are overwritten in place, unlike a frozen snapshot row).
- **Frontend** (outside the repo, at `C:\work\eval-lab-scratch\classifier-viewer-app`):
  a new `src/lib/dataLayer.ts` holding one `fetchJson` and the URL builders both
  modes share; `useViewerDataSource()` probes `/api/v1/revision`, polls at 30 s
  backing off to a 5 min cap, and on a revision change invalidates every query;
  items are refetched as `data/items.json?v=<revision>`; a `revision-chip` shows
  `live` + the first 8 hex characters, or `static snapshot` when no API answers.
  Rebuilt and copied **only** `index.html`, `assets/`, and `favicon.ico` into
  `site/gleif-classifier/`; the committed `data/` files were byte-identical
  under LF normalization and were left untouched. No `node_modules`,
  `package.json`, or lockfile entered the checkout.

Files changed: `src/eval_lab/viewer_api.py` (new),
`scripts/serve_classifier_viewer.py` (new), `schemas/viewer-api/*.json` (new),
`docs/VIEWER_API.md` (new), `tests/test_viewer_api.py` (new),
`tests/test_viewer_polling_e2e.py` (new),
`site/gleif-classifier/{index.html,assets/*,favicon.ico}` (rebuilt),
`tasks/TASK-0071-*.md`, `checkpoints/CURRENT.md`.

Commands run: `ruff check`, `ruff format --check`, `mypy src/eval_lab`,
`pytest tests -q`, `check_repo_contract.py`, `check_workspace_policy.py
--canonical-root D:/development/eval-lab`, `export_chart_data.py --check`,
`run_telemetry.py --check`, `npx tsc --noEmit -p tsconfig.app.json`,
`npx vite build`, `node eval/out/poll-viewer.mjs`.

Test results: **273 passed** (was 241; +30 in `test_viewer_api.py`, +2 in
`test_viewer_polling_e2e.py`). Repository contract OK. Workspace policy OK.
Export chart data `--check` exit 0. Run telemetry current (159 records).
Browser verification of the built bundle: 0 console/page errors, 6 recharts
charts, 6 summary tiles, 50 table rows, 80 SVGs, both viewports.

Decisions made:

- **Aggregate-only, per the user's locked choice.** `docs/architecture/live-app.md`
  §11/§15 forbid a per-record endpoint for a blind partition and EXP-032's is
  `blind_holdout`, so the API serves metadata, the six aggregate chart documents,
  and the revision — nothing per-record. This adds no new exposure: the static
  `items.json` is already public and is the TASK-0070 deliverable.
- **`no-cache` + content-addressed ETag instead of `immutable`.** §8 marks
  snapshot URLs `immutable` because they name a frozen row; here the export paths
  are overwritten in place when a new run lands, so `immutable` would pin a stale
  body. Revalidation is a cheap `304`.
- **The revision covers both faces.** Hashing only the API face would let a
  regenerated export with a stale site copy report a stable revision.
- **The browser E2E skips in CI.** The driver (Playwright 1.63) is vendored in
  the external `app-builder-automation` workspace, not a dependency of this
  repository. The deterministic proof of the same mechanism that CI *does* run is
  `test_revision_endpoint_reports_a_change_after_a_served_byte_moves`; the
  browser test is the local demonstration acceptance criterion 4 asks for.

Unresolved questions: none.

Next atomic action: publish this checkpoint for issue #99 via
`publish_checkpoint.py`, then finalize (confirm the merge, audit state,
fast-forward the canonical checkout).

## Handoff

The viewer's frontend source is not in this repository — only built assets are
committed. It lives at `C:\work\eval-lab-scratch\classifier-viewer-app\` (Vite
+ React + TS, recharts, `@tanstack/react-query`), with `node_modules`
symlinked into the external `app-builder-automation` template. Rebuilding means
running the build there and copying `dist/` into `site/gleif-classifier/`;
never commit the app source or `node_modules` here.

Do not serve per-record blind rows from the API. Do not add a Python
dependency for the server.
