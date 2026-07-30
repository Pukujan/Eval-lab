# ADR-0004 — Mock models are a LiteLLM custom provider; fallbacks are off

- **Status:** Accepted
- **Date:** 2026-07-30

## Context

The brief requires three deterministic mock models, no live credentials in CI, a
provider-independent registry, disabled fallback between named models during
benchmark runs, recording of the *resolved* model id, and bounded retries — while
forbidding custom provider SDKs.

The naive option is `mock_response` in `litellm_params`, which returns one fixed
string per model. That is deterministic but content-blind: it cannot return a
different hypothesis set for a different bug report, so the walking skeleton would
be exercising nothing.

## Decision

Implement the three mock models as a **`litellm.CustomLLM` subclass registered
through LiteLLM's own documented extension point**, `litellm_settings.
custom_provider_map`.

Verified against the pinned source, not memory: `litellm/proxy/proxy_server.py`
L4478-4490 loads `custom_provider_map`, resolving each entry's `custom_handler`
string through `get_instance_fn(value=..., config_file_path=...)` and then calling
`custom_llm_setup()`.

```yaml
litellm_settings:
  custom_provider_map:
    - provider: reliability-mock
      custom_handler: app.models.mock_provider.reliability_mock
```

The handler is deterministic by construction: the response is a pure function of
`(model_name, sha256(canonicalised messages))`. No clock, no RNG, no network.

## Determinism controls

| Requirement | Mechanism |
|---|---|
| Disable fallback between named models | `router_settings.fallbacks: []` plus `litellm_settings.num_retries: 0` for benchmark runs; the registry additionally refuses to accept a response whose resolved model differs from the requested one |
| Record the actual resolved model | Read back `response.model` and store it on `EvaluationRun`; never assume the alias |
| Bound retries explicitly | Retries are bounded in exactly one place — Temporal's `RetryPolicy(maximum_attempts=...)` on the activity. LiteLLM's own retry is set to 0 so the two do not multiply |

That last row matters: two independently-configured retry layers silently produce
N×M attempts. Retry is Temporal's job (ADR-0002), so LiteLLM's is switched off.

## Alternatives rejected

- **`mock_response` strings** — content-blind, as above.
- **A local fake OpenAI HTTP server** — that is writing a provider adapter, which
  the brief forbids and LiteLLM already provides.
- **Bypassing the proxy and calling the handler in-process** — would not exercise
  the gateway at all. The app always talks HTTP to the proxy.

## Consequences

- The mock path needs **no credentials**: the custom provider ignores `api_key`.
- Live providers are additive — an extra `model_list` entry gated on an env var —
  with no application change, which is what "provider-independent registry" has to
  mean in practice.
- Container healthchecks must use `/health/readiness` or `/health/liveliness`;
  `/health` sits behind `user_api_key_auth` (`_health_endpoints.py` L901).
