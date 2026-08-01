"""Prepare — and refuse to execute — a Task 2B sequential evaluation run.

This script validates a human's model selection, constructs the HTTP client in
the configuration Task 2B requires, asserts that configuration against the object
actually built, and writes a run-plan artifact. It makes **no network request**:
there is no call site for one in this file, and the client's own guard
(:func:`app.models.sequential_plan.assert_execution_allowed`) would refuse anyway.

Two exit behaviours matter.

``--assert-executable`` exits non-zero while Task 2B is blocked. That is the
execution gate: it is meant to fail, loudly, until PR #1 is merged and a confirmed
zero-hidden-proxy-retry CKFF route exists. A gate that passes before its
preconditions are met is not a gate.

Without a model selection the script exits non-zero as well. The Task 2B
evaluation set is deliberately unchosen; defaulting to some list would turn an
open research decision into a silent one.

    python scripts/prepare_task_2b_run.py --models '["gpt-5.6-luna"]'
    python scripts/prepare_task_2b_run.py --models "$MODELS" --assert-executable
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from app.models.ckff_client import (  # noqa: E402
    CLIENT_RETRIES,
    ClientConfigurationError,
    assert_no_client_retry,
    build_http_client,
)
from app.models.sequential_plan import (  # noqa: E402
    BLOCKING_PRECONDITIONS,
    EXECUTION_BLOCKED,
    OBSERVED_GATEWAY_ALIASES,
    ExecutionBlockedError,
    PlanError,
    RunLimits,
    assert_execution_allowed,
    build_plan,
)

DEFAULT_OUTPUT = Path("artifacts") / "task-2b-run-plan.json"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    # No default. A default here would be a model set nobody chose.
    parser.add_argument(
        "--models",
        default="",
        help='JSON array of exact gateway aliases, e.g. \'["gpt-5.6-luna", "[aws]glm-5"]\'',
    )
    parser.add_argument("--prompt-id", default="task-2b-preflight-v1")
    parser.add_argument("--selection-source", default="unspecified")
    parser.add_argument("--request-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--total-wall-clock-seconds", type=float, default=900.0)
    parser.add_argument("--max-requests-per-model", type=int, default=1)
    parser.add_argument("--max-completion-tokens", type=int, default=512)
    parser.add_argument(
        "--allow-unconfirmed-aliases",
        action="store_true",
        help="accept an alias not in the observed list; use when the gateway has changed",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--assert-executable",
        action="store_true",
        help="exit non-zero while Task 2B execution is blocked (the execution gate)",
    )
    return parser


def preflight_client_configuration(limits: RunLimits) -> dict[str, object]:
    """Construct the real client and read its retry configuration back.

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

    try:
        limits = RunLimits(
            request_timeout_seconds=arguments.request_timeout_seconds,
            total_wall_clock_seconds=arguments.total_wall_clock_seconds,
            max_requests_per_model=arguments.max_requests_per_model,
            max_completion_tokens=arguments.max_completion_tokens,
        )
        plan = build_plan(
            arguments.models,
            limits=limits,
            prompt_id=arguments.prompt_id,
            selection_source=arguments.selection_source,
            allow_unconfirmed_aliases=arguments.allow_unconfirmed_aliases,
        )
    except PlanError as exc:
        print(f"Task 2B run plan refused: {exc}", file=sys.stderr)
        print(
            "Aliases observed on the gateway (NOT the evaluation set): "
            f"{list(OBSERVED_GATEWAY_ALIASES)}",
            file=sys.stderr,
        )
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
