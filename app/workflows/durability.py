"""Durability, retry and timeout probe workflows.

These exist to produce **real Temporal history** for the infrastructure claims the
walking skeleton could not previously demonstrate. They are deliberately separate
from the coding-evaluation workflow: they prove properties of the *platform*, not
of a patch, and mixing the two would let an infrastructure result masquerade as a
coding verdict.

Nothing here reimplements Temporal. There is no retry loop, no backoff arithmetic,
no timer wheel, and no checkpoint store standing in for workflow history — every
one of those is configured on Temporal and then *observed* in the history it wrote.

The durable effect ledger is the same idea as the fixture's effect counter: an
append-only SQLite table. If an activity re-executes, a second row appears. That is
how "did not repeat an already committed external effect" becomes a number rather
than an assurance.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import activity, workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

DURABILITY_TASK_QUEUE = "reliability-durability"

#: Retry policy for the retry probe. Small, explicit, and bounded so the test can
#: assert every field back out of history.
RETRY_PROBE_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=4),
    maximum_attempts=5,
)


# ---------------------------------------------------------------------------
# Durable effect ledger (activity side only — never touched from workflow code)
# ---------------------------------------------------------------------------


def _connect(ledger_path: str):
    import sqlite3

    connection = sqlite3.connect(ledger_path, timeout=20.0)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=20000")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS effects ("
        " row_id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " run_key TEXT NOT NULL,"
        " step TEXT NOT NULL,"
        " attempt INTEGER NOT NULL,"
        " worker_identity TEXT NOT NULL,"
        " recorded_at REAL NOT NULL)"
    )
    connection.commit()
    return connection


def record_effect(ledger_path: str, run_key: str, step: str, attempt: int, identity: str) -> int:
    """Append one externally visible effect and return the new total for the step."""
    import time

    connection = _connect(ledger_path)
    try:
        connection.execute(
            "INSERT INTO effects (run_key, step, attempt, worker_identity, recorded_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (run_key, step, attempt, identity, time.time()),
        )
        connection.commit()
        row = connection.execute(
            "SELECT COUNT(*) FROM effects WHERE run_key = ? AND step = ?", (run_key, step)
        ).fetchone()
        return int(row[0])
    finally:
        connection.close()


def effect_rows(ledger_path: str, run_key: str) -> list[dict[str, Any]]:
    connection = _connect(ledger_path)
    try:
        return [
            {
                "step": r[0],
                "attempt": r[1],
                "worker_identity": r[2],
                "recorded_at": r[3],
            }
            for r in connection.execute(
                "SELECT step, attempt, worker_identity, recorded_at FROM effects"
                " WHERE run_key = ? ORDER BY row_id",
                (run_key,),
            )
        ]
    finally:
        connection.close()


def effect_count(ledger_path: str, run_key: str, step: str) -> int:
    connection = _connect(ledger_path)
    try:
        row = connection.execute(
            "SELECT COUNT(*) FROM effects WHERE run_key = ? AND step = ?", (run_key, step)
        ).fetchone()
        return int(row[0])
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------


@activity.defn(name="record_durable_checkpoint")
async def record_durable_checkpoint(params: dict[str, Any]) -> dict[str, Any]:
    """Record a durable checkpoint as an externally visible effect.

    Executed by the FIRST worker. After that worker is killed and a second one
    takes over, this activity must not run again — its result lives in workflow
    history, and Temporal replays the result rather than the work.
    """
    info = activity.info()
    total = record_effect(
        params["ledger_path"],
        params["run_key"],
        "checkpoint",
        info.attempt,
        str(info.workflow_run_id or ""),
    )
    return {
        "step": "checkpoint",
        "attempt": info.attempt,
        "total_effects_for_step": total,
        "activity_id": info.activity_id,
    }


@activity.defn(name="commit_terminal_effect")
async def commit_terminal_effect(params: dict[str, Any]) -> dict[str, Any]:
    """The post-resume effect, executed by whichever worker is alive."""
    info = activity.info()
    total = record_effect(
        params["ledger_path"],
        params["run_key"],
        "terminal",
        info.attempt,
        str(info.workflow_run_id or ""),
    )
    return {"step": "terminal", "attempt": info.attempt, "total_effects_for_step": total}


@activity.defn(name="flaky_activity")
async def flaky_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Fail a known number of times, then succeed.

    Each attempt appends a row, so the number of attempts is observable on disk as
    well as in history — two independent witnesses for the same claim.

    The *consequential* side effect is recorded only on the successful attempt,
    which is what makes "no duplicate consequential side effect" checkable.
    """
    info = activity.info()
    record_effect(
        params["ledger_path"],
        params["run_key"],
        "attempt",
        info.attempt,
        str(info.workflow_run_id or ""),
    )

    if info.attempt <= int(params["fail_times"]):
        raise ApplicationError(
            f"induced failure on attempt {info.attempt} of {params['fail_times']}",
            type="InducedFailure",
            non_retryable=False,
        )

    total = record_effect(
        params["ledger_path"],
        params["run_key"],
        "committed",
        info.attempt,
        str(info.workflow_run_id or ""),
    )
    return {
        "final_attempt": info.attempt,
        "committed_effect_total": total,
    }


@activity.defn(name="slow_activity")
async def slow_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Sleep past the configured start-to-close timeout."""
    await asyncio.sleep(float(params["sleep_seconds"]))
    return {"unreachable": True}


DURABILITY_ACTIVITIES = [
    record_durable_checkpoint,
    commit_terminal_effect,
    flaky_activity,
    slow_activity,
]


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------


@workflow.defn(name="DurableCheckpointWorkflow")
class DurableCheckpointWorkflow:
    """Checkpoint, wait for an external signal, then commit.

    The wait is what makes the worker-interruption test meaningful: while the
    workflow is blocked on ``wait_condition`` there is no workflow task in
    flight, so killing the worker is a genuine mid-flight interruption of a
    *durable* execution rather than the abandonment of an in-memory one.
    """

    def __init__(self) -> None:
        self._resume = False
        self._checkpoint: dict[str, Any] | None = None

    @workflow.signal(name="resume")
    def resume(self) -> None:
        self._resume = True

    @workflow.query(name="checkpoint_recorded")
    def checkpoint_recorded(self) -> bool:
        return self._checkpoint is not None

    @workflow.run
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        self._checkpoint = await workflow.execute_activity(
            record_durable_checkpoint,
            params,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        # Blocked here across the worker kill/restart boundary.
        await workflow.wait_condition(
            lambda: self._resume, timeout=timedelta(seconds=int(params.get("resume_timeout", 300)))
        )

        terminal = await workflow.execute_activity(
            commit_terminal_effect,
            params,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        return {
            "checkpoint": self._checkpoint,
            "terminal": terminal,
            "workflow_id": workflow.info().workflow_id,
            "run_id": workflow.info().run_id,
        }


@workflow.defn(name="RetryProbeWorkflow")
class RetryProbeWorkflow:
    """Run an activity that fails a known number of times before succeeding."""

    @workflow.run
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        result = await workflow.execute_activity(
            flaky_activity,
            params,
            start_to_close_timeout=timedelta(seconds=20),
            retry_policy=RETRY_PROBE_POLICY,
        )
        return {
            "activity_result": result,
            "workflow_id": workflow.info().workflow_id,
        }


@workflow.defn(name="TimeoutProbeWorkflow")
class TimeoutProbeWorkflow:
    """Run an activity that exceeds its start-to-close timeout.

    The documented failure policy: an activity timeout is an **infrastructure**
    condition. It says the harness could not complete a step; it says nothing
    about whether a patch under evaluation was correct. Classifying it as
    ``rejected`` would fabricate a coding verdict out of a platform problem, so
    this workflow returns the classification explicitly and the reliability layer
    carries it through unchanged.
    """

    @workflow.run
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            await workflow.execute_activity(
                slow_activity,
                params,
                start_to_close_timeout=timedelta(seconds=int(params["timeout_seconds"])),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
        except ActivityError as exc:
            cause = exc.cause
            return {
                "classification": "infrastructure_failure",
                "timed_out": type(cause).__name__ == "TimeoutError",
                "cause_type": type(cause).__name__,
                "detail": str(cause)[:300],
                "workflow_id": workflow.info().workflow_id,
            }
        return {
            "classification": "unexpected_success",
            "timed_out": False,
            "workflow_id": workflow.info().workflow_id,
        }


DURABILITY_WORKFLOWS = [
    DurableCheckpointWorkflow,
    RetryProbeWorkflow,
    TimeoutProbeWorkflow,
]
