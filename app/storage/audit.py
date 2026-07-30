"""The agent-accessible audit store.

Everything the workflow, graph nodes, activities, scorers and reports may read.
Records are keyed by **pseudonym only**; this database has no table capable of
holding a vendor name or a real model identifier.

Append-only in the writer: there is no ``UPDATE`` and no ``DELETE`` anywhere in
this module. That is enforcement in application code, not in the engine — a
process with direct SQLite access can still rewrite history (threat model T-7).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.domain.schemas import (
    EvaluationRun,
    Evidence,
    ProbeResult,
    ReliabilityDecision,
    RootCauseHypothesis,
)

_FORBIDDEN_KEYS = {"vendor", "model_identifier", "resolved_model_identifier", "api_key"}


class AuditStoreError(RuntimeError):
    pass


class AuditStore:
    """Append-only application audit records."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.database_path), timeout=15.0)
        self._create_schema()

    def _create_schema(self) -> None:
        for statement in (
            "CREATE TABLE IF NOT EXISTS runs ("
            " run_id TEXT PRIMARY KEY, specification_id TEXT NOT NULL,"
            " execution_mode TEXT NOT NULL, payload TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS hypotheses ("
            " run_id TEXT NOT NULL, hypothesis_id TEXT NOT NULL,"
            " mechanism_class TEXT NOT NULL, payload TEXT NOT NULL,"
            " PRIMARY KEY (run_id, hypothesis_id))",
            "CREATE TABLE IF NOT EXISTS evidence ("
            " run_id TEXT NOT NULL, evidence_id TEXT NOT NULL,"
            " polarity TEXT NOT NULL, payload TEXT NOT NULL,"
            " PRIMARY KEY (run_id, evidence_id))",
            "CREATE TABLE IF NOT EXISTS probe_results ("
            " run_id TEXT NOT NULL, probe_id TEXT NOT NULL,"
            " outcome TEXT NOT NULL, payload TEXT NOT NULL,"
            " PRIMARY KEY (run_id, probe_id))",
            "CREATE TABLE IF NOT EXISTS decisions ("
            " run_id TEXT PRIMARY KEY, outcome TEXT NOT NULL, payload TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS spans ("
            " run_id TEXT NOT NULL, span_name TEXT NOT NULL, ordinal INTEGER NOT NULL,"
            " PRIMARY KEY (run_id, span_name, ordinal))",
        ):
            self._connection.execute(statement)
        self._connection.commit()

    # -- guards -----------------------------------------------------------

    @staticmethod
    def _reject_identity_fields(payload: dict[str, Any]) -> None:
        """Refuse to persist anything shaped like a real model identity.

        Defence in depth: this database structurally cannot hold the mapping, but
        a caller could still try to smuggle a vendor name inside a free-text
        payload. Cheap to check, and the failure is loud.
        """
        found = _FORBIDDEN_KEYS.intersection(payload)
        if found:
            raise AuditStoreError(
                f"refusing to write privileged identity fields to the audit store: {sorted(found)}"
            )

    #: Table -> allowed columns. Interpolating identifiers into SQL is only safe
    #: because both sides are checked against this constant, so nothing derived
    #: from a payload can ever reach the query string.
    _SCHEMA: dict[str, frozenset[str]] = {
        "runs": frozenset({"run_id", "specification_id", "execution_mode", "payload"}),
        "hypotheses": frozenset({"run_id", "hypothesis_id", "mechanism_class", "payload"}),
        "evidence": frozenset({"run_id", "evidence_id", "polarity", "payload"}),
        "probe_results": frozenset({"run_id", "probe_id", "outcome", "payload"}),
        "decisions": frozenset({"run_id", "outcome", "payload"}),
        "spans": frozenset({"run_id", "span_name", "ordinal"}),
    }

    def _write(self, table: str, columns: tuple[str, ...], values: tuple[Any, ...]) -> None:
        allowed = self._SCHEMA.get(table)
        if allowed is None or not set(columns).issubset(allowed):
            raise AuditStoreError(f"refusing to write unknown table/columns: {table}{columns}")

        placeholders = ", ".join("?" for _ in columns)
        # S608: table and column names are validated against _SCHEMA immediately
        # above; every *value* is bound as a parameter.
        self._connection.execute(
            f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",  # noqa: S608
            values,
        )
        self._connection.commit()

    # -- writes -----------------------------------------------------------

    def record_run(self, run: EvaluationRun) -> None:
        payload = run.model_dump(mode="json")
        self._reject_identity_fields(payload)
        self._write(
            "runs",
            ("run_id", "specification_id", "execution_mode", "payload"),
            (run.run_id, run.specification_id, str(run.execution_mode), json.dumps(payload)),
        )

    def record_hypothesis(self, run_id: str, hypothesis: RootCauseHypothesis) -> None:
        payload = hypothesis.model_dump(mode="json")
        self._reject_identity_fields(payload)
        self._write(
            "hypotheses",
            ("run_id", "hypothesis_id", "mechanism_class", "payload"),
            (run_id, hypothesis.hypothesis_id, hypothesis.mechanism_class, json.dumps(payload)),
        )

    def record_evidence(self, run_id: str, evidence: Evidence) -> None:
        payload = evidence.model_dump(mode="json")
        self._reject_identity_fields(payload)
        self._write(
            "evidence",
            ("run_id", "evidence_id", "polarity", "payload"),
            (run_id, evidence.evidence_id, str(evidence.polarity), json.dumps(payload)),
        )

    def record_probe_result(self, run_id: str, result: ProbeResult) -> None:
        payload = result.model_dump(mode="json")
        self._write(
            "probe_results",
            ("run_id", "probe_id", "outcome", "payload"),
            (run_id, result.probe_id, str(result.outcome), json.dumps(payload)),
        )

    def record_decision(self, decision: ReliabilityDecision) -> None:
        payload = decision.model_dump(mode="json")
        self._write(
            "decisions",
            ("run_id", "outcome", "payload"),
            (decision.run_id, decision.outcome, json.dumps(payload)),
        )

    def record_span(self, run_id: str, span_name: str, ordinal: int) -> None:
        self._write("spans", ("run_id", "span_name", "ordinal"), (run_id, span_name, ordinal))

    # -- reads ------------------------------------------------------------

    def evidence_ids(self, run_id: str) -> set[str]:
        return {
            row[0]
            for row in self._connection.execute(
                "SELECT evidence_id FROM evidence WHERE run_id = ?", (run_id,)
            )
        }

    def span_names(self, run_id: str) -> set[str]:
        return {
            row[0]
            for row in self._connection.execute(
                "SELECT span_name FROM spans WHERE run_id = ?", (run_id,)
            )
        }

    def has_run(self, run_id: str) -> bool:
        return (
            self._connection.execute(
                "SELECT 1 FROM runs WHERE run_id = ? LIMIT 1", (run_id,)
            ).fetchone()
            is not None
        )

    def resolve_model_identity(self, pseudonym: str) -> None:
        """Always ``None``: this store cannot resolve pseudonyms.

        Present so the impossibility is explicit and testable, rather than being
        an absence a reader has to infer.
        """
        return None

    def close(self) -> None:
        self._connection.close()
