"""OpenTelemetry spans, exported to Phoenix.

OpenTelemetry owns span plumbing, batching and the wire protocol; Phoenix owns
storage and the viewer. We own the span tree's *shape* and which artifacts are
recorded (ADR-0010).

Two things worth knowing about the design:

* **Only observable artifacts are recorded** — exit codes, counters, durations,
  content hashes, decision records. No attempt is made to store or reconstruct
  private model chain-of-thought.
* **A local span ledger runs alongside the exporter.** OTLP export is
  fire-and-forget, so a dropped span is invisible. The ``required_artifacts_present``
  gate consults the ledger rather than trusting the collector; otherwise a
  network hiccup would silently satisfy an artifact gate.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.models.blinding import IdentityLeakError, find_identity_leaks
from app.telemetry.redaction import redact_attributes

ROOT_SPAN_NAME = "coding-evaluation"

CHILD_SPAN_NAMES: tuple[str, ...] = (
    "validate-specification",
    "inspect-repository",
    "generate-hypotheses",
    "design-probes",
    "execute-probes",
    "establish-diagnosis",
    "generate-repair-candidates",
    "apply-patch",
    "run-build",
    "run-tests",
    "run-property-tests",
    "apply-reliability-gates",
    "produce-report",
)


@dataclass
class SpanLedger:
    """In-process record of every span this run opened.

    The gate's source of truth for "were the required artifacts produced?", since
    a successful export cannot be confirmed from inside the process.
    """

    entries: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def record(self, name: str, attributes: dict[str, Any]) -> None:
        self.entries.append((name, attributes))

    @property
    def names(self) -> frozenset[str]:
        return frozenset(name for name, _ in self.entries)

    def attributes_for(self, name: str) -> dict[str, Any]:
        for entry_name, attributes in self.entries:
            if entry_name == name:
                return attributes
        return {}


_provider: TracerProvider | None = None


def configure_tracing(
    *, endpoint: str | None, project_name: str, service_name: str = "reliability-walking-skeleton"
) -> TracerProvider:
    """Configure the tracer provider once per process.

    With no endpoint, spans are still created (so the ledger and the span tree
    are exercised) but nothing is exported. That keeps `make test` free of any
    service dependency without changing the code path under test.
    """
    global _provider
    if _provider is not None:
        return _provider

    resource = Resource.create(
        {"service.name": service_name, "openinference.project.name": project_name}
    )
    provider = TracerProvider(resource=resource)

    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces"))
        )

    trace.set_tracer_provider(provider)
    _provider = provider
    return provider


def reset_tracing_for_tests() -> None:
    """Drop the cached provider so a test can reconfigure."""
    global _provider
    _provider = None


def get_tracer(name: str = "app.telemetry"):
    return trace.get_tracer(name)


@contextmanager
def span(
    name: str,
    ledger: SpanLedger,
    attributes: dict[str, Any] | None = None,
) -> Iterator[Any]:
    """Open a span, redact its attributes, and record it in the ledger.

    Attributes are checked for real model identities before export. Blinding that
    holds in prompts but leaks in a span attribute is not blinding — the trace
    store is just a slower way to publish the mapping.
    """
    cleaned = redact_attributes(attributes or {})

    for key, value in cleaned.items():
        if isinstance(value, str) and find_identity_leaks(value):
            raise IdentityLeakError(
                f"span attribute '{key}' on '{name}' contains a real model identity"
            )

    ledger.record(name, cleaned)

    tracer = get_tracer()
    with tracer.start_as_current_span(name) as active_span:
        for key, value in cleaned.items():
            active_span.set_attribute(key, value)
        yield active_span


def current_trace_id() -> str | None:
    """Hex trace id of the active span, for cross-referencing in Phoenix."""
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return None
    return format(context.trace_id, "032x")


def force_flush(timeout_millis: int = 5000) -> bool:
    """Flush pending spans. Called before a run reports its trace id."""
    if _provider is None:
        return False
    return _provider.force_flush(timeout_millis)
