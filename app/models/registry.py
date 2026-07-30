"""Provider-independent model registry.

Holds an arbitrary number of configured models keyed by a stable logical name. The
application never names a vendor: it asks for a role, gets a pseudonym, and the
registry resolves that to whatever the gateway is configured to call.

Three requirements from the brief live here, and each is a specific mechanism
rather than a hope:

* **No fallback between named models during benchmark runs.** ``allow_fallback`` is
  ``False`` and the registry rejects a response whose resolved model differs from
  the one requested. Silent substitution is worse than an error, because the result
  still looks like a result.
* **Record the actual resolved model identifier.** Read back from the response,
  never assumed from the alias.
* **Bound retries explicitly.** One layer, named, defaulting to zero here because
  Temporal owns retry (ADR-0002, ADR-0004).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.mock_provider import MOCK_MODEL_NAMES


class ModelResolutionError(RuntimeError):
    """Raised when a model resolves to something other than what was requested."""


@dataclass(frozen=True)
class ModelDescriptor:
    """One configured model, as the application sees it."""

    logical_name: str
    #: The name the gateway is asked for. For mocks this is the proxy alias.
    gateway_model: str
    vendor: str
    endpoint: str
    is_mock: bool = True
    #: Explicit, bounded. Zero means "Temporal is the only retry layer".
    max_retries: int = 0
    requires_credentials: bool = False


@dataclass
class ModelRegistry:
    """An arbitrary number of configured models."""

    descriptors: dict[str, ModelDescriptor] = field(default_factory=dict)
    allow_fallback: bool = False

    def register(self, descriptor: ModelDescriptor) -> None:
        self.descriptors[descriptor.logical_name] = descriptor

    def get(self, logical_name: str) -> ModelDescriptor:
        try:
            return self.descriptors[logical_name]
        except KeyError as exc:
            raise ModelResolutionError(
                f"model '{logical_name}' is not registered; known: {sorted(self.descriptors)}"
            ) from exc

    @property
    def logical_names(self) -> tuple[str, ...]:
        return tuple(sorted(self.descriptors))

    @property
    def mock_names(self) -> tuple[str, ...]:
        return tuple(sorted(n for n, d in self.descriptors.items() if d.is_mock))

    def requires_no_credentials(self) -> bool:
        """True when every registered model can run without a credential."""
        return all(not d.requires_credentials for d in self.descriptors.values())

    def verify_resolution(self, requested: str, resolved: str) -> None:
        """Fail loudly when the gateway answered as a different model.

        With fallback disabled this should be impossible; checking anyway is how
        a misconfiguration surfaces as an error rather than as quietly invalid
        benchmark data.
        """
        if self.allow_fallback:
            return
        requested_base = requested.split("/")[-1]
        resolved_base = resolved.split("/")[-1]
        if requested_base != resolved_base:
            raise ModelResolutionError(
                f"requested model '{requested}' but the gateway resolved "
                f"'{resolved}'; fallback is disabled for benchmark runs"
            )


def build_default_registry(enable_live_providers: bool = False) -> ModelRegistry:
    """The walking-skeleton registry: three deterministic mocks.

    Live providers are additive — an extra descriptor and an extra ``model_list``
    entry in the proxy config. No application code changes, which is the only
    meaningful test of "provider-independent".
    """
    registry = ModelRegistry(allow_fallback=False)
    for name in MOCK_MODEL_NAMES:
        registry.register(
            ModelDescriptor(
                logical_name=name,
                gateway_model=name,
                vendor="mock",
                endpoint="litellm-proxy",
                is_mock=True,
                max_retries=0,
                requires_credentials=False,
            )
        )

    if enable_live_providers:
        # Deliberately minimal: the brief says not to add live models yet. This
        # is the seam that shows the registry is provider-independent, nothing more.
        registry.register(
            ModelDescriptor(
                logical_name="live-primary",
                gateway_model="live-primary",
                vendor="configured-live",
                endpoint="litellm-proxy",
                is_mock=False,
                max_retries=0,
                requires_credentials=True,
            )
        )

    return registry
