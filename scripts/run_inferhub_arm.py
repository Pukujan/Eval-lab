"""Run one bounded, checkpointed streaming InferHub arm."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
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

EXPERIMENT_ID = "EXP-20260922-023-inferhub-wave"
SOURCE_POOL = Path("experiments") / "EXP-20260921-015-grok-luna-qwen-bakeoff"
PROTOCOL = "eval-lab-system-one-v1"


def _load_dotenv(path: Path | None) -> dict[str, str]:
    values: dict[str, str] = {}
    if path is None or not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _load_records(pool: Path, partition: str, limit: int) -> list[JudgeRecord]:
    rows = [
        json.loads(line)
        for line in (pool / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected = [row for row in rows if partition == "all" or row["partition"] == partition]
    if limit:
        selected = selected[:limit]
    records = [JudgeRecord.model_validate(row["record"]) for row in selected]
    if not records or len({record.record_id for record in records}) != len(records):
        raise ValueError("selected pool is empty or contains duplicate record IDs")
    return records


def _legal_labels(record: JudgeRecord) -> set[str]:
    if record.mode is JudgmentMode.SINGLE:
        return {"pass", "fail"}
    return {item.value for item in PairwiseLabel}


def build_prompt(record: JudgeRecord) -> str:
    decision = build_decision_spec(record)
    labels = ", ".join(decision.legal_labels)
    payload = {"record_id": decision.record_id, **decision.provider_payload()}
    return (
        "You are a strictly typed objective evaluation judge. "
        f"Return exactly one JSON object with label set to one of [{labels}]. "
        "Do not include explanation, markdown, or additional keys.\n\n"
        + json.dumps(payload, sort_keys=True)
    )


def _json_fragments(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    fragments: list[dict[str, Any]] = []
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            fragments.append(value)
    return fragments


def parse_label(text: str, record: JudgeRecord) -> str | None:
    """Extract a legal label from JSON or a conservative plain-text fallback."""

    legal = _legal_labels(record)
    for fragment in _json_fragments(text):
        for key in ("label", "verdict", "prediction", "choice", "class", "value"):
            value = fragment.get(key)
            if isinstance(value, dict):
                value = next((value.get(name) for name in ("label", "choice", "value") if name in value), None)
            if value is None:
                continue
            candidate = str(value).strip()
            normalized = candidate.upper() if record.mode is JudgmentMode.PAIRWISE else candidate.lower()
            if normalized in legal:
                return normalized
    normalized_text = text.upper() if record.mode is JudgmentMode.PAIRWISE else text.lower()
    pattern = r"\b(?:A|B|TIE)\b" if record.mode is JudgmentMode.PAIRWISE else r"\b(?:pass|fail)\b"
    for token in reversed(re.findall(pattern, normalized_text)):
        candidate = token if record.mode is JudgmentMode.PAIRWISE else token.lower()
        if candidate in legal:
            return candidate
    return None


def parse_sse(lines: list[str]) -> tuple[str, list[str], dict[str, int | float]]:
    """Collect content, surfaced model IDs, and usage from OpenAI SSE lines."""

    content: list[str] = []
    surfaced: set[str] = set()
    usage: dict[str, int | float] = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            continue
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        model = event.get("model")
        if isinstance(model, str) and model:
            surfaced.add(model)
        event_usage = event.get("usage")
        if isinstance(event_usage, dict):
            for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cost"):
                if isinstance(event_usage.get(key), (int, float)) and not isinstance(event_usage.get(key), bool):
                    usage[key] = event_usage[key]
        for choice in event.get("choices", []):
            if not isinstance(choice, dict):
                continue
            delta = choice.get("delta") or choice.get("message") or {}
            if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                content.append(delta["content"])
    return "".join(content), sorted(surfaced), usage


def _error_prediction(
    record: JudgeRecord,
    *,
    model: str,
    status: ExecutionStatus,
    started: float,
    error: dict[str, Any],
    metadata: dict[str, Any],
) -> JudgePrediction:
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=model,
        protocol_version=PROTOCOL,
        execution_status=status,
        latency_ms=(time.perf_counter() - started) * 1000.0,
        provider_metadata=metadata,
        error=error,
    )


def _evaluate(record: JudgeRecord, args: argparse.Namespace, api_key: str, api_url: str) -> JudgePrediction:
    started = time.perf_counter()
    metadata: dict[str, Any] = {
        "provider": "inferhub",
        "arm_id": args.arm_id or args.model,
        "requested_model": args.model,
        "route": "inferhub_openai_chat_completions",
        "streaming": True,
        "stream_format": "openai-sse",
        "max_tokens": args.max_tokens,
        "typed_spec_id": "eval-lab-system-one",
        "typed_spec_version": "0.1.0",
    }
    if not api_key:
        return _error_prediction(
            record,
            model=args.model,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"type": "missing_api_key"},
            metadata=metadata,
        )
    request = {
        "model": args.model,
        "messages": [{"role": "user", "content": build_prompt(record)}],
        "max_tokens": args.max_tokens,
        "temperature": 0,
        "stream": True,
    }
    try:
        with httpx.Client(timeout=args.timeout) as client, client.stream(
            "POST",
            f"{api_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=request,
        ) as response:
            metadata["http_status"] = response.status_code
            metadata["rate_limit_remaining"] = response.headers.get("X-RateLimit-Remaining")
            if response.status_code == 429:
                return _error_prediction(
                    record,
                    model=args.model,
                    status=ExecutionStatus.RATE_LIMITED,
                    started=started,
                    error={"type": "http_429", "retry_after": response.headers.get("Retry-After")},
                    metadata=metadata,
                )
            if response.status_code >= 400:
                return _error_prediction(
                    record,
                    model=args.model,
                    status=ExecutionStatus.PROVIDER_ERROR,
                    started=started,
                    error={"type": "http_error", "http_status": response.status_code},
                    metadata=metadata,
                )
            content, surfaced, usage = parse_sse(list(response.iter_lines()))
        metadata["surfaced_model_ids"] = surfaced
        if usage:
            metadata["usage_present"] = True
        label = parse_label(content, record)
        if label is None:
            return _error_prediction(
                record,
                model=args.model,
                status=ExecutionStatus.PARSE_ERROR,
                started=started,
                error={"type": "label_not_found"},
                metadata=metadata,
            )
        return JudgePrediction(
            record_id=record.record_id,
            judge_id=args.model,
            protocol_version=PROTOCOL,
            label=label,
            execution_status=ExecutionStatus.OK,
            latency_ms=(time.perf_counter() - started) * 1000.0,
            token_usage=usage or None,
            provider_metadata={**metadata, "content_length": len(content)},
        )
    except httpx.TimeoutException:
        return _error_prediction(
            record,
            model=args.model,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"type": "timeout"},
            metadata=metadata,
        )
    except Exception as exc:  # noqa: BLE001 - preserve one provider status per record
        return _error_prediction(
            record,
            model=args.model,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"type": type(exc).__name__},
            metadata=metadata,
        )


def _checksums(output: Path) -> None:
    lines = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "checksums.sha256":
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(output).as_posix()}")
    (output / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output)
    if output.exists() and any(output.iterdir()) and not args.resume:
        raise FileExistsError(f"refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    prediction_path = output / "predictions.jsonl"
    existing: dict[str, JudgePrediction] = {}
    if args.resume and prediction_path.is_file():
        for line in prediction_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                prediction = JudgePrediction.model_validate_json(line)
                if prediction.record_id in existing:
                    raise ValueError("resume checkpoint contains duplicate record IDs")
                existing[prediction.record_id] = prediction

    records = _load_records(Path(args.pool), args.partition, args.limit)
    expected = {record.record_id for record in records}
    if not set(existing).issubset(expected):
        raise ValueError("resume checkpoint contains an out-of-pool record ID")
    environment = {**_load_dotenv(Path(args.env_file) if args.env_file else None), **os.environ}
    api_key = environment.get("INFERHUB_API_KEY", "")
    api_url = args.api_url or environment.get("INFERHUB_API_URL", "https://api.inferhub.dev/v1")
    pending = [record for record in records if record.record_id not in existing]
    started = time.perf_counter()
    prediction_path.touch(exist_ok=True)
    with prediction_path.open("a", encoding="utf-8") as handle, ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(_evaluate, record, args, api_key, api_url): record.record_id for record in pending}
        for future in as_completed(futures):
            prediction = future.result()
            existing[prediction.record_id] = prediction
            handle.write(prediction.model_dump_json() + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    if set(existing) != expected:
        raise RuntimeError("InferHub run did not produce one status per selected record")
    ordered = [existing[record.record_id] for record in records]
    statuses = dict(sorted(Counter(prediction.execution_status.value for prediction in ordered).items()))
    source_manifest = json.loads((Path(args.pool) / "pool-manifest.json").read_text(encoding="utf-8"))
    results = {
        "experiment_id": args.experiment_id,
        "run_id": output.name,
        "provider": "inferhub",
        "requested_model": args.model,
        "partition": args.partition,
        "record_count": len(records),
        "workers": args.workers,
        "streaming": True,
        "stream_format": "openai-sse",
        "status_counts": statuses,
        "resolved_count": sum(prediction.execution_status is ExecutionStatus.OK for prediction in ordered),
        "elapsed_seconds": time.perf_counter() - started,
        "source_pool": {
            "records_fingerprint": source_manifest["records_fingerprint"],
            "blind_record_ids_fingerprint": source_manifest["blind_record_ids_fingerprint"],
            "typed_question_spec_fingerprint": source_manifest["typed_question_spec_fingerprint"],
        },
        "gold_not_used_for_provider_request": True,
        "created_at_utc": datetime.now(UTC).isoformat(),
    }
    (output / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "report.md").write_text(
        "\n".join(
            [
                f"# {args.experiment_id} — {output.name}",
                "",
                f"Partition: `{args.partition}`; records: `{len(records)}`; workers: `{args.workers}`.",
                f"Requested model: `{args.model}`; streaming format: `openai-sse`.",
                f"Status counts: `{statuses}`.",
                "",
                "Provider failures, rate limits, timeouts, and parse errors remain unresolved and receive no fallback label.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _checksums(output)
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, default=SOURCE_POOL)
    parser.add_argument("--experiment-id", default=EXPERIMENT_ID)
    parser.add_argument("--partition", choices=("public_selection", "blind_holdout", "all"), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--arm-id")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--api-url")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.limit < 0 or args.workers <= 0 or args.timeout <= 0 or args.max_tokens <= 0:
        raise SystemExit("--limit must be non-negative; --workers, --timeout, and --max-tokens must be positive")
    print(json.dumps(run(args), sort_keys=True))


if __name__ == "__main__":
    main()
