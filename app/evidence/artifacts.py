"""Writing inspectable evidence artifacts.

Every infrastructure claim this task makes has to be checkable by someone who was
not there. So each verification writes two things: a small JSON summary of what it
asserted, and the **raw Temporal history** it asserted against.

History is serialised with the SDK's own :meth:`WorkflowHistory.to_json_dict`, and
every assertion downstream reads that same structure. We do not write a custom
history parser — the SDK provides the supported serialization and
:class:`temporalio.worker.Replayer` provides the supported replay, so both are used
as given.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import load_settings


def evidence_directory() -> Path:
    """Where evidence artifacts are written (``EVIDENCE_DIR`` overrides)."""
    override = os.environ.get("EVIDENCE_DIR")
    base = Path(override) if override else load_settings().var_dir / "evidence"
    base.mkdir(parents=True, exist_ok=True)
    return base


def write_evidence(name: str, payload: dict[str, Any]) -> Path:
    """Write a JSON evidence summary and return its path."""
    payload = {
        **payload,
        "recorded_at": datetime.now(UTC).isoformat(),
        "evidence_name": name,
    }
    destination = evidence_directory() / f"{name}.json"
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return destination


def write_history(name: str, history: Any) -> Path:
    """Persist a :class:`temporalio.client.WorkflowHistory` as JSON."""
    destination = evidence_directory() / f"{name}.history.json"
    destination.write_text(
        json.dumps(history.to_json_dict(), indent=2, sort_keys=True), encoding="utf-8"
    )
    return destination


def event_types(history_dict: dict[str, Any]) -> list[str]:
    """Ordered event-type names from a serialised history."""
    return [event.get("eventType", "") for event in history_dict.get("events", [])]


def events_of_type(history_dict: dict[str, Any], event_type: str) -> list[dict[str, Any]]:
    return [e for e in history_dict.get("events", []) if e.get("eventType") == event_type]


def workflow_status_name(status: Any) -> str:
    """Readable name for a Temporal ``WorkflowExecutionStatus``.

    ``WorkflowExecutionStatus`` is an ``IntEnum``, so ``str(status)`` is ``"2"``,
    not ``"COMPLETED"``. Formatting it into an assertion or an evidence record
    therefore produces something that looks like a value but carries no meaning —
    CI run 30577856007 reported "terminal status was 2" for a workflow that had in
    fact completed perfectly.

    Assertions should compare against the enum member; this is for *recording* a
    status a human will read.
    """
    return getattr(status, "name", str(status))


class EvidenceError(AssertionError):
    """Raised when an infrastructure claim could not be evidenced."""


def require(condition: bool, message: str) -> None:
    """Assert a claim, with a message that names what was expected."""
    if not condition:
        raise EvidenceError(message)
