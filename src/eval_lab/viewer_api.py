"""Read-only viewer API contract logic for the EXP-032 classifier viewer (TASK-0071).

The GLEIF classifier viewer ships as static assets, which means it goes stale
silently: a new eval run lands, the committed snapshot keeps showing the old
numbers, and nothing in the UI says so. This module is the pure logic behind a
small read-only HTTP API (``viewer-api.v1``) that lets an open viewer notice the
change and refetch. The HTTP surface lives in
``scripts/serve_classifier_viewer.py``; everything here is importable and
testable without a socket.

Design rules:

* **Aggregate-only.** ``docs/architecture/live-app.md`` (TASK-0060, issue #71)
  states twice that no per-record endpoint exists for a blind partition ("No
  per-record blind drilldown, ever"). EXP-032's partition is ``blind_holdout``,
  so this module never exposes per-record rows. The 2142-record table keeps
  loading from the committed static ``site/gleif-classifier/data/items.json``.
* **Serve the committed bytes verbatim.** The chart and dataset documents are
  byte-frozen by ``scripts/export_chart_data.py --check`` in CI and their
  provenance embeds a git commit and timestamp, so they are copied through, never
  re-rendered.
* **The revision is derived, not declared.** It hashes the content the viewer
  actually shows, so "the revision changed" implies "the viewer's data changed"
  and nothing else. Hashing the *upstream* experiment artifacts instead would
  flip the revision while every served byte stayed identical.
* **The revision covers both faces.** The API serves the ``paper/data`` exports;
  the viewer's table reads the static ``items.json``. Hashing the union means a
  regenerated export with stale site copies cannot report a stable revision.
* Deterministic: paths are sorted, hashes are over LF-normalized bytes so a
  Windows CRLF checkout hashes identically, and no timestamp is generated.
"""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any

import yaml

API_VERSION = "viewer-api.v1"
EXPERIMENT_ID = "EXP-20261005-032-gleif-classifier"
# Route form: the API path uses the short id, not the full directory name.
EXPERIMENT_ROUTE_ID = "EXP-20261005-032"
# Short form used in the API route path (the full ID is long and its date and
# sequence already identify it uniquely within the route namespace).
EXPERIMENT_ROUTE_ID = "EXP-20261005-032"
DATASET_ID = "eval-lab/gleif-classifier"
PARTITION = "blind_holdout"

EXPERIMENT_DIR = f"experiments/{EXPERIMENT_ID}"
DATASET_DOC = "paper/data/gleif-classifier.json"
CHART_DIR = "paper/data/classifier-charts"
ITEMS_DOC = "site/gleif-classifier/data/items.json"

# The bytes the viewer actually renders. Sorted, so the hash is order-stable.
REVISION_FILES: tuple[str, ...] = (
    DATASET_DOC,
    ITEMS_DOC,
    *(
        f"{CHART_DIR}/{name}.json"
        for name in (
            "classifier_class_distribution",
            "classifier_confidence_histogram",
            "classifier_coverage_at_target_error",
            "classifier_family_scores",
            "classifier_reliability",
            "classifier_risk_coverage",
        )
    ),
)

# Upstream artifacts behind those bytes. Pipeline visibility only: a new run
# landing must NOT flip the UI's revision until the served bytes actually change.
INPUT_FILES: tuple[str, ...] = (
    f"{EXPERIMENT_DIR}/records.jsonl",
    f"{EXPERIMENT_DIR}/typed-question-spec.json",
    f"{EXPERIMENT_DIR}/results.json",
    *(
        f"{EXPERIMENT_DIR}/runs/{family}/predictions.jsonl"
        for family in (
            "entity-category",
            "legal-jurisdiction",
            "registration-status",
        )
    ),
)

CHART_IDS: tuple[str, ...] = tuple(
    Path(path).stem for path in REVISION_FILES if path.startswith(f"{CHART_DIR}/")
)


def sha256_file(path: Path) -> str:
    """SHA-256 of the LF-normalized bytes, so CRLF checkouts hash identically."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _hash_tree(root: Path, relative_paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(relative_paths):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(root / relative).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def compute_revision(root: Path) -> str:
    """Hash of everything the viewer shows, plus the contract version."""
    digest = hashlib.sha256()
    digest.update(API_VERSION.encode("ascii"))
    digest.update(b"\n")
    digest.update(_hash_tree(root, REVISION_FILES).encode("ascii"))
    return digest.hexdigest()


def compute_inputs_revision(root: Path) -> str:
    """Hash of the upstream experiment artifacts. Never drives UI invalidation."""
    return _hash_tree(root, INPUT_FILES)


def _load_json(root: Path, relative: str) -> dict[str, Any]:
    loaded = json.loads((root / relative).read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError(f"{relative}: expected a JSON object")
    return loaded


def build_revision_payload(root: Path) -> dict[str, Any]:
    """The cheap endpoint the viewer polls: small, constant-size, no chart data."""
    items = _load_json(root, ITEMS_DOC)
    return {
        "apiVersion": API_VERSION,
        "revision": compute_revision(root),
        "inputsRevision": compute_inputs_revision(root),
        "experimentId": EXPERIMENT_ID,
        "datasetId": DATASET_ID,
        "partition": PARTITION,
        "recordCount": items["recordCount"],
        "resolvedCount": items["resolvedCount"],
        "families": items["families"],
    }


def build_experiment_summary(root: Path) -> dict[str, Any]:
    """Experiment metadata, derived from ``experiment.yaml`` and ``results.json``."""
    manifest = yaml.safe_load(
        (root / EXPERIMENT_DIR / "experiment.yaml").read_text(encoding="utf-8")
    )
    results = _load_json(root, f"{EXPERIMENT_DIR}/results.json")
    judge = manifest.get("judge") or {}
    return {
        "apiVersion": API_VERSION,
        "experimentId": EXPERIMENT_ID,
        "datasetId": DATASET_ID,
        "status": manifest.get("status"),
        "hypothesis": manifest.get("hypothesis"),
        "codeCommit": manifest.get("code_commit"),
        "model": judge.get("model"),
        "provider": results.get("provider"),
        "route": judge.get("route"),
        "partition": results.get("partition", PARTITION),
        "recordCount": results["record_count"],
        "resolvedCount": results["resolved_count"],
        "statusCounts": results.get("status_counts", {}),
        "families": sorted((results.get("families") or {}).keys()),
        "goldProvenance": results.get("gold_provenance"),
        "revision": compute_revision(root),
    }


def read_served_document(root: Path, relative: str) -> bytes:
    """Return a committed document's bytes verbatim, for pass-through serving."""
    if relative not in REVISION_FILES:
        raise KeyError(f"{relative}: not a served document")
    return (root / relative).read_bytes()


class ViewerState:
    """Memoizes the revision hashes, keyed on the served files' ``(mtime, size)``.

    A poll every 30 s must not re-hash several megabytes each tick, but it must
    also notice a change. The stat key is the cheap middle ground. Guarded by a
    lock because ``ThreadingHTTPServer`` handles concurrent polls.
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._lock = threading.Lock()
        self._key: tuple[tuple[str, int, int], ...] | None = None
        self._payload: dict[str, Any] | None = None

    def _stat_key(self) -> tuple[tuple[str, int, int], ...]:
        entries = []
        for relative in sorted(set(REVISION_FILES) | set(INPUT_FILES)):
            stat = (self._root / relative).stat()
            entries.append((relative, stat.st_mtime_ns, stat.st_size))
        return tuple(entries)

    def revision_payload(self) -> dict[str, Any]:
        key = self._stat_key()
        with self._lock:
            if self._payload is None or key != self._key:
                self._payload = build_revision_payload(self._root)
                self._key = key
            return self._payload
