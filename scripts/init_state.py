"""Initialise application stores and confirm the Temporal namespace exists.

Small on purpose. The application's SQLite stores create their own schema on first
connection, and ``temporal server start-dev`` creates the ``default`` namespace at
launch, so this step *verifies* initialisation rather than performing a migration
we would otherwise have to own.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from app.config import load_settings  # noqa: E402
from app.evidence.artifacts import write_evidence  # noqa: E402
from app.storage.audit import AuditStore  # noqa: E402
from app.storage.privileged import PrivilegedAccess, PrivilegedIdentityStore  # noqa: E402


async def main() -> int:
    settings = load_settings()
    settings.ensure_directories()

    audit = AuditStore(settings.audit_database)
    audit.close()
    privileged = PrivilegedIdentityStore(
        settings.privileged_database, PrivilegedAccess(granted_to="ci-initialisation")
    )
    privileged.close()

    from temporalio.client import Client

    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    describe = await client.service_client.workflow_service.describe_namespace(
        __import__(
            "temporalio.api.workflowservice.v1", fromlist=["DescribeNamespaceRequest"]
        ).DescribeNamespaceRequest(namespace=settings.temporal_namespace)
    )
    namespace_name = describe.namespace_info.name
    namespace_state = str(describe.namespace_info.state)

    write_evidence(
        "state-initialisation",
        {
            "claim": "application stores exist and the Temporal namespace is registered",
            "audit_database": str(settings.audit_database),
            "privileged_database": str(settings.privileged_database),
            "audit_database_exists": settings.audit_database.is_file(),
            "privileged_database_exists": settings.privileged_database.is_file(),
            "temporal_address": settings.temporal_address,
            "namespace": namespace_name,
            "namespace_state": namespace_state,
            "verified": True,
        },
    )

    print("state initialisation OK")
    print(f"  audit store      : {settings.audit_database}")
    print(f"  privileged store : {settings.privileged_database}")
    print(f"  temporal namespace: {namespace_name} ({namespace_state})")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
