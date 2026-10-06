"""TASK-0071: the EXP-032 classifier viewer's read API contract.

These run in CI through `pytest tests` and make the dynamic-update claim
falsifiable. Four pillars:

- **Derived revision.** The revision hashes the bytes the viewer shows, so an
  unchanged artifact cannot move it and a changed artifact cannot keep it. The
  upstream inputs hash separately and never drive UI invalidation.
- **Live-server contract.** A real ``ThreadingHTTPServer`` on an ephemeral port
  answers the documented routes, headers, cache directives and status codes.
- **Static/API parity.** Every aggregate body the API serves is byte-equal to
  the committed static file the viewer also loads.
- **Aggregate-only.** No route serves per-record blind rows, and no response
  body carries a blind record ID.

The end-to-end polling test lives in `tests/test_viewer_polling_e2e.py` and
skips where a browser driver is not installed.
"""

from __future__ import annotations

import json
import shutil
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import jsonschema
import pytest

from eval_lab import viewer_api
from eval_lab.viewer_api import (
    API_VERSION,
    CHART_IDS,
    EXPERIMENT_DIR,
    INPUT_FILES,
    ITEMS_DOC,
    PARTITION,
    REVISION_FILES,
    ViewerState,
    build_experiment_summary,
    build_revision_payload,
    compute_inputs_revision,
    compute_revision,
    read_served_document,
    sha256_file,
)
from scripts.serve_classifier_viewer import SITE_DIR, build_server

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "viewer-api"
REVISION_SCHEMA = SCHEMA_DIR / "revision.v1.schema.json"
SUMMARY_SCHEMA = SCHEMA_DIR / "experiment-summary.v1.schema.json"
BLIND_RECORDS = ROOT / EXPERIMENT_DIR / "records.jsonl"

ALL_FILES = tuple(sorted(set(REVISION_FILES) | set(INPUT_FILES)))


def _load(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _mirror(destination: Path) -> Path:
    """A writable copy of just the files the API reads, for mutation tests."""
    for relative in ALL_FILES:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return destination


def _blind_record_ids() -> set[str]:
    ids: set[str] = set()
    for line in BLIND_RECORDS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["partition"] == PARTITION:
            ids.add(row["record"]["record_id"])
    return ids


# --- revision derivation ----------------------------------------------------


def test_revision_is_deterministic_and_full_width() -> None:
    first = compute_revision(ROOT)
    assert first == compute_revision(ROOT)
    assert len(first) == 64 and set(first) <= set("0123456789abcdef")


def test_crlf_checkout_hashes_like_an_lf_checkout(tmp_path: Path) -> None:
    (tmp_path / "lf.txt").write_bytes(b"a\nb\n")
    (tmp_path / "crlf.txt").write_bytes(b"a\r\nb\r\n")
    assert sha256_file(tmp_path / "lf.txt") == sha256_file(tmp_path / "crlf.txt")


def test_identical_bytes_keep_the_revision(tmp_path: Path) -> None:
    root = _mirror(tmp_path)
    before = compute_revision(root)
    _mirror(tmp_path)
    assert compute_revision(root) == before


def test_one_changed_served_byte_moves_the_revision(tmp_path: Path) -> None:
    root = _mirror(tmp_path)
    before = compute_revision(root)
    items = root / ITEMS_DOC
    items.write_bytes(items.read_bytes().replace(b'"recordCount":2142', b'"recordCount":2143'))
    assert compute_revision(root) != before


def test_revision_covers_the_static_only_face(tmp_path: Path) -> None:
    """The table's static items.json is part of the revision, not a bystander.

    A regenerated export that leaves a stale site copy behind must not report a
    stable revision.
    """
    root = _mirror(tmp_path)
    before = compute_revision(root)
    items = root / ITEMS_DOC
    items.write_bytes(items.read_bytes() + b"\n")
    assert compute_revision(root) != before


def test_revision_covers_every_served_document(tmp_path: Path) -> None:
    root = _mirror(tmp_path)
    for relative in REVISION_FILES:
        baseline = compute_revision(root)
        path = root / relative
        path.write_bytes(path.read_bytes() + b"\n")
        assert compute_revision(root) != baseline, relative
        path.write_bytes(path.read_bytes()[:-1])
        assert compute_revision(root) == baseline, relative


def test_inputs_revision_moves_without_moving_the_ui_revision(tmp_path: Path) -> None:
    """A new eval run must not flip the UI until the served bytes change."""
    root = _mirror(tmp_path)
    revision_before = compute_revision(root)
    inputs_before = compute_inputs_revision(root)
    predictions = root / f"{EXPERIMENT_DIR}/runs/entity-category/predictions.jsonl"
    predictions.write_bytes(predictions.read_bytes() + b"\n")
    assert compute_inputs_revision(root) != inputs_before
    assert compute_revision(root) == revision_before


def test_revision_depends_on_the_contract_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _mirror(tmp_path)
    before = compute_revision(root)
    monkeypatch.setattr(viewer_api, "API_VERSION", "viewer-api.v2")
    assert compute_revision(root) != before


def test_read_served_document_refuses_anything_not_served() -> None:
    assert read_served_document(ROOT, ITEMS_DOC) == (ROOT / ITEMS_DOC).read_bytes()
    for relative in ("experiments/EXP-20261005-032-gleif-classifier/results.json", "../PROJECT.md"):
        with pytest.raises(KeyError):
            read_served_document(ROOT, relative)


def test_viewer_state_memoizes_and_notices_a_change(tmp_path: Path) -> None:
    root = _mirror(tmp_path)
    state = ViewerState(root)
    first = state.revision_payload()
    assert state.revision_payload() is first
    items = root / ITEMS_DOC
    items.write_bytes(items.read_bytes() + b"\n")
    second = state.revision_payload()
    assert second is not first
    assert second["revision"] != first["revision"]


# --- payload shape ----------------------------------------------------------


def test_live_payloads_satisfy_their_schemas() -> None:
    for schema_path, payload in (
        (REVISION_SCHEMA, build_revision_payload(ROOT)),
        (SUMMARY_SCHEMA, build_experiment_summary(ROOT)),
    ):
        schema = _load(schema_path)
        jsonschema.Draft202012Validator.check_schema(schema)
        errors = [e.message for e in jsonschema.Draft202012Validator(schema).iter_errors(payload)]
        assert errors == [], f"{schema_path.name}: {errors[:3]}"


def test_schemas_reject_a_wrong_version_and_a_short_revision() -> None:
    validator = jsonschema.Draft202012Validator(_load(REVISION_SCHEMA))
    payload = build_revision_payload(ROOT)
    assert not list(validator.iter_errors(payload))
    assert list(validator.iter_errors({**payload, "apiVersion": "viewer-api.v2"}))
    assert list(validator.iter_errors({**payload, "revision": payload["revision"][:8]}))
    assert list(validator.iter_errors({**payload, "recordCount": -1}))
    assert list(validator.iter_errors({**payload, "extra": 1}))


def test_revision_payload_is_aggregate_only() -> None:
    payload = build_revision_payload(ROOT)
    assert payload["partition"] == PARTITION
    assert payload["recordCount"] == payload["resolvedCount"] == 2142
    assert set(payload) == {
        "apiVersion",
        "revision",
        "inputsRevision",
        "experimentId",
        "datasetId",
        "partition",
        "recordCount",
        "resolvedCount",
        "families",
    }


def test_chart_ids_are_the_six_committed_charts() -> None:
    assert CHART_IDS == (
        "classifier_class_distribution",
        "classifier_confidence_histogram",
        "classifier_coverage_at_target_error",
        "classifier_family_scores",
        "classifier_reliability",
        "classifier_risk_coverage",
    )
    for chart_id in CHART_IDS:
        assert (ROOT / f"paper/data/classifier-charts/{chart_id}.json").is_file()


def test_the_served_file_set_pins_the_committed_directories() -> None:
    """Guard the one silent-staleness hole: a chart the revision does not cover.

    ``CHART_IDS`` is a frozen tuple, so a renamed or newly exported chart would
    be served by nobody and hashed by nobody, and the revision would not move.
    Pinning the tuple to the directory turns that into a loud CI failure.
    """
    on_disk = sorted(path.stem for path in (ROOT / "paper/data/classifier-charts").glob("*.json"))
    assert sorted(CHART_IDS) == on_disk
    assert (ROOT / "paper/data/gleif-classifier.json").is_file()
    site_charts = sorted(path.stem for path in (ROOT / SITE_DIR / "data/charts").glob("*.json"))
    assert site_charts == on_disk


# --- live server ------------------------------------------------------------


@pytest.fixture(scope="module")
def base_url() -> Iterator[str]:
    server = build_server(root=ROOT, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)


@pytest.fixture(scope="module")
def client(base_url: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=base_url, timeout=10) as http:
        yield http


def test_every_response_carries_the_api_version(client: httpx.Client) -> None:
    for path in (
        "/",
        "/api/v1/revision",
        "/api/v1/experiments/EXP-20261005-032",
        "/api/v1/dataset",
        "/api/v1/charts/classifier_reliability",
        "/api/v1/nope",
        "/data/items.json",
    ):
        response = client.get(path)
        assert response.headers.get("X-Viewer-Api-Version") == API_VERSION, path
    assert client.post("/api/v1/revision").headers.get("X-Viewer-Api-Version") == API_VERSION
    assert (
        client.request("OPTIONS", "/api/v1/revision").headers.get("X-Viewer-Api-Version")
        == API_VERSION
    )


def test_revision_endpoint_is_small_uncached_and_has_no_etag(client: httpx.Client) -> None:
    response = client.get("/api/v1/revision")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert "ETag" not in response.headers
    assert response.json() == build_revision_payload(ROOT)
    assert len(response.content) < 2048


def test_revision_endpoint_reports_a_change_after_a_served_byte_moves(
    tmp_path: Path,
) -> None:
    """The whole point of the endpoint: a poll notices a new served artifact."""
    root = _mirror(tmp_path)
    server = build_server(root=root, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        with httpx.Client(base_url=f"http://{host}:{port}", timeout=10) as http:
            before = http.get("/api/v1/revision").json()["revision"]
            items = root / ITEMS_DOC
            items.write_bytes(items.read_bytes() + b"\n")
            after = http.get("/api/v1/revision").json()["revision"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)
    assert before != after


def test_experiment_summary_revalidates_with_an_etag(client: httpx.Client) -> None:
    response = client.get("/api/v1/experiments/EXP-20261005-032")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-cache"
    etag = response.headers["ETag"]
    assert response.json() == build_experiment_summary(ROOT)
    again = client.get("/api/v1/experiments/EXP-20261005-032", headers={"If-None-Match": etag})
    assert again.status_code == 304
    assert again.content == b""


def test_unknown_experiment_is_a_404(client: httpx.Client) -> None:
    response = client.get("/api/v1/experiments/EXP-19990101-001-nope")
    assert response.status_code == 404
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json()["error"]


def test_dataset_and_charts_serve_committed_bytes_verbatim(client: httpx.Client) -> None:
    documents = {"dataset": "paper/data/gleif-classifier.json"}
    documents.update(
        {
            f"charts/{chart_id}": f"paper/data/classifier-charts/{chart_id}.json"
            for chart_id in CHART_IDS
        }
    )
    for route, relative in documents.items():
        response = client.get(f"/api/v1/{route}")
        assert response.status_code == 200, route
        assert response.content == (ROOT / relative).read_bytes(), route
        etag = response.headers["ETag"]
        again = client.get(f"/api/v1/{route}", headers={"If-None-Match": etag})
        assert again.status_code == 304, route
        assert again.content == b""


def test_api_and_static_bodies_agree_byte_for_byte(client: httpx.Client) -> None:
    """Acceptance 5: the committed snapshot equals the API response."""
    pairs = [("/api/v1/dataset", f"{SITE_DIR}/data/dataset.json")]
    pairs += [
        (f"/api/v1/charts/{chart_id}", f"{SITE_DIR}/data/charts/{chart_id}.json")
        for chart_id in CHART_IDS
    ]
    for route, static_relative in pairs:
        assert client.get(route).content == (ROOT / static_relative).read_bytes(), route


def test_unknown_chart_and_unknown_route_are_404(client: httpx.Client) -> None:
    for path in ("/api/v1/charts/nope", "/api/v1/charts/../items", "/api/v1/", "/api/v1/nope"):
        response = client.get(path)
        assert response.status_code == 404, path
        assert response.headers["Cache-Control"] == "no-store"


def test_no_per_record_route_exists_for_the_blind_partition(client: httpx.Client) -> None:
    """docs/architecture/live-app.md §11/§15: no per-record blind drilldown."""
    for path in (
        "/api/v1/records",
        "/api/v1/records/",
        "/api/v1/items",
        "/api/v1/dataset/items",
        "/api/v1/experiments/EXP-20261005-032/records",
    ):
        response = client.get(path)
        assert response.status_code in (403, 404), path
        assert b'"items"' not in response.content, path


def test_no_api_body_leaks_a_blind_record_id(client: httpx.Client) -> None:
    blind_ids = _blind_record_ids()
    assert len(blind_ids) == 2142
    for path in (
        "/api/v1/revision",
        "/api/v1/experiments/EXP-20261005-032",
        "/api/v1/dataset",
        *(f"/api/v1/charts/{chart_id}" for chart_id in CHART_IDS),
    ):
        body = client.get(path).text
        leaked = [record_id for record_id in blind_ids if record_id in body]
        assert leaked == [], f"{path}: {leaked[:3]}"
        assert '"gold"' not in body, path


def test_writes_are_refused_with_405(client: httpx.Client) -> None:
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        response = client.request(method, "/api/v1/revision")
        assert response.status_code == 405, method
        assert "GET" in response.headers["Allow"]
        assert response.json()["error"]


def test_head_matches_get_without_a_body(client: httpx.Client) -> None:
    get = client.get("/api/v1/dataset")
    head = client.head("/api/v1/dataset")
    assert head.status_code == 200
    assert head.content == b""
    assert head.headers["Content-Length"] == get.headers["Content-Length"]
    assert head.headers["ETag"] == get.headers["ETag"]


def test_options_is_answered_for_preflight(client: httpx.Client) -> None:
    response = client.request("OPTIONS", "/api/v1/revision")
    assert response.status_code == 204
    assert "GET" in response.headers["Access-Control-Allow-Methods"]


def test_cors_is_off_unless_an_origin_is_permitted(client: httpx.Client) -> None:
    response = client.get("/api/v1/revision", headers={"Origin": "http://evil.example"})
    assert "Access-Control-Allow-Origin" not in response.headers


def test_static_bundle_is_served_with_traversal_blocked(client: httpx.Client) -> None:
    index = client.get("/")
    assert index.status_code == 200
    assert index.content == (ROOT / SITE_DIR / "index.html").read_bytes()
    assert "text/html" in index.headers["Content-Type"]

    items = client.get("/data/items.json")
    assert items.status_code == 200
    assert items.content == (ROOT / SITE_DIR / "data/items.json").read_bytes()

    for path in ("/../PROJECT.md", "/..%2fPROJECT.md", "/assets/../../PROJECT.md"):
        assert client.get(path).status_code == 404, path


def test_allowed_origin_is_echoed_when_configured() -> None:
    origin = "http://localhost:5173"
    server = build_server(root=ROOT, host="127.0.0.1", port=0, allow_origins=(origin,))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        with httpx.Client(base_url=f"http://{host}:{port}", timeout=10) as http:
            allowed = http.get("/api/v1/revision", headers={"Origin": origin})
            assert allowed.headers["Access-Control-Allow-Origin"] == origin
            assert allowed.headers["Vary"] == "Origin"
            denied = http.get("/api/v1/revision", headers={"Origin": "http://other.example"})
            assert "Access-Control-Allow-Origin" not in denied.headers
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)
