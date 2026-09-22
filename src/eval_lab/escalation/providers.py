"""Provider adapters that preserve typed semantics and failure states."""

from __future__ import annotations

import json
import math
import os
import re
import threading
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx

from eval_lab.escalation.spec import build_decision_spec
from eval_lab.schema import (
    ExecutionStatus,
    JudgePrediction,
    JudgeRecord,
    JudgmentMode,
    PairwiseLabel,
)

OPENROUTER_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
OPENROUTER_PINNED_MODEL = "typesafe/jev-1.13"
OPENROUTER_ROLLING_MODEL = "~typesafe/jev-latest"
YOLO_AUTO_BASE_URL = "https://api.yolo-auto.com/v1"
YOLO_QWEN_MODEL = "qwen3.8-flash"
SYSTEM_ONE_PROTOCOL = "eval-lab-system-one-v1"


def _nested(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    values = [payload]
    for key in ("result", "data", "output", "response", "answer", "answers", "message"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            values.append(value)
    choices = payload.get("choices")
    if isinstance(choices, Sequence) and choices and isinstance(choices[0], Mapping):
        values.append(choices[0])
        message = choices[0].get("message")
        if isinstance(message, Mapping):
            values.append(message)
    return values


def _find(payload: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for item in _nested(payload):
        for key in keys:
            if key in item:
                return item[key]
    return None


def _labels(record: JudgeRecord) -> tuple[str, ...]:
    return ("pass", "fail") if record.mode is JudgmentMode.SINGLE else tuple(item.value for item in PairwiseLabel)


def _normalize_label(value: Any, record: JudgeRecord) -> str:
    if isinstance(value, Mapping):
        value = _find(value, ("label", "verdict", "prediction", "choice", "value", "is_correct"))
    if isinstance(value, bool):
        if record.mode is not JudgmentMode.SINGLE:
            raise ValueError("boolean label is invalid for pairwise records")
        return "pass" if value else "fail"
    text = str(value).strip()
    if record.mode is JudgmentMode.SINGLE:
        if text.lower() in {"pass", "correct", "true", "yes", "1"}:
            return "pass"
        if text.lower() in {"fail", "incorrect", "false", "no", "0"}:
            return "fail"
    elif text.upper() in {item.value for item in PairwiseLabel}:
        return text.upper()
    raise ValueError("provider response contained an illegal label")


def _probabilities(value: Any, record: JudgeRecord) -> dict[str, float] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise TypeError("provider probabilities must be an object")
    output: dict[str, float] = {}
    for key, raw in value.items():
        label = _normalize_label(key, record)
        number = float(raw)
        if not math.isfinite(number) or number < 0:
            raise ValueError("provider probabilities must be finite and non-negative")
        output[label] = number
    total = sum(output.values())
    if not total:
        raise ValueError("provider probabilities must have positive mass")
    legal = _labels(record)
    normalized = {label: output.get(label, 0.0) / total for label in legal}
    if not math.isclose(sum(normalized.values()), 1.0, abs_tol=1e-6):
        raise ValueError("provider probabilities failed normalization")
    return normalized


def normalize_typed_response(
    payload: Mapping[str, Any],
    record: JudgeRecord,
    *,
    provider: str,
    model: str,
    latency_ms: float | None = None,
) -> JudgePrediction:
    """Normalize provider JSON or OpenAI message content into the canonical schema."""

    content = _find(payload, ("content", "text"))
    if isinstance(content, str):
        try:
            decoded = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, flags=re.DOTALL)
            if match:
                try:
                    decoded = json.loads(match.group(0))
                except json.JSONDecodeError:
                    decoded = {"label": content}
            else:
                decoded = {"label": content}
        if isinstance(decoded, Mapping):
            payload = decoded
    value = _find(payload, ("label", "verdict", "prediction", "choice", "class", "is_correct"))
    if value is None:
        raise ValueError("provider response has no typed verdict")
    label = _normalize_label(value, record)
    probabilities = _probabilities(_find(payload, ("probabilities", "probability_map", "probs")), record)
    metadata: dict[str, Any] = {
        "provider": provider,
        "model": model,
        "typed_spec_id": "eval-lab-system-one",
        "typed_spec_version": "0.1.0",
        "wire_protocol": SYSTEM_ONE_PROTOCOL,
    }
    usage = _find(payload, ("usage",))
    if isinstance(usage, Mapping):
        metadata["usage"] = {
            str(key): float(value) if isinstance(value, (int, float)) else str(value)
            for key, value in usage.items()
            if isinstance(value, (int, float, str))
        }
    resolved_model = _find(payload, ("model",))
    if resolved_model is not None:
        metadata["resolved_model"] = str(resolved_model)
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=model,
        protocol_version=SYSTEM_ONE_PROTOCOL,
        label=label,
        probabilities=probabilities,
        execution_status=ExecutionStatus.OK,
        latency_ms=latency_ms,
        provider_metadata=metadata,
    )


def error_prediction(
    record: JudgeRecord,
    *,
    provider: str,
    model: str,
    status: ExecutionStatus,
    latency_ms: float,
    error_type: str,
    status_code: int | None = None,
) -> JudgePrediction:
    error: dict[str, Any] = {"type": error_type}
    if status_code is not None:
        error["status_code"] = status_code
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=model,
        protocol_version=SYSTEM_ONE_PROTOCOL,
        execution_status=status,
        latency_ms=latency_ms,
        provider_metadata={
            "provider": provider,
            "model": model,
            "typed_spec_id": "eval-lab-system-one",
            "typed_spec_version": "0.1.0",
            "wire_protocol": SYSTEM_ONE_PROTOCOL,
        },
        error=error,
    )


def _run_http(
    records: Sequence[JudgeRecord],
    *,
    url: str,
    model: str,
    api_key: str | None,
    provider: str,
    headers: Mapping[str, str],
    payload_builder: Any,
    client: httpx.Client | None,
    timeout: float,
) -> list[JudgePrediction]:
    if not api_key:
        return [
            error_prediction(
                record,
                provider=provider,
                model=model,
                status=ExecutionStatus.SKIPPED,
                latency_ms=0.0,
                error_type="missing_api_key",
            )
            for record in records
        ]
    owned = client is None
    session = client
    thread_state = threading.local()

    def evaluate_one(record: JudgeRecord) -> JudgePrediction:
        local_session = session
        if local_session is None:
            local_session = getattr(thread_state, "client", None)
            if local_session is None:
                local_session = httpx.Client(timeout=timeout)
                thread_state.client = local_session
        started = time.perf_counter()
        try:
            response = local_session.post(
                url,
                headers={**headers, "Authorization": f"Bearer {api_key}"},
                json=payload_builder(record),
            )
            latency = (time.perf_counter() - started) * 1000.0
            if response.status_code == 429:
                status = ExecutionStatus.RATE_LIMITED
                error_type = "rate_limited"
            elif response.status_code >= 400:
                status = ExecutionStatus.PROVIDER_ERROR
                error_type = "provider_error"
            else:
                try:
                    return normalize_typed_response(
                        response.json(),
                        record,
                        provider=provider,
                        model=model,
                        latency_ms=latency,
                    )
                except (ValueError, TypeError, json.JSONDecodeError):
                    status = ExecutionStatus.PARSE_ERROR
                    error_type = "parse_error"
            return error_prediction(
                record,
                provider=provider,
                model=model,
                status=status,
                latency_ms=latency,
                error_type=error_type,
                status_code=response.status_code,
            )
        except httpx.RequestError:
            return error_prediction(
                record,
                provider=provider,
                model=model,
                status=ExecutionStatus.PROVIDER_ERROR,
                latency_ms=(time.perf_counter() - started) * 1000.0,
                error_type="transport_error",
            )

    workers = max(1, int(os.getenv("EVAL_LAB_PROVIDER_WORKERS", "8")))
    if owned and len(records) > 1 and workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            predictions = list(executor.map(evaluate_one, records))
    else:
        predictions = [evaluate_one(record) for record in records]
    return predictions


def run_openrouter_jev(
    records: Sequence[JudgeRecord],
    *,
    model: str = OPENROUTER_PINNED_MODEL,
    api_key: str | None = None,
    url: str = OPENROUTER_DECISIONS_URL,
    client: httpx.Client | None = None,
    timeout: float = 60.0,
    label_orders: Mapping[str, Sequence[str]] | None = None,
    instruction_overrides: Mapping[str, str] | None = None,
) -> list[JudgePrediction]:
    """Run a single isolated pinned or rolling Jev arm."""

    if model not in {OPENROUTER_PINNED_MODEL, OPENROUTER_ROLLING_MODEL}:
        raise ValueError("OpenRouter Jev model must be the pinned ID or the separate rolling alias")
    key = api_key or os.getenv("OPENROUTER_API_KEY")

    def payload(record: JudgeRecord) -> dict[str, Any]:
        spec = build_decision_spec(
            record,
            label_order=(label_orders or {}).get(record.record_id),
            instruction_override=(instruction_overrides or {}).get(record.record_id),
        )
        return {"model": model, **spec.provider_payload(), "spec_id": spec.spec_id, "spec_version": spec.spec_version}

    return _run_http(
        records,
        url=url,
        model=model,
        api_key=key,
        provider="openrouter",
        headers={"Content-Type": "application/json"},
        payload_builder=payload,
        client=client,
        timeout=timeout,
    )


def run_yolo_qwen(
    records: Sequence[JudgeRecord],
    *,
    model: str = YOLO_QWEN_MODEL,
    api_key: str | None = None,
    base_url: str = YOLO_AUTO_BASE_URL,
    client: httpx.Client | None = None,
    timeout: float = 60.0,
    label_orders: Mapping[str, Sequence[str]] | None = None,
    instruction_overrides: Mapping[str, str] | None = None,
) -> list[JudgePrediction]:
    """Run YOLO-Auto's OpenAI-compatible Qwen arm with explicit failure states."""

    if model != YOLO_QWEN_MODEL:
        raise ValueError(f"YOLO-Auto task arm requires {YOLO_QWEN_MODEL!r}")
    key = api_key or os.getenv("YOLO_AUTO_API_KEY") or os.getenv("YOLO_API_KEY") or os.getenv("QWEN_API_KEY")

    def payload(record: JudgeRecord) -> dict[str, Any]:
        spec = build_decision_spec(
            record,
            label_order=(label_orders or {}).get(record.record_id),
            instruction_override=(instruction_overrides or {}).get(record.record_id),
        )
        typed = json.dumps(spec.provider_payload(), sort_keys=True)
        return {
            "model": model,
            "messages": [
                {"role": "system", "content": "Return a JSON object with a legal label."},
                {"role": "user", "content": typed},
            ],
            "temperature": 0,
        }

    return _run_http(
        records,
        url=f"{base_url.rstrip('/')}/chat/completions",
        model=model,
        api_key=key,
        provider="yolo-auto",
        headers={"Content-Type": "application/json"},
        payload_builder=payload,
        client=client,
        timeout=timeout,
    )


__all__ = [
    "OPENROUTER_DECISIONS_URL",
    "OPENROUTER_PINNED_MODEL",
    "OPENROUTER_ROLLING_MODEL",
    "SYSTEM_ONE_PROTOCOL",
    "YOLO_AUTO_BASE_URL",
    "YOLO_QWEN_MODEL",
    "error_prediction",
    "normalize_typed_response",
    "run_openrouter_jev",
    "run_yolo_qwen",
]
