"""KNOWN-GOOD reference implementation — the answer key.

NOT AVAILABLE TO SOLVER ROLES. This directory is excluded from
``app.domain.fixtures.solver_visible_paths()`` and listed in the prohibited-path
manifest (threat model T-1).

The repair establishes the invariant instead of tidying its symptom: before any
irreversible work happens, the worker takes an **atomic claim** on the job id. The
claim is a PRIMARY KEY insert, so exclusivity is decided by the database, not by a
sequence of application-level steps that a scheduler can interleave.

Note what did *not* change: the checkpoint stays exactly where it was, so the
concurrent window is still forced wide open by the probe. The race is still run;
it just no longer produces two winners. A repair that only narrowed the window
would still fail under the probe, which is the point.
"""

from __future__ import annotations

from dataclasses import dataclass

from .effects import record_effect
from .store import ResultStore
from .sync import checkpoint


@dataclass(frozen=True)
class Job:
    job_id: str
    payload: str


class JobProcessor:
    """Processes jobs delivered at least once, idempotently."""

    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        self.store = ResultStore(database_path)

    def process(self, job: Job) -> bool:
        """Process ``job``. Returns True when this call committed a result."""
        # Cheap early exit for the common redelivery case. This is an
        # optimisation, not the correctness mechanism — the claim below is.
        if self.store.has_result(job.job_id):
            return False

        checkpoint("after-duplicate-check")

        # The correctness mechanism. Exactly one caller can win this insert;
        # everyone else observes an integrity violation and stops before doing
        # any irreversible work.
        if not self.store.try_claim(job.job_id):
            return False

        record_effect(self.database_path, job.job_id)
        self.store.commit_result(job.job_id, self._transform(job))
        return True

    @staticmethod
    def _transform(job: Job) -> str:
        return f"processed:{job.payload}"

    def close(self) -> None:
        self.store.close()
