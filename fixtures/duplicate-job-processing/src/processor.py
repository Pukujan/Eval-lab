"""Job processing — KNOWN-BAD version.

The defect: a check-then-write race.

``process`` asks "has this job already been done?", and if not, does the work and
commits the result. Under at-least-once delivery two workers can receive the same
job id, both observe "not done yet", and both proceed. Nothing between the check
and the write establishes exclusivity, so the external effect fires twice and two
result rows are committed for one logical job id.

The store already exposes :meth:`ResultStore.try_claim`, backed by a PRIMARY KEY.
The machinery for correctness is present and simply not used — which is what makes
this a design defect rather than a missing feature.
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
    """Processes jobs delivered at least once."""

    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        self.store = ResultStore(database_path)

    def process(self, job: Job) -> bool:
        """Process ``job``. Returns True when this call committed a result.

        BUG: the window between the check below and the commit is unguarded.
        """
        if self.store.has_result(job.job_id):
            return False

        # Every worker that got here observed "not yet processed". Under
        # concurrent delivery, that is more than one of them.
        checkpoint("after-duplicate-check")

        record_effect(self.database_path, job.job_id)
        self.store.commit_result(job.job_id, self._transform(job))
        return True

    @staticmethod
    def _transform(job: Job) -> str:
        return f"processed:{job.payload}"

    def close(self) -> None:
        self.store.close()
