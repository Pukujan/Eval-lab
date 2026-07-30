"""A deliberately incompatible workflow variation, used to prove replay bites.

A replay test that only ever passes is indistinguishable from a replay test that
does nothing. This module supplies a workflow registered under the **same name**
as :class:`app.workflows.durability.DurableCheckpointWorkflow` but with a
different command sequence, so replaying a real recorded history against it must
raise a nondeterminism error.

It is never registered on a worker — only handed to
:class:`temporalio.worker.Replayer` by the determinism verification script.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.workflows.durability import commit_terminal_effect, record_durable_checkpoint


@workflow.defn(name="DurableCheckpointWorkflow", sandboxed=False)
class IncompatibleDurableCheckpointWorkflow:
    """Same workflow name, incompatible history.

    The genuine workflow records a checkpoint, waits for a signal, then commits.
    This variation commits **first** and never waits — so on the very first
    workflow task the commands it issues disagree with the events already in the
    recorded history, which is exactly the class of change Temporal's replayer is
    designed to catch when a workflow is edited without versioning.
    """

    def __init__(self) -> None:
        self._resume = False

    @workflow.signal(name="resume")
    def resume(self) -> None:
        self._resume = True

    @workflow.run
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        terminal = await workflow.execute_activity(
            commit_terminal_effect,
            params,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        checkpoint = await workflow.execute_activity(
            record_durable_checkpoint,
            params,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        return {"terminal": terminal, "checkpoint": checkpoint}
