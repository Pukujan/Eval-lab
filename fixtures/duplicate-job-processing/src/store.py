"""Persistence for processed jobs.

Two tables matter:

``results``
    One row per committed processing result. The primary invariant is a statement
    about *this table*: one logical job id, at most one committed row.

``claims``
    An exclusive claim on a job id, with ``job_id`` as PRIMARY KEY so the database
    itself refuses a second claim. The known-bad processor never uses it. It exists
    because the repair is meant to be reachable without inventing new machinery —
    the invariant is available, the buggy code just does not establish it.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommittedResult:
    job_id: str
    payload: str


class ResultStore:
    """A per-worker connection to the shared SQLite database.

    Each worker constructs its own store, exactly as two processes would each hold
    their own connection. That is what makes the race real rather than simulated.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        self._connection = sqlite3.connect(self.database_path, timeout=15.0)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA busy_timeout=15000")

    @classmethod
    def initialise(cls, database_path: str | Path) -> None:
        connection = sqlite3.connect(str(database_path), timeout=15.0)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS results ("
                " row_id INTEGER PRIMARY KEY AUTOINCREMENT,"
                " job_id TEXT NOT NULL,"
                " payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS claims (job_id TEXT PRIMARY KEY)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS effects ("
                " row_id INTEGER PRIMARY KEY AUTOINCREMENT,"
                " job_id TEXT NOT NULL)"
            )
            connection.commit()
        finally:
            connection.close()

    # -- reads ------------------------------------------------------------

    def has_result(self, job_id: str) -> bool:
        """Whether a result has already been committed for ``job_id``."""
        row = self._connection.execute(
            "SELECT 1 FROM results WHERE job_id = ? LIMIT 1", (job_id,)
        ).fetchone()
        return row is not None

    def committed_results(self) -> list[CommittedResult]:
        """The public read API for committed results."""
        rows = self._connection.execute(
            "SELECT job_id, payload FROM results ORDER BY row_id"
        ).fetchall()
        return [CommittedResult(job_id=r[0], payload=r[1]) for r in rows]

    def raw_result_rows(self) -> list[tuple[str, str]]:
        """Every persisted row, with no de-duplication of any kind.

        The invariant probe reads *this*, never :meth:`committed_results`. A patch
        can change what a read API returns; it cannot change what was written.
        """
        return [
            (r[0], r[1])
            for r in self._connection.execute(
                "SELECT job_id, payload FROM results ORDER BY row_id"
            ).fetchall()
        ]

    # -- writes -----------------------------------------------------------

    def commit_result(self, job_id: str, payload: str) -> None:
        self._connection.execute(
            "INSERT INTO results (job_id, payload) VALUES (?, ?)", (job_id, payload)
        )
        self._connection.commit()

    def try_claim(self, job_id: str) -> bool:
        """Atomically claim ``job_id``. Returns False if someone already holds it.

        Unused by the known-bad processor.
        """
        try:
            self._connection.execute("INSERT INTO claims (job_id) VALUES (?)", (job_id,))
            self._connection.commit()
        except sqlite3.IntegrityError:
            return False
        return True

    def close(self) -> None:
        self._connection.close()
