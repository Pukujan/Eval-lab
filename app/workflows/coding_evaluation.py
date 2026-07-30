"""The Temporal workflow that carries the LangGraph investigation.

Temporal owns durable execution, retries, timeouts, cancellation and history. The
official ``LangGraphPlugin`` (shipped in ``temporalio==1.31.0`` behind the
``langgraph`` extra) runs each graph node marked ``execute_in="activity"`` as a
Temporal Activity, so retry and timeout policy is Temporal's, declared per node in
the graph (ADR-0002).

The workflow body is deliberately thin. All it does is fetch the registered graph
and invoke it. Anything more would be orchestration logic living outside the graph
that owns it — and every line of it would be a line Temporal or LangGraph already
provides.

Determinism rules apply: no clock, no RNG, no I/O here. Those live in activities.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.config import Settings
    from app.graphs.investigation import (
        INVESTIGATION_GRAPH_NAME,
        build_investigation_graph,
    )

WORKFLOW_EXECUTION_TIMEOUT = timedelta(minutes=20)


@workflow.defn(name="CodingEvaluationWorkflow")
class CodingEvaluationWorkflow:
    """Runs the bounded investigation graph under durable execution."""

    @workflow.run
    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        from temporalio.contrib.langgraph import graph

        application = graph(INVESTIGATION_GRAPH_NAME).compile()
        return await application.ainvoke(state)


def build_plugin():
    """Construct the official LangGraph plugin for this graph.

    ``default_activity_options`` supplies the fallback timeout and retry policy;
    individual nodes override it via their own ``metadata``. ``execute_in`` is
    deliberately absent here — the plugin rejects it in defaults, and requiring it
    per node is what stops a node silently losing its durability guarantees.
    """
    from temporalio.contrib.langgraph import LangGraphPlugin

    return LangGraphPlugin(
        graphs={INVESTIGATION_GRAPH_NAME: build_investigation_graph()},
        default_activity_options={
            "start_to_close_timeout": timedelta(seconds=120),
            "retry_policy": RetryPolicy(maximum_attempts=3),
        },
    )


def run_scoped_task_queue(settings: Settings, run_id: str) -> str:
    """A task queue private to one inline-worker run.

    The investigation's probe activities operate on a working copy on the local
    filesystem. The long-lived Compose worker also polls the shared queue, and if
    it picked up one of those activities it would be handed a path that does not
    exist inside its container — an infrastructure failure that would look
    exactly like a flaky evaluation.

    Scoping the queue to the run guarantees that the worker which created the
    working copy is the only one that can be given work referring to it.
    """
    return f"{settings.temporal_task_queue}-{run_id}"


async def execute_investigation_workflow(
    settings: Settings, state: dict[str, Any], run_id: str
) -> dict[str, Any]:
    """Connect, run an inline worker, and execute one workflow to completion.

    The worker is inline because the walking skeleton runs as a single command and
    because the investigation's activities are filesystem-bound to the working copy
    this process created — see :func:`run_scoped_task_queue`.
    """
    from temporalio.client import Client
    from temporalio.worker import Worker

    plugin = build_plugin()
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    task_queue = run_scoped_task_queue(settings, run_id)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[CodingEvaluationWorkflow],
        plugins=[plugin],
    ):
        return await client.execute_workflow(
            CodingEvaluationWorkflow.run,
            state,
            id=f"coding-evaluation-{run_id}",
            task_queue=task_queue,
            execution_timeout=WORKFLOW_EXECUTION_TIMEOUT,
        )


async def run_worker(settings: Settings) -> None:
    """Long-lived worker entry point, used by the Compose `worker` service."""
    from temporalio.client import Client
    from temporalio.worker import Worker

    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    async with Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[CodingEvaluationWorkflow],
        plugins=[build_plugin()],
    ):
        import asyncio

        await asyncio.Future()
