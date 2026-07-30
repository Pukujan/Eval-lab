"""Promptfoo provider bridge to the LiteLLM gateway.

Promptfoo owns the matrix, the assertion engine and the comparison report. This
file is only the adapter that lets it drive **our** gateway, so the models it
compares are the same ones the workflow uses — not a parallel path that could
drift.

Implements Promptfoo's Python provider contract, verified against the shipped
wrapper (`promptfoo/dist/src/python/wrapper.py`): a module-level ``call_api``
taking ``(prompt, options, context)`` and returning a dict.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from app.config import load_settings  # noqa: E402
from app.models.gateway import GatewayError, ModelGateway  # noqa: E402
from app.models.registry import build_default_registry  # noqa: E402


def call_api(prompt: str, options: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Invoke one configured model with a structured task."""
    del context

    config = (options or {}).get("config") or {}
    logical_name = config.get("model", "mock-analyst")
    # Pseudonym supplied by the config: the comparison sees a pseudonym, never a
    # vendor. For mocks the "vendor" is trivially known, but the plumbing is the
    # same one a live provider would use (ADR-0008).
    pseudonym = config.get("pseudonym", "model-00000000")

    try:
        task = json.loads(prompt)
    except (TypeError, ValueError) as exc:
        return {"error": f"prompt is not valid JSON: {exc}"}

    settings = load_settings()
    gateway = ModelGateway(
        registry=build_default_registry(settings.enable_live_providers),
        base_url=settings.litellm_base_url,
        api_key=settings.litellm_master_key,
    )

    started = time.perf_counter()
    try:
        invocation = gateway.invoke(pseudonym=pseudonym, logical_name=logical_name, task=task)
    except GatewayError as exc:
        return {"error": str(exc)}
    latency_ms = round((time.perf_counter() - started) * 1000, 3)

    return {
        "output": invocation.content,
        "tokenUsage": {
            "prompt": invocation.prompt_tokens,
            "completion": invocation.completion_tokens,
            "total": invocation.prompt_tokens + invocation.completion_tokens,
        },
        "metadata": {
            "pseudonym": invocation.pseudonym,
            "resolved_model": invocation.resolved_model,
            "transport": invocation.transport,
            "latency_ms": latency_ms,
        },
        # Deterministic mocks: identical input always yields identical output, so
        # nothing here is a caching artifact.
        "cached": False,
    }
