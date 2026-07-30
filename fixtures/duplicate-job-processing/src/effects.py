"""The externally visible side effect.

Stand-in for the thing you cannot take back: the email that went out, the card that
got charged, the webhook the downstream system already acted on.

This counter is the ground truth for "did processing actually happen twice?", and
it is deliberately *not* readable through any API a patch would naturally touch.
A patch can deduplicate a result list; it cannot un-send an email. That asymmetry
is the entire point of the fixture.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def record_effect(database_path: str | Path, job_id: str) -> None:
    """Perform the irreversible external effect for ``job_id``."""
    connection = sqlite3.connect(str(database_path), timeout=15.0)
    try:
        connection.execute("PRAGMA busy_timeout=15000")
        connection.execute("INSERT INTO effects (job_id) VALUES (?)", (job_id,))
        connection.commit()
    finally:
        connection.close()


def effect_count(database_path: str | Path, job_id: str) -> int:
    """How many times the external effect actually executed for ``job_id``."""
    connection = sqlite3.connect(str(database_path), timeout=15.0)
    try:
        row = connection.execute(
            "SELECT COUNT(*) FROM effects WHERE job_id = ?", (job_id,)
        ).fetchone()
        return int(row[0])
    finally:
        connection.close()
