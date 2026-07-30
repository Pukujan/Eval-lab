"""The privileged model-identity store.

This is the **only** module permitted to open ``privileged.db`` (ADR-0008).

Two properties make the boundary structural rather than conventional:

1. **A different file.** The mapping table does not exist in ``audit.db``, so a
   leak is not a forgotten ``WHERE`` clause — it requires deliberately opening
   another database.
2. **A capability, not a global.** :class:`PrivilegedIdentityStore` cannot be
   constructed without a :class:`PrivilegedAccess` token, and workflow code has no
   way to obtain one: the token is minted outside the workflow boundary by the
   harness that owns the run.

What this is not: an OS-level security boundary. Code that already has filesystem
access can open the file directly. That residual is recorded honestly as T-2 in
the threat model rather than dressed up.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.domain.schemas import PrivilegedModelIdentity


class PrivilegedAccessError(RuntimeError):
    """Raised when privileged identity data is requested without a capability."""


@dataclass(frozen=True)
class PrivilegedAccess:
    """Capability token for the privileged store.

    Held by the evaluation harness, never by workflow, graph, activity, scorer, or
    report code. Passing one into workflow code would be a review failure, not a
    runtime one — which is why the constructor requires it explicitly rather than
    reading an ambient global.
    """

    granted_to: str

    def __post_init__(self) -> None:
        if not self.granted_to:
            raise PrivilegedAccessError("a privileged capability needs a named holder")


class PrivilegedIdentityStore:
    """Maps pseudonyms to real vendor/model identities."""

    def __init__(self, database_path: str | Path, access: PrivilegedAccess) -> None:
        if not isinstance(access, PrivilegedAccess):
            raise PrivilegedAccessError(
                "PrivilegedIdentityStore requires a PrivilegedAccess capability; "
                "workflow components cannot construct one"
            )
        self._access = access
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.database_path), timeout=15.0)
        self._create_schema()

    def _create_schema(self) -> None:
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS model_identities ("
            " pseudonym TEXT PRIMARY KEY,"
            " vendor TEXT NOT NULL,"
            " model_identifier TEXT NOT NULL,"
            " resolved_model_identifier TEXT NOT NULL,"
            " endpoint TEXT NOT NULL,"
            " run_id TEXT NOT NULL)"
        )
        self._connection.commit()

    def record(self, run_id: str, identity: PrivilegedModelIdentity) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO model_identities"
            " (pseudonym, vendor, model_identifier, resolved_model_identifier,"
            "  endpoint, run_id) VALUES (?, ?, ?, ?, ?, ?)",
            (
                identity.pseudonym,
                identity.vendor,
                identity.model_identifier,
                identity.resolved_model_identifier,
                identity.endpoint,
                run_id,
            ),
        )
        self._connection.commit()

    def resolve(self, pseudonym: str) -> PrivilegedModelIdentity | None:
        row = self._connection.execute(
            "SELECT pseudonym, vendor, model_identifier, resolved_model_identifier,"
            " endpoint FROM model_identities WHERE pseudonym = ?",
            (pseudonym,),
        ).fetchone()
        if row is None:
            return None
        return PrivilegedModelIdentity(
            pseudonym=row[0],
            vendor=row[1],
            model_identifier=row[2],
            resolved_model_identifier=row[3],
            endpoint=row[4],
        )

    def close(self) -> None:
        self._connection.close()
