# ADR-0011 — Gateway transport falls back in-process, and says so

- **Status:** Accepted
- **Date:** 2026-07-30

## Context

The application's only route to a model is LiteLLM. The primary transport is HTTP
to the LiteLLM Proxy. But `make test` and `make demo` must work with **no running
services and no credentials**, and in the sandbox this was built in, the proxy's
container image cannot be pulled at all (registry egress denied).

A skeleton whose demo requires a service that cannot start is a skeleton that never
gets exercised.

## Decision

`ModelGateway` supports two transports and picks one by probing
`GET /health/readiness` (unauthenticated in the pinned version;
`/health` is not — it sits behind `user_api_key_auth`):

| Transport | Mechanism | When |
|---|---|---|
| `http` | `POST {base}/v1/chat/completions` to the LiteLLM Proxy | Proxy reachable — the primary path, used by Compose and CI |
| `in_process` | `litellm.completion()` with the same `custom_provider_map` handler registered in-process | Proxy unreachable |

The choice is recorded on `ModelInvocation.transport`, propagated to the run
record, and surfaced as a report caveat. It is never made silently.

## Why this is not a bypass of LiteLLM

Both transports are LiteLLM. The `in_process` path uses LiteLLM's own dispatch,
request schema, provider resolution, and response normalisation — the same
`CustomLLM` handler object the proxy loads through `custom_provider_map`. What is
absent is the network hop and the proxy's *operational* features: virtual keys,
budgets, rate limiting, request logging, and multi-client sharing.

No provider adapter, request builder, or response parser is reimplemented. If it
were, the correct fix would be to delete it and use the proxy.

## Consequences

- Unit tests exercise the handler contract with no service running.
- Integration tests that specifically assert **proxy** behaviour (health endpoints,
  config loading, `custom_provider_map` resolution) require the proxy and **skip**
  when it is unreachable, naming what was unavailable.
- A run whose transport was `in_process` cannot be read as evidence that the proxy
  deployment works. That distinction is the whole reason the field exists.
