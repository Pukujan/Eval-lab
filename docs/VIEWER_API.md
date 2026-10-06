# Viewer API (`viewer-api.v1`)

TASK-0071 (issue #99). The read-only contract the EXP-032 classifier viewer
polls, and the reference for anything that reimplements it.

- **Implementation.** Pure logic: `src/eval_lab/viewer_api.py`. HTTP surface:
  `scripts/serve_classifier_viewer.py` (standard library only, no new
  dependency). Schemas: `schemas/viewer-api/*.schema.json`. Tests:
  `tests/test_viewer_api.py`.
- **Relationship to `docs/architecture/live-app.md` (TASK-0060).** That document
  designs the eventual `live/` stack — FastAPI, Postgres, ingest, Cloudflare
  Tunnel, the `/eval-lab` SPA route. This API is a **subset of that design that
  runs today against committed artifacts**, and it conforms to the same rules:
  read-only, aggregate-only, no per-record endpoint for a blind partition. It
  does **not** implement the `live/` backend, the database, ingest, or the
  tunnel; those remain plan-only and blocked on that document's own decisions.
- **Scope.** One experiment. Every route and the revision derivation are hard-wired
  to EXP-032's artifacts. Serving a second experiment means generalising the
  route table and the file set, not adding a row to a config file.

## 1. Why it exists

The viewer under `site/gleif-classifier/` is a static bundle. It fetches
committed JSON once and never updates, so it goes stale silently: a new eval run
lands, the committed snapshot keeps showing the old numbers, and nothing in the
UI says so. This API answers the question the viewer could not — *is the
published result live, and has it gone stale?* — by exposing a small derived
revision an open page can poll.

The static bundle is the sanctioned deployment for paper figures
(`export_chart_data.py` from git is the canonical route). The API is additive,
not a replacement: the same bytes are served from the same commit.

## 2. Contract

Every response — including errors, `304`s, and static files — carries
`X-Viewer-Api-Version: viewer-api.v1`. Every JSON body carries
`apiVersion: "viewer-api.v1"`.

| Method | Path | Body | `Cache-Control` | `ETag` |
|---|---|---|---|---|
| GET/HEAD | `/api/v1/revision` | revision payload | `no-store` | no |
| GET/HEAD | `/api/v1/experiments/EXP-20261005-032` | experiment summary | `no-cache` | strong |
| GET/HEAD | `/api/v1/dataset` | `paper/data/gleif-classifier.json`, verbatim | `no-cache` | strong |
| GET/HEAD | `/api/v1/charts/{id}` | `paper/data/classifier-charts/{id}.json`, verbatim | `no-cache` | strong |
| GET | `/api/v1/records…` | `403`, aggregate-only refusal | `no-store` | no |
| GET | any other `/api/v1/**` | `404` JSON error | `no-store` | no |
| GET/HEAD | `/**` | static bundle from `site/gleif-classifier/`, including `data/items.json` | `no-cache` | strong |
| OPTIONS | any | `204` CORS preflight | `no-store` | no |
| POST/PUT/PATCH/DELETE | any | `405`, `Allow: GET, HEAD, OPTIONS` | `no-store` | no |

The six chart ids: `classifier_class_distribution`,
`classifier_confidence_histogram`, `classifier_coverage_at_target_error`,
`classifier_family_scores`, `classifier_reliability`,
`classifier_risk_coverage`. The route id is the short experiment form
(`EXP-20261005-032`), not the full directory name.

### Revision payload

```json
{
  "apiVersion": "viewer-api.v1",
  "revision": "<64-hex>",
  "inputsRevision": "<64-hex>",
  "experimentId": "EXP-20261005-032-gleif-classifier",
  "datasetId": "eval-lab/gleif-classifier",
  "partition": "blind_holdout",
  "recordCount": 2142,
  "resolvedCount": 2142,
  "families": ["entity-category", "legal-jurisdiction", "registration-status"]
}
```

Schema: `schemas/viewer-api/revision.v1.schema.json`. The response is constant
in size and carries no chart rows and no per-record rows, so a 30 s poll is
cheap.

## 3. Revision derivation

`revision` is a **derived** hash, never a declared number or timestamp. It is
SHA-256 over:

1. the literal contract string `"viewer-api.v1"`, then
2. for each path in sorted order: the path, a `\0` separator, the SHA-256 of
   the file's **LF-normalized** bytes, and a newline.

The files are the union of both faces of the viewer:

- **the API face** — `paper/data/gleif-classifier.json` and the six
  `paper/data/classifier-charts/*.json` documents, and
- **the static-only face** — `site/gleif-classifier/data/items.json`, the file
  the viewer's 2142-row table loads.

Four consequences, each deliberate:

- **"The revision changed" implies "the viewer's data changed" and nothing
  else.** Hashing the *upstream* experiment artifacts instead would flip the
  revision while every served byte stayed identical.
- **Both faces are covered.** The API serves the `paper/data` exports; the
  viewer's table reads the static `items.json`. Hashing the union means a
  regenerated export with a stale site copy cannot report a stable revision.
- **Deterministic across checkouts.** Paths are sorted and bytes are
  LF-normalized, so a Windows CRLF checkout hashes identically to a Linux one.
  No timestamp is generated.
- **The contract version is part of it.** A schema-breaking change cannot
  produce the same revision as the document it replaced.

`inputsRevision` is the same construction over the upstream EXP-032 artifacts
(`records.jsonl`, `typed-question-spec.json`, `results.json`, and the three
`runs/<family>/predictions.jsonl`). It is **pipeline visibility only**: a new
run landing must not flip the UI's revision until the served bytes actually
change, so nothing in the viewer is keyed on it.

## 4. Aggregate-only exposure

The API serves **no per-record rows**. `docs/architecture/live-app.md` §11
states "No per-record endpoint exists for blind partitions" and §15 states "No
per-record blind drilldown, ever"; EXP-032's partition is `blind_holdout`, so
that rule governs here. There is no per-record API route and no wildcard under
`/api/v1` that could reach a per-record document. The refusal is explicit — a
path under `/api/v1/records…` returns `403` with a legible message rather than a
generic `404` — and `tests/test_viewer_api.py` asserts that no API response body
contains any of the 2142 blind record ids or a `"gold"` key.

**No new exposure.** The viewer's table keeps loading
`site/gleif-classifier/data/items.json` from the static bundle, exactly as it
does today. That file is already public in this repository: it is the TASK-0070
deliverable acceptance criterion 5 requires (all ≥1000 records viewable), and
`docs/architecture/live-app.md` already records, as a blocking finding, that the
blind holdout with gold labels is committed in the public repo. This server
serves the bundle it is pointed at and adds no per-record path of its own.

## 5. Caching

`docs/architecture/live-app.md` §8 sets the cache convention for the eventual
CDN-fronted deployment. This server is a plain same-origin origin with no CDN,
so it emits `CDN-Cache-Control` with the same value as `Cache-Control` for
forward-compatibility with that design, and adapts the §8 values as follows:

| §8 value | Here | Why |
|---|---|---|
| `no-store` for `/status` | `/api/v1/revision` → `no-store` | The revision endpoint is the `/status` analogue and is the poll target. Any caching hands a poller a stale revision, which defeats the whole mechanism. |
| `immutable` for snapshots | committed documents → `no-cache` + strong `ETag` | In §8 a snapshot URL is immutable because it names a frozen row. Here the export paths are **overwritten in place** when a new run lands, so `immutable` would pin a stale body for a year. The `ETag` is content-addressed (SHA-256 of the LF-normalized bytes), so revalidation is a cheap `304` when nothing changed. |
| `max-age=30` + `stale-while-revalidate=300` for live endpoints | not used | Those values exist to keep a CDN fast while a live backend is behind it. With no CDN in front, `no-cache` + `ETag` gives the same correctness with one conditional request. |

The browser talks to one origin, so the default is **no CORS headers** and no
cookies. `--allow-origin` may be repeated to permit specific dev origins; the
origin is then echoed with `Vary: Origin`, and an unpermitted origin gets no
`Access-Control-Allow-Origin` and is refused by the browser.

## 6. Client behaviour

The viewer polls `/api/v1/revision`, starting at 30 s and backing off to a 5 min
cap, resetting on success. When the revision differs from the one it last
rendered it invalidates its queries and refetches, appending `?v=<revision>` to
the static `items.json` request so the browser cache cannot serve a stale
snapshot under a new revision. A header chip shows the first 8 hex characters.
The end-to-end test in `tests/test_viewer_polling_e2e.py` asserts that the UI
updates without a page reload.

## 7. Running it

```powershell
uv run --locked python scripts/serve_classifier_viewer.py --port 8123
uv run --locked python scripts/serve_classifier_viewer.py --allow-origin http://localhost:5173
```

`--root` points at a different checkout (default: this one), `--host` and
`--port` set the bind address, and `--allow-origin` is repeatable. The server is
read-only: it opens no write path and needs no credentials.
