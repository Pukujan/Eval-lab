"""Prepare — and refuse to execute — a Task 2B run.

This script builds a run plan, constructs the HTTP client in the configuration
Task 2B requires, asserts that configuration against the object actually built,
and writes a plan artifact. It makes **no network request**: there is no call site
for one in this file, and the client's own guard
(:func:`app.models.sequential_plan.assert_execution_allowed`) would refuse anyway.

Two run kinds, deliberately not interchangeable:

``--kind canary`` prepares one ``gpt-5.6-luna`` request that asks only whether the
evaluation endpoint answers. It needs no frozen snapshot, because it happens
before the freeze — and its artifact is stamped ``is_benchmark_evidence: false``
so it can never be quoted as a model result.

``--kind benchmark`` requires ``--snapshot``: a frozen, hashed alias list read off
the evaluation service. There is no flag to supply models directly and none to
accept an unlisted alias. Both existed in an earlier version and both were wrong —
the first made the snapshot advisory, the second turned a hard stop into a
checkbox.

``--assert-executable`` exits non-zero while Task 2B is blocked. That is the
execution gate; it is meant to fail until every precondition is actually met. A
gate that passes before its preconditions hold is not a gate.

    python scripts/prepare_task_2b_run.py --kind canary
    python scripts/prepare_task_2b_run.py --kind benchmark --snapshot verification/snapshot.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from app.models.alias_snapshot import (  # noqa: E402
    EVALUATION_SERVICE_URL,
    SnapshotError,
    load_snapshot,
)
from app.models.ckff_client import (  # noqa: E402
    CLIENT_RETRIES,
    ClientConfigurationError,
    assert_no_client_retry,
    build_http_client,
)
from app.models.sequential_plan import (  # noqa: E402
    BLOCKING_PRECONDITIONS,
    DEFAULT_REQUESTS_PER_MINUTE,
    EXECUTION_BLOCKED,
    ExecutionBlockedError,
    PlanError,
    RunLimits,
    assert_execution_allowed,
    build_benchmark_plan,
    build_canary_plan,
)

DEFAULT_OUTPUT = Path("artifacts") / "task-2b-run-plan.json"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kind",
        choices=("canary", "benchmark"),
        required=True,
        help="canary: one gpt-5.6-luna connectivity request. benchmark: the frozen campaign.",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=None,
        help="frozen alias snapshot of the evaluation service; required for --kind benchmark",
    )
    parser.add_argument("--prompt-id", default="task-2b-preflight-v1")
    parser.add_argument("--selection-source", default="unspecified")
    parser.add_argument("--request-timeout-seconds", type=float, default=120.0)
    parser.add_argument("--total-wall-clock-seconds", type=float, default=900.0)
    parser.add_argument("--max-requests-per-model", type=int, default=1)
    parser.add_argument("--max-completion-tokens", type=int, default=512)
    parser.add_argument("--requests-per-minute", type=int, default=DEFAULT_REQUESTS_PER_MINUTE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--assert-executable",
        action="store_true",
        help="exit non-zero while Task 2B execution is blocked (the execution gate)",
    )
    return parser


def preflight_client_configuration(limits: RunLimits) -> dict[str, object]:
    """Construct the real client and read its configuration back.

    Constructing an ``httpx.Client`` opens no connection, so this stays offline
    while still checking the object a run would actually use rather than a
    description of it.
    """
    client = build_http_client(limits.request_timeout_seconds)
    try:
        assert_no_client_retry(client)
        return {
            "client_retry_count": CLIENT_RETRIES,
            "follow_redirects": client.follow_redirects,
            "connect_timeout_seconds": client.timeout.connect,
            "read_timeout_seconds": client.timeout.read,
            "verified_against": "the constructed transport, not the keyword argument",
        }
    finally:
        client.close()


def main(argv: list[str] | None = None) -> int:
    arguments = build_argument_parser().parse_args(argv)

    limits = RunLimits(
        request_timeout_seconds=arguments.request_timeout_seconds,
        total_wall_clock_seconds=arguments.total_wall_clock_seconds,
        max_requests_per_model=arguments.max_requests_per_model,
        max_completion_tokens=arguments.max_completion_tokens,
    )

    try:
        if arguments.kind == "canary":
            if arguments.snapshot is not None:
                print(
                    "a connectivity canary takes no snapshot: it runs before the freeze "
                    "and its evidence is not benchmark evidence",
                    file=sys.stderr,
                )
                return 2
            plan = build_canary_plan(
                limits=limits,
                prompt_id=arguments.prompt_id,
                selection_source=arguments.selection_source,
            )
        else:
            if arguments.snapshot is None:
                print(
                    "--kind benchmark requires --snapshot: a frozen, hashed alias list "
                    f"read from {EVALUATION_SERVICE_URL}. There is no way to pass models "
                    "directly, because a list that cannot be tied to a retrieval time, a "
                    "source and a deployment produces evidence nobody can attribute.",
                    file=sys.stderr,
                )
                return 2
            snapshot = load_snapshot(arguments.snapshot)
            plan = build_benchmark_plan(
                snapshot,
                limits=limits,
                prompt_id=arguments.prompt_id,
                selection_source=arguments.selection_source,
                requests_per_minute=arguments.requests_per_minute,
            )
    except SnapshotError as exc:
        print(f"Task 2B alias snapshot refused: {exc}", file=sys.stderr)
        return 2
    except PlanError as exc:
        print(f"Task 2B run plan refused: {exc}", file=sys.stderr)
        return 2

    try:
        client_configuration = preflight_client_configuration(limits)
    except ClientConfigurationError as exc:
        print(f"Task 2B client preflight failed: {exc}", file=sys.stderr)
        return 3

    document = plan.as_document()
    document["client_configuration"] = client_configuration
    document["network_requests_made"] = 0

    output = Path(arguments.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(document, indent=2, sort_keys=True))
    print(f"\nRun plan written to {output}. No gateway request was made.")
    if arguments.kind == "canary":
        print("This is a CONNECTIVITY CANARY. It is not benchmark evidence.")

    if EXECUTION_BLOCKED:
        print("\nTask 2B execution is BLOCKED. Unmet preconditions:")
        for precondition in BLOCKING_PRECONDITIONS:
            print(f"  - {precondition}")

    if arguments.assert_executable:
        try:
            assert_execution_allowed()
        except ExecutionBlockedError as exc:
            print(f"\nExecution gate: {exc}", file=sys.stderr)
            return 4
        print("\nExecution gate: preconditions are recorded as met.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
