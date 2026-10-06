"""Serve the EXP-032 classifier viewer with a read-only ``viewer-api.v1`` API.

Standard library only (TASK-0071). The pure contract logic lives in
``src/eval_lab/viewer_api.py``; this file is the socket. It serves two things
from one origin:

* the committed static bundle at ``site/gleif-classifier/``, so the viewer
  renders exactly as it does from a plain file host, and
* a versioned read API under ``/api/v1``, so an open viewer can notice a new
  eval run and refetch without a page reload.

Contract table::

    GET  /api/v1/revision                  JSON, no-store, no ETag (poll target)
    GET  /api/v1/experiments/EXP-20261005-032
                                           JSON, ETag, no-cache
    GET  /api/v1/dataset                   committed document verbatim, ETag
    GET  /api/v1/charts/{id}               committed document verbatim, ETag
    *    /api/v1/**  (anything else)       404 JSON error, no-store
    *    non-GET/HEAD                      405, Allow: GET, HEAD
    GET  /**                               static bundle from site/gleif-classifier/

Every response, including errors and static files, carries
``X-Viewer-Api-Version: viewer-api.v1``.

Two rules are structural, not stylistic:

* **Aggregate-only API.** There is no per-record API route and no wildcard under
  ``/api/v1`` that could reach a per-record document. EXP-032's partition is
  ``blind_holdout`` and ``docs/architecture/live-app.md`` forbids a per-record
  blind endpoint outright. The viewer's table does keep loading the committed
  static ``items.json`` from ``site/gleif-classifier/`` — that file is the
  TASK-0070 deliverable acceptance criterion 5 requires, it is already public,
  and this server adds no new exposure to it.
* **Verbatim bytes.** The dataset and chart documents are byte-frozen by
  ``scripts/export_chart_data.py --check`` in CI and their provenance embeds a
  git commit and timestamp, so they are streamed through, never re-rendered.

Usage::

    uv run --locked python scripts/serve_classifier_viewer.py --port 8123
    uv run --locked python scripts/serve_classifier_viewer.py --allow-origin http://localhost:5173
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

try:
    from eval_lab.viewer_api import (
        API_VERSION,
        CHART_DIR,
        CHART_IDS,
        EXPERIMENT_ROUTE_ID,
        ViewerState,
        build_experiment_summary,
        sha256_file,
    )
except ImportError:  # executed as a file from the repository root
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from eval_lab.viewer_api import (
        API_VERSION,
        CHART_DIR,
        CHART_IDS,
        EXPERIMENT_ROUTE_ID,
        ViewerState,
        build_experiment_summary,
        sha256_file,
    )

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = "site/gleif-classifier"
API_PREFIX = "/api/v1"
VERSION_HEADER = "X-Viewer-Api-Version"


def _etag(path: Path) -> str:
    """Strong ETag over the same LF-normalized bytes the revision hashes."""
    return f'"{sha256_file(path)}"'


def _etag_bytes(data: bytes) -> str:
    return f'"{hashlib.sha256(data).hexdigest()}"'


class ViewerHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        handler: type[BaseHTTPRequestHandler],
        *,
        root: Path,
        allow_origins: tuple[str, ...],
    ) -> None:
        super().__init__(address, handler)
        self.root = root
        self.state = ViewerState(root)
        self.allow_origins = allow_origins


class ViewerRequestHandler(BaseHTTPRequestHandler):
    server_version = "ViewerAPI/1.0"
    server: ViewerHTTPServer

    # --- response plumbing -------------------------------------------------

    def _cors_headers(self) -> dict[str, str]:
        origin = self.headers.get("Origin")
        if origin is None or origin not in self.server.allow_origins:
            return {}
        return {"Access-Control-Allow-Origin": origin, "Vary": "Origin"}

    def _respond(
        self,
        status: int,
        body: bytes,
        content_type: str,
        *,
        cache_control: str | None = None,
        etag: str | None = None,
        extra: dict[str, str] | None = None,
        include_body: bool = True,
    ) -> None:
        self.send_response(status)
        self.send_header(VERSION_HEADER, API_VERSION)
        self.send_header("Content-Type", content_type)
        self.send_header("X-Content-Type-Options", "nosniff")
        if cache_control is not None:
            self.send_header("Cache-Control", cache_control)
            self.send_header("CDN-Cache-Control", cache_control)
        if etag is not None:
            self.send_header("ETag", etag)
        for key, value in {**self._cors_headers(), **(extra or {})}.items():
            self.send_header(key, value)
        if status != HTTPStatus.NOT_MODIFIED:
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if include_body and status != HTTPStatus.NOT_MODIFIED and body:
            self.wfile.write(body)

    def _json(
        self,
        status: int,
        payload: dict[str, Any],
        *,
        cache_control: str | None = None,
        etag: str | None = None,
        extra: dict[str, str] | None = None,
        include_body: bool = True,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self._respond(
            status,
            body,
            "application/json; charset=utf-8",
            cache_control=cache_control,
            etag=etag,
            extra=extra,
            include_body=include_body,
        )

    def _error(self, status: int, message: str, *, extra: dict[str, str] | None = None) -> None:
        self._json(
            status,
            {"apiVersion": API_VERSION, "error": message, "status": int(status)},
            cache_control="no-store",
            extra=extra,
        )

    def _not_modified(self, etag: str) -> bool:
        return self.headers.get("If-None-Match") == etag

    # --- HTTP verbs --------------------------------------------------------

    def do_GET(self) -> None:
        self._dispatch(include_body=True)

    def do_HEAD(self) -> None:
        self._dispatch(include_body=False)

    def do_OPTIONS(self) -> None:
        # Always answered, so a CORS preflight from a non-permitted origin fails
        # on the missing Access-Control-Allow-Origin rather than on the status.
        self._respond(
            HTTPStatus.NO_CONTENT,
            b"",
            "text/plain; charset=utf-8",
            cache_control="no-store",
            extra={
                "Allow": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "If-None-Match",
                "Access-Control-Max-Age": "600",
            },
        )

    def _method_not_allowed(self) -> None:
        self._error(
            HTTPStatus.METHOD_NOT_ALLOWED,
            f"{self.command} is not allowed; this API is read-only",
            extra={"Allow": "GET, HEAD, OPTIONS"},
        )

    def do_POST(self) -> None:
        self._method_not_allowed()

    def do_PUT(self) -> None:
        self._method_not_allowed()

    def do_PATCH(self) -> None:
        self._method_not_allowed()

    def do_DELETE(self) -> None:
        self._method_not_allowed()

    def _dispatch(self, *, include_body: bool) -> None:
        path = unquote(urlsplit(self.path).path)
        if path == API_PREFIX or path.startswith(f"{API_PREFIX}/"):
            self._api(path[len(API_PREFIX) :], include_body=include_body)
        else:
            self._static(path, include_body=include_body)

    # --- API routes --------------------------------------------------------

    def _api(self, route: str, *, include_body: bool) -> None:
        route = route.rstrip("/") or "/"

        if route == "/revision":
            # The poll target: small, constant-size, never cached, no ETag, so a
            # client cannot be handed a stale revision by an intermediary.
            self._json(
                HTTPStatus.OK,
                self.server.state.revision_payload(),
                cache_control="no-store",
                include_body=include_body,
            )
            return

        if route.startswith("/experiments/"):
            requested = route[len("/experiments/") :]
            if requested not in (EXPERIMENT_ROUTE_ID,):
                self._error(HTTPStatus.NOT_FOUND, f"unknown experiment: {requested}")
                return
            body = json.dumps(
                build_experiment_summary(self.server.root),
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
            etag = _etag_bytes(body)
            if self._not_modified(etag):
                self._respond(HTTPStatus.NOT_MODIFIED, b"", "application/json", etag=etag)
                return
            self._respond(
                HTTPStatus.OK,
                body,
                "application/json; charset=utf-8",
                cache_control="no-cache",
                etag=etag,
                include_body=include_body,
            )
            return

        served = self._served_document(route)
        if served is not None:
            self._serve_document(served, include_body=include_body)
            return

        if route.startswith("/records"):
            # Named explicitly so the refusal is legible rather than a generic
            # 404: EXP-032 is a blind_holdout partition and no per-record
            # endpoint may exist for it (docs/architecture/live-app.md §11, §15).
            self._error(
                HTTPStatus.FORBIDDEN,
                "per-record rows are not served for a blind partition",
            )
            return

        self._error(HTTPStatus.NOT_FOUND, f"no such endpoint: {API_PREFIX}{route}")

    def _served_document(self, route: str) -> str | None:
        """Map an API route to a committed document path, or ``None``."""
        if route == "/dataset":
            return "paper/data/gleif-classifier.json"
        if route.startswith("/charts/"):
            chart_id = route[len("/charts/") :]
            if chart_id in CHART_IDS:
                return f"{CHART_DIR}/{chart_id}.json"
        return None

    def _serve_document(self, relative: str, *, include_body: bool) -> None:
        path = self.server.root / relative
        etag = _etag(path)
        if self._not_modified(etag):
            self._respond(HTTPStatus.NOT_MODIFIED, b"", "application/json", etag=etag)
            return
        body = path.read_bytes()
        self._respond(
            HTTPStatus.OK,
            body,
            "application/json; charset=utf-8",
            # Content-addressed by the strong ETag, so revalidate rather than
            # serve stale numbers; the revision endpoint is what drives refetch.
            cache_control="no-cache",
            etag=etag,
            include_body=include_body,
        )

    # --- static bundle -----------------------------------------------------

    def _static(self, url_path: str, *, include_body: bool) -> None:
        site_root = (self.server.root / SITE_DIR).resolve()
        relative = url_path.lstrip("/")
        if relative == "" or relative.endswith("/"):
            relative = f"{relative}index.html"

        candidate = (site_root / relative).resolve()
        if not candidate.is_relative_to(site_root) or not candidate.is_file():
            self._error(HTTPStatus.NOT_FOUND, f"no such file: {url_path}")
            return

        content_type, _ = mimetypes.guess_type(candidate.name)
        body = candidate.read_bytes()
        self._respond(
            HTTPStatus.OK,
            body,
            content_type or "application/octet-stream",
            cache_control="no-cache",
            etag=_etag(candidate),
            include_body=include_body,
        )

    # --- logging -----------------------------------------------------------

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"[viewer-api] {self.address_string()} {format % args}\n")


def build_server(
    *,
    root: Path,
    host: str,
    port: int,
    allow_origins: tuple[str, ...] = (),
) -> ViewerHTTPServer:
    return ViewerHTTPServer(
        (host, port),
        ViewerRequestHandler,
        root=root,
        allow_origins=allow_origins,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root holding site/ and paper/data/ (default: this checkout)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8123, help="bind port (default: 8123)")
    parser.add_argument(
        "--allow-origin",
        action="append",
        default=[],
        metavar="ORIGIN",
        help="permit this browser origin via CORS; repeatable (default: same-origin only)",
    )
    args = parser.parse_args(argv)

    server = build_server(
        root=args.root.resolve(),
        host=args.host,
        port=args.port,
        allow_origins=tuple(args.allow_origin),
    )
    host, port = server.server_address[:2]
    print(f"serving {args.root} at http://{host}:{port}/  (api {API_VERSION})")
    print(f"revision: {server.state.revision_payload()['revision']}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
