from __future__ import annotations

import asyncio
import math
import os
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import httpx

from eval_lab.schema import (
    ExecutionStatus,
    JudgePrediction,
    JudgeRecord,
    JudgmentMode,
    PairwiseLabel,
)

DEFAULT_URL = "https://opencode.ai/zen/v1/systemone"
DEFAULT_MODEL = "jev-1.13-free"
DIRECT_PROTOCOL = "jev-direct-v1"
ATOMIC_PROTOCOL = "jev-atomic-v1"


class JevError(RuntimeError):
    """Base class for provider and response failures without secret-bearing state."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


class JevRateLimitError(JevError):
    """The provider rejected the request because the current quota is exhausted."""


class JevProviderError(JevError):
    """A transport or HTTP provider failure."""


class JevParseError(JevError):
    """The provider returned a payload that cannot be normalized."""


def parse_retry_after(value: str | None) -> float | None:
    """Parse Retry-After seconds or an HTTP date into non-negative seconds."""

    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return max(0.0, (parsed - datetime.now(UTC)).total_seconds())


async def evaluate_jev(
    state: str | dict[str, Any] | list[Any],
    questions: dict[str, Any],
    *,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    base_url: str = DEFAULT_URL,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Call OpenCode Zen's Jev System One endpoint and return its JSON payload."""

    if model != DEFAULT_MODEL:
        raise ValueError(f"TASK-0003 requires model {DEFAULT_MODEL!r}; no paid fallback is allowed")
    key = api_key or os.getenv("OPENCODE_API_KEY")
    if not key:
        raise RuntimeError("Set OPENCODE_API_KEY before calling Jev.")

    payload = {"model": DEFAULT_MODEL, "state": state, "questions": questions}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(base_url, headers=headers, json=payload)
    except httpx.RequestError as exc:
        raise JevProviderError("Jev request failed before receiving a response") from exc

    if response.status_code == 429:
        raise JevRateLimitError(
            "Jev provider rate limit",
            status_code=429,
            retry_after_seconds=parse_retry_after(response.headers.get("Retry-After")),
        )
    if response.status_code >= 400:
        raise JevProviderError(
            f"Jev provider returned HTTP {response.status_code}",
            status_code=response.status_code,
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise JevParseError(
            "Jev provider returned invalid JSON", status_code=response.status_code
        ) from exc
    if not isinstance(payload, dict):
        raise JevParseError(
            "Jev provider JSON payload must be an object", status_code=response.status_code
        )
    return payload


def _state_for_record(record: JudgeRecord) -> str:
    state = f"User prompt: {record.prompt}\nCandidate A: {record.candidate_a}"
    if record.mode is JudgmentMode.PAIRWISE:
        state += f"\nCandidate B: {record.candidate_b}"
    return state


def _choice_criteria(record: JudgeRecord) -> dict[str, str]:
    if record.mode is JudgmentMode.SINGLE:
        return {
            "pass": "The candidate is objectively correct.",
            "fail": "The candidate is objectively incorrect.",
        }
    return {
        PairwiseLabel.A.value: "Candidate A is better or more correct.",
        PairwiseLabel.B.value: "Candidate B is better or more correct.",
        PairwiseLabel.TIE.value: "The candidates are objectively equivalent.",
    }


def build_direct_request(record: JudgeRecord) -> dict[str, Any]:
    """Build the typed direct protocol request for one canonical record."""

    return {
        "state": _state_for_record(record),
        "questions": {
            "verdict": {
                "type": "choice",
                "instructions": "Return the single objective verdict for the candidate record.",
                "criteria": _choice_criteria(record),
            }
        },
    }


def build_atomic_request(record: JudgeRecord) -> dict[str, Any]:
    """Build criterion-level questions whose aggregation remains local and deterministic."""

    criteria: dict[str, Any] = {}
    for criterion in record.rubric:
        criteria[criterion.criterion_id] = {
            "type": "noul" if record.mode is JudgmentMode.SINGLE else "choice",
            "instructions": criterion.description,
            "criteria": _choice_criteria(record),
        }
    return {"state": _state_for_record(record), "questions": criteria}


def _nested_values(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    values = [payload]
    for key in ("result", "data", "output", "response", "answer"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            values.append(value)
    return values


def _find_first(payload: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for candidate in _nested_values(payload):
        for key in keys:
            if key in candidate:
                return candidate[key]
    return None


def _normalize_label(value: Any, mode: JudgmentMode) -> str:
    if isinstance(value, bool):
        if mode is not JudgmentMode.SINGLE:
            raise JevParseError("boolean labels are only valid for single judgments")
        return "pass" if value else "fail"
    text = str(value).strip()
    lowered = text.lower()
    if mode is JudgmentMode.SINGLE:
        if lowered in {"pass", "correct", "true", "yes", "1"}:
            return "pass"
        if lowered in {"fail", "incorrect", "false", "no", "0"}:
            return "fail"
    else:
        if text.upper() in {item.value for item in PairwiseLabel}:
            return text.upper()
    raise JevParseError(f"unrecognized {mode.value} Jev label")


def _normalize_probability_map(value: Any, mode: JudgmentMode) -> dict[str, float] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping) or not value:
        raise JevParseError("Jev probabilities must be a non-empty object")
    normalized: dict[str, float] = {}
    for key, raw in value.items():
        try:
            number = float(raw)
        except (TypeError, ValueError) as exc:
            raise JevParseError("Jev probabilities must be numeric") from exc
        if not math.isfinite(number):
            raise JevParseError("Jev probabilities must be finite")
        label = _normalize_label(key, mode)
        normalized[label] = number
    try:
        return JudgePrediction(
            record_id="probability-check",
            judge_id="jev",
            protocol_version="check",
            label="pass" if mode is JudgmentMode.SINGLE else PairwiseLabel.A.value,
            probabilities=normalized,
        ).probabilities
    except Exception as exc:
        raise JevParseError("Jev probabilities must sum to one") from exc


def _extract_direct_label(payload: Mapping[str, Any], mode: JudgmentMode) -> str:
    value = _find_first(
        payload, ("label", "verdict", "prediction", "choice", "class", "is_correct")
    )
    if value is None:
        raise JevParseError("Jev direct response has no label")
    if isinstance(value, Mapping):
        value = _find_first(value, ("label", "verdict", "prediction", "choice", "class", "value"))
    return _normalize_label(value, mode)


def _extract_direct_probabilities(
    payload: Mapping[str, Any], mode: JudgmentMode
) -> dict[str, float] | None:
    value = _find_first(payload, ("probabilities", "probability_map", "probs"))
    return _normalize_probability_map(value, mode)


def _provider_metadata(protocol_version: str) -> dict[str, str]:
    return {
        "provider": "opencode-zen",
        "model": DEFAULT_MODEL,
        "protocol_version": protocol_version,
    }


def normalize_direct_response(
    response: Mapping[str, Any],
    record: JudgeRecord,
    *,
    latency_ms: float | None = None,
) -> JudgePrediction:
    """Normalize a direct Jev response into the canonical prediction schema."""

    label = _extract_direct_label(response, record.mode)
    probabilities = _extract_direct_probabilities(response, record.mode)
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=DEFAULT_MODEL,
        protocol_version=DIRECT_PROTOCOL,
        label=label,
        probabilities=probabilities,
        execution_status=ExecutionStatus.OK,
        latency_ms=latency_ms,
        provider_metadata=_provider_metadata(DIRECT_PROTOCOL),
    )


def _criterion_payloads(response: Mapping[str, Any]) -> Mapping[str, Any]:
    criteria = _find_first(response, ("criteria", "criterion_results", "answers", "results"))
    if not isinstance(criteria, Mapping):
        raise JevParseError("Jev atomic response has no criterion results")
    return criteria


def _criterion_result(value: Any, mode: JudgmentMode) -> tuple[str, dict[str, float] | None]:
    if isinstance(value, Mapping):
        label_value = _find_first(
            value, ("label", "verdict", "prediction", "choice", "value", "is_correct")
        )
        probabilities = _normalize_probability_map(
            _find_first(value, ("probabilities", "probability_map", "probs")), mode
        )
    else:
        label_value = value
        probabilities = None
    if label_value is None:
        raise JevParseError("Jev atomic criterion has no label")
    return _normalize_label(label_value, mode), probabilities


def _aggregate_atomic(
    response: Mapping[str, Any],
    record: JudgeRecord,
) -> tuple[str, dict[str, float] | None, dict[str, str]]:
    payloads = _criterion_payloads(response)
    labels: dict[str, str] = {}
    probability_maps: list[dict[str, float]] = []
    for criterion in record.rubric:
        if criterion.criterion_id not in payloads:
            raise JevParseError(f"missing atomic criterion {criterion.criterion_id}")
        label, criterion_probabilities = _criterion_result(
            payloads[criterion.criterion_id], record.mode
        )
        labels[criterion.criterion_id] = label
        if criterion_probabilities is not None:
            probability_maps.append(criterion_probabilities)

    if record.mode is JudgmentMode.SINGLE:
        label = "pass" if all(value == "pass" for value in labels.values()) else "fail"
        classes: tuple[str, ...] = ("pass", "fail")
    else:
        unique = set(labels.values())
        label = unique.pop() if len(unique) == 1 else PairwiseLabel.TIE.value
        classes = tuple(item.value for item in PairwiseLabel)

    probabilities: dict[str, float] | None = None
    if probability_maps and len(probability_maps) == len(labels):
        probabilities = {
            key: sum(item.get(key, 0.0) for item in probability_maps) / len(probability_maps)
            for key in classes
        }
        total = sum(probabilities.values())
        probabilities = {key: value / total for key, value in probabilities.items()}
    return label, probabilities, labels


def normalize_atomic_response(
    response: Mapping[str, Any],
    record: JudgeRecord,
    *,
    latency_ms: float | None = None,
) -> JudgePrediction:
    """Normalize criterion-level Jev results using deterministic local aggregation."""

    label, probabilities, criterion_labels = _aggregate_atomic(response, record)
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=DEFAULT_MODEL,
        protocol_version=ATOMIC_PROTOCOL,
        label=label,
        probabilities=probabilities,
        execution_status=ExecutionStatus.OK,
        latency_ms=latency_ms,
        provider_metadata={
            **_provider_metadata(ATOMIC_PROTOCOL),
            "criterion_labels": criterion_labels,
        },
    )


def _error_prediction(
    record: JudgeRecord,
    protocol_version: str,
    status: ExecutionStatus,
    *,
    latency_ms: float,
    error_type: str,
    status_code: int | None = None,
    retry_after_seconds: float | None = None,
) -> JudgePrediction:
    error: dict[str, Any] = {"type": error_type}
    if status_code is not None:
        error["status_code"] = status_code
    if retry_after_seconds is not None:
        error["retry_after_seconds"] = retry_after_seconds
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=DEFAULT_MODEL,
        protocol_version=protocol_version,
        execution_status=status,
        latency_ms=latency_ms,
        provider_metadata=_provider_metadata(protocol_version),
        error=error,
    )


async def run_jev(
    records: Sequence[JudgeRecord],
    *,
    protocol_version: str = DIRECT_PROTOCOL,
    api_key: str | None = None,
    base_url: str = DEFAULT_URL,
    timeout: float = 30.0,
) -> list[JudgePrediction]:
    """Run canonical records sequentially and preserve every provider execution state."""

    if protocol_version not in {DIRECT_PROTOCOL, ATOMIC_PROTOCOL}:
        raise ValueError(f"unsupported Jev protocol: {protocol_version}")
    normalizer = (
        normalize_direct_response
        if protocol_version == DIRECT_PROTOCOL
        else normalize_atomic_response
    )
    builder = build_direct_request if protocol_version == DIRECT_PROTOCOL else build_atomic_request
    predictions: list[JudgePrediction] = []
    for record in records:
        started = time.perf_counter()
        try:
            request = builder(record)
            response = await evaluate_jev(
                request["state"],
                request["questions"],
                model=DEFAULT_MODEL,
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
            )
            predictions.append(
                normalizer(response, record, latency_ms=(time.perf_counter() - started) * 1000)
            )
        except JevRateLimitError as exc:
            predictions.append(
                _error_prediction(
                    record,
                    protocol_version,
                    ExecutionStatus.RATE_LIMITED,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    error_type="rate_limited",
                    status_code=exc.status_code,
                    retry_after_seconds=exc.retry_after_seconds,
                )
            )
        except JevProviderError as exc:
            predictions.append(
                _error_prediction(
                    record,
                    protocol_version,
                    ExecutionStatus.PROVIDER_ERROR,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    error_type="provider_error",
                    status_code=exc.status_code,
                )
            )
        except (JevParseError, ValueError, TypeError):
            predictions.append(
                _error_prediction(
                    record,
                    protocol_version,
                    ExecutionStatus.PARSE_ERROR,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    error_type="parse_error",
                )
            )
        except RuntimeError:
            predictions.append(
                _error_prediction(
                    record,
                    protocol_version,
                    ExecutionStatus.PROVIDER_ERROR,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    error_type="configuration_error",
                )
            )
    return predictions


def write_predictions_jsonl(predictions: Sequence[JudgePrediction], path: str | Path) -> None:
    """Write normalized predictions without raw provider payloads or credentials."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(prediction.model_dump_json() + "\n" for prediction in predictions),
        encoding="utf-8",
    )


def run_jev_sync(
    records: Sequence[JudgeRecord],
    **kwargs: Any,
) -> list[JudgePrediction]:
    """Synchronous convenience wrapper for the deterministic runner."""

    return asyncio.run(run_jev(records, **kwargs))


__all__ = [
    "ATOMIC_PROTOCOL",
    "DEFAULT_MODEL",
    "DEFAULT_URL",
    "DIRECT_PROTOCOL",
    "JevError",
    "JevParseError",
    "JevProviderError",
    "JevRateLimitError",
    "build_atomic_request",
    "build_direct_request",
    "evaluate_jev",
    "normalize_atomic_response",
    "normalize_direct_response",
    "parse_retry_after",
    "run_jev",
    "run_jev_sync",
    "write_predictions_jsonl",
]
