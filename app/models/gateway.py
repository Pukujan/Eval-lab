"""The model gateway: the application's only route to a model.

Everything goes through LiteLLM. The application imports no vendor SDK, builds no
provider request, and parses no provider-specific response — LiteLLM owns all of
that (ADR-0004).

Two transports, selected by reachability and **recorded on the run**:

``http``
    POST to the LiteLLM Proxy. The primary path, and what Compose and CI use.
``in_process``
    ``litellm.completion()`` with the same custom provider registered in-process.
    Still LiteLLM's dispatch, request schema, and response normalisation — just
    without the network hop (ADR-0011).

The transport is never chosen silently: :attr:`ModelGateway.transport` ends up on
the run record and in the reliability report's caveats, for the same reason the
execution mode does. An artifact that does not say how it was produced invites
someone to assume the stronger reading.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx
import litellm

from app.models.blinding import assert_blinded, normalise_response
from app.models.mock_provider import register_in_process
from app.models.registry import ModelRegistry

DEFAULT_TIMEOUT_SECONDS = 30.0


class GatewayError(RuntimeError):
    """Raised when the gateway cannot produce a usable response."""


@dataclass(frozen=True)
class ModelInvocation:
    """One completed model call, in blinded terms."""

    pseudonym: str
    requested_model: str
    #: Read back from the response. Never assumed from the alias.
    resolved_model: str
    content: str
    prompt_tokens: int
    completion_tokens: int
    transport: str

    def parsed(self) -> dict[str, Any]:
        try:
            return json.loads(self.content)
        except (TypeError, ValueError) as exc:
            raise GatewayError(
                f"model {self.pseudonym} returned content that is not valid JSON"
            ) from exc


def proxy_is_reachable(base_url: str, timeout: float = 2.0) -> bool:
    """Whether the LiteLLM Proxy answers its unauthenticated readiness probe.

    ``/health/readiness`` and not ``/health``: the latter sits behind
    ``user_api_key_auth`` in the pinned version.
    """
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/health/readiness", timeout=timeout)
    except (httpx.HTTPError, OSError):
        return False
    return response.status_code == 200


class ModelGateway:
    """Blinded, deterministic access to configured models."""

    def __init__(
        self,
        registry: ModelRegistry,
        base_url: str,
        api_key: str,
        *,
        transport: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.registry = registry
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.timeout = timeout
        self.transport = transport or ("http" if proxy_is_reachable(base_url) else "in_process")
        if self.transport == "in_process":
            register_in_process()

    # -- invocation -------------------------------------------------------

    def invoke(
        self,
        *,
        pseudonym: str,
        logical_name: str,
        task: dict[str, Any],
        system_prompt: str = "You return only JSON matching the requested schema.",
    ) -> ModelInvocation:
        """Call a model with a structured task and return its blinded response."""
        descriptor = self.registry.get(logical_name)
        user_content = json.dumps(task, sort_keys=True, separators=(",", ":"))

        # The prompt must not name a real model. Checked before egress, because
        # after egress it is someone else's log file (threat model T-5).
        assert_blinded(system_prompt, context="system prompt")
        assert_blinded(user_content, context="task payload")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        if self.transport == "http":
            content, resolved, prompt_tokens, completion_tokens = self._invoke_http(
                descriptor.gateway_model, messages
            )
        else:
            content, resolved, prompt_tokens, completion_tokens = self._invoke_in_process(
                descriptor.gateway_model, messages
            )

        self.registry.verify_resolution(descriptor.gateway_model, resolved)

        return ModelInvocation(
            pseudonym=pseudonym,
            requested_model=descriptor.gateway_model,
            resolved_model=resolved,
            content=normalise_response(content),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            transport=self.transport,
        )

    def _invoke_http(self, model: str, messages: list[dict[str, str]]) -> tuple[str, str, int, int]:
        try:
            response = httpx.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": model, "messages": messages, "temperature": 0},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GatewayError(f"LiteLLM proxy call failed for '{model}': {exc}") from exc

        usage = payload.get("usage") or {}
        return (
            payload["choices"][0]["message"]["content"],
            payload.get("model", model),
            int(usage.get("prompt_tokens", 0)),
            int(usage.get("completion_tokens", 0)),
        )

    def _invoke_in_process(
        self, model: str, messages: list[dict[str, str]]
    ) -> tuple[str, str, int, int]:
        try:
            response = litellm.completion(
                model=f"reliability-mock/{model}",
                messages=messages,
                temperature=0,
                num_retries=0,
            )
        except Exception as exc:  # noqa: BLE001 - litellm raises provider-shaped errors
            raise GatewayError(f"in-process model call failed for '{model}': {exc}") from exc

        usage = getattr(response, "usage", None)
        return (
            response.choices[0].message.content or "",
            getattr(response, "model", model),
            int(getattr(usage, "prompt_tokens", 0) or 0),
            int(getattr(usage, "completion_tokens", 0) or 0),
        )
