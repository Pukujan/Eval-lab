"""Confirm Temporal and Phoenix state survived a stack restart.

Run *after* `docker compose stop && docker compose up`. Persistence is only
meaningful if it is checked against data written before the restart, so this reads
back the workflow histories and Phoenix traces recorded earlier in the run.
"""

from __future__ import annotations

import asyncio
import json
import sys
import urllib.request
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from app.config import load_settings  # noqa: E402
from app.evidence.artifacts import (  # noqa: E402
    EvidenceError,
    evidence_directory,
    require,
    write_evidence,
)


def preserved_workflow_ids() -> list[str]:
    """Workflow ids from histories written before the restart."""
    ids: list[str] = []
    for path in sorted(evidence_directory().glob("*.history.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        started = payload.get("events", [{}])[0].get("workflowExecutionStartedEventAttributes", {})
        workflow_id = started.get("workflowId")
        if workflow_id:
            ids.append(workflow_id)
    return ids


async def main() -> int:
    settings = load_settings()
    findings: dict[str, object] = {}

    try:
        workflow_ids = preserved_workflow_ids()
        require(
            bool(workflow_ids),
            "no pre-restart histories were preserved, so persistence cannot be checked",
        )

        from temporalio.client import Client

        client = await Client.connect(
            settings.temporal_address, namespace=settings.temporal_namespace
        )

        survived = {}
        for workflow_id in workflow_ids:
            handle = client.get_workflow_handle(workflow_id)
            described = await handle.describe()
            history = await handle.fetch_history()
            survived[workflow_id] = {
                "status": str(described.status),
                "history_event_count": len(history.events),
            }
            require(
                len(history.events) > 0,
                f"workflow {workflow_id} has no history after restart — state was lost",
            )

        # Phoenix traces must also have survived.
        endpoint = (settings.phoenix_endpoint or "http://localhost:6006").rstrip("/")
        request = urllib.request.Request(  # noqa: S310
            f"{endpoint}/graphql",
            data=json.dumps(
                {"query": "{ projects(first: 20) { edges { node { name traceCount } } } }"}
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))

        trace_counts = {
            edge["node"]["name"]: edge["node"]["traceCount"]
            for edge in payload["data"]["projects"]["edges"]
        }
        project_traces = trace_counts.get(settings.phoenix_project_name, 0)
        require(
            project_traces > 0,
            f"Phoenix reports {project_traces} traces for "
            f"'{settings.phoenix_project_name}' after restart — storage did not persist",
        )

        findings = {
            "claim": "Temporal workflow history and Phoenix traces survived a stack restart",
            "workflows_checked": survived,
            "phoenix_trace_counts": trace_counts,
            "phoenix_project_traces_after_restart": project_traces,
            "verified": True,
        }
        evidence_path = write_evidence("persistence-across-restart", findings)

        print("persistence across restart VERIFIED")
        for workflow_id, detail in survived.items():
            print(f"  {workflow_id}: {detail['status']}, {detail['history_event_count']} events")
        print(f"  phoenix traces   : {project_traces}")
        print(f"  evidence         : {evidence_path}")
        return 0

    except EvidenceError as exc:
        write_evidence("persistence-across-restart", {"verified": False, "failure": str(exc)})
        print(f"persistence NOT VERIFIED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
