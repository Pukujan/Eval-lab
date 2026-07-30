"""Phoenix / OpenTelemetry instrumentation smoke test.

Span *creation* and the tree shape are checked without any collector, so this runs
everywhere. Actually reaching a Phoenix server is a separate, skippable test —
"we produced the spans" and "the collector received them" are different claims and
must not be conflated.
"""

from __future__ import annotations

import httpx
import pytest

from app.config import load_settings
from app.reliability.gates import GATE_REQUIRED_SPAN_NAMES, REQUIRED_SPAN_NAMES
from app.telemetry.redaction import (
    REDACTED,
    content_fingerprint,
    is_sensitive_key,
    redact_attributes,
)
from app.telemetry.tracing import (
    CHILD_SPAN_NAMES,
    ROOT_SPAN_NAME,
    SpanLedger,
    configure_tracing,
    span,
)


def test_required_span_tree_is_fully_declared() -> None:
    assert REQUIRED_SPAN_NAMES == {ROOT_SPAN_NAME, *CHILD_SPAN_NAMES}
    assert len(CHILD_SPAN_NAMES) == 13


def test_gate_requirement_excludes_only_the_report_span() -> None:
    """`produce-report` cannot have completed when the decision is made."""
    assert REQUIRED_SPAN_NAMES - GATE_REQUIRED_SPAN_NAMES == {"produce-report"}


def test_spans_are_created_and_recorded_without_a_collector() -> None:
    configure_tracing(endpoint=None, project_name="test")
    ledger = SpanLedger()

    with span(ROOT_SPAN_NAME, ledger, {"evaluation.run_id": "run-x"}):
        for name in CHILD_SPAN_NAMES:
            with span(name, ledger, {"investigation.node": name}):
                pass

    assert ledger.names == REQUIRED_SPAN_NAMES
    assert ledger.attributes_for(ROOT_SPAN_NAME)["evaluation.run_id"] == "run-x"


def test_span_attributes_are_redacted() -> None:
    configure_tracing(endpoint=None, project_name="test")
    ledger = SpanLedger()

    with span(
        "run-build",
        ledger,
        {"api_key": "sk-abcdef1234567890", "note": "token sk-secretvalue123 inline"},
    ):
        pass

    attributes = ledger.attributes_for("run-build")
    assert attributes["api_key"] == REDACTED
    assert "sk-secretvalue123" not in attributes["note"]


def test_span_attributes_naming_a_real_model_are_refused() -> None:
    """Blinding that holds in prompts but leaks in a span is not blinding."""
    from app.models.blinding import IdentityLeakError

    configure_tracing(endpoint=None, project_name="test")
    ledger = SpanLedger()

    with pytest.raises(IdentityLeakError):
        with span("generate-hypotheses", ledger, {"model.name": "claude-opus"}):
            pass


def test_sensitive_key_detection() -> None:
    for key in ("api_key", "OPENAI_API_KEY", "authorization", "db_password", "secret_token"):
        assert is_sensitive_key(key)
    for key in ("evaluation.run_id", "build.exit_code", "effect_count"):
        assert not is_sensitive_key(key)


def test_prompts_are_recorded_as_fingerprints_not_raw_text() -> None:
    """A pasted credential must not be able to land in the trace store."""
    fingerprint = content_fingerprint("please do the thing sk-verysecret")
    assert set(fingerprint) == {"content.sha256", "content.length"}
    assert "sk-verysecret" not in str(fingerprint)
    assert len(fingerprint["content.sha256"]) == 64


def test_redaction_preserves_non_sensitive_values() -> None:
    cleaned = redact_attributes({"build.exit_code": 0, "gate": "not_symptom_suppression"})
    assert cleaned == {"build.exit_code": 0, "gate": "not_symptom_suppression"}


@pytest.mark.integration
def test_spans_reach_a_running_phoenix() -> None:
    """Requires a Phoenix server; skipped (not failed) when unreachable."""
    settings = load_settings()
    endpoint = settings.phoenix_endpoint or "http://localhost:6006"

    try:
        response = httpx.get(f"{endpoint.rstrip('/')}/healthz", timeout=3.0)
        reachable = response.status_code == 200
    except (httpx.HTTPError, OSError):
        reachable = False

    if not reachable:
        pytest.skip(f"Phoenix not reachable at {endpoint}; trace export not verified here")

    from app.telemetry.tracing import force_flush, reset_tracing_for_tests

    reset_tracing_for_tests()
    configure_tracing(endpoint=endpoint, project_name=settings.phoenix_project_name)
    ledger = SpanLedger()
    with span(ROOT_SPAN_NAME, ledger, {"evaluation.run_id": "phoenix-smoke"}):
        with span("run-build", ledger, {"build.exit_code": 0}):
            pass

    assert force_flush(timeout_millis=5000)
