"""Confirm Phoenix received the complete required span tree.

Queries Phoenix's own GraphQL API — its supported query surface — rather than
reading its database. We do not own that schema and must not depend on it.

Exits non-zero if any required span is missing, which is an
``infrastructure_failure`` condition, not a statement about any patch (ADR-0012).

Usage:  python scripts/verify_phoenix_trace.py [--project NAME]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from app.config import load_settings  # noqa: E402
from app.evidence.artifacts import EvidenceError, require, write_evidence  # noqa: E402
from app.reliability.gates import REQUIRED_SPAN_NAMES  # noqa: E402

QUERY = """
{
  projects(first: 20) {
    edges {
      node {
        name
        traceCount
        spans(first: 400) { edges { node { name } } }
      }
    }
  }
}
"""


def graphql(endpoint: str, query: str, timeout: float = 20.0) -> dict:
    request = urllib.request.Request(  # noqa: S310
        f"{endpoint.rstrip('/')}/graphql",
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=None)
    parser.add_argument("--retries", type=int, default=12)
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()

    settings = load_settings()
    endpoint = settings.phoenix_endpoint or "http://localhost:6006"
    project_name = args.project or settings.phoenix_project_name

    try:
        observed: set[str] = set()
        trace_count = 0
        last_error = ""

        # Spans are exported in batches, so poll rather than assume immediacy.
        for _ in range(args.retries):
            try:
                payload = graphql(endpoint, QUERY)
            except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                time.sleep(args.interval)
                continue

            if "errors" in payload:
                last_error = json.dumps(payload["errors"])[:300]
                time.sleep(args.interval)
                continue

            for edge in payload["data"]["projects"]["edges"]:
                node = edge["node"]
                if node["name"] != project_name:
                    continue
                trace_count = node.get("traceCount", 0)
                observed = {s["node"]["name"] for s in node["spans"]["edges"]}

            if REQUIRED_SPAN_NAMES.issubset(observed):
                break
            time.sleep(args.interval)

        require(
            bool(observed),
            f"Phoenix project '{project_name}' reported no spans at {endpoint} "
            f"({last_error or 'no error'})",
        )

        missing = sorted(REQUIRED_SPAN_NAMES - observed)
        require(
            not missing,
            f"Phoenix is missing required spans: {missing}. This is an "
            "infrastructure_failure: it blocks acceptance but implies nothing "
            "about the patch.",
        )

        evidence_path = write_evidence(
            "phoenix-trace",
            {
                "claim": "Phoenix received every required span for the project",
                "endpoint": endpoint,
                "project": project_name,
                "trace_count": trace_count,
                "required_spans": sorted(REQUIRED_SPAN_NAMES),
                "observed_spans": sorted(observed),
                "missing_spans": missing,
                "verified": True,
            },
        )

        print("phoenix trace VERIFIED")
        print(f"  endpoint      : {endpoint}")
        print(f"  project       : {project_name}")
        print(f"  traces        : {trace_count}")
        print(f"  required spans: {len(REQUIRED_SPAN_NAMES)} — all present")
        print(f"  evidence      : {evidence_path}")
        return 0

    except EvidenceError as exc:
        write_evidence("phoenix-trace", {"verified": False, "failure": str(exc)})
        print(f"phoenix trace NOT VERIFIED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
