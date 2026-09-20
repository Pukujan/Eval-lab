"""Run a one-record-at-a-time streaming retry for the frozen Qwen arm."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from eval_lab.escalation.providers import normalize_typed_response
from eval_lab.escalation.spec import build_decision_spec
from eval_lab.reporting import build_report
from eval_lab.schema import ExecutionStatus, JudgePrediction, JudgeRecord

EXPERIMENT_ID = "EXP-20260920-009-selective-escalation"
MODEL = "qwen3.8-flash"
PROTOCOL = "eval-lab-system-one-v1"
BENCHMARK_FINGERPRINT = "18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5"


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


def _load_records(benchmark: Path, limit: int) -> tuple[list[JudgeRecord], dict[str, str]]:
    records: list[JudgeRecord] = []
    domains: dict[str, str] = {}
    for raw in (benchmark / "records.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(raw)
        if row["partition"] != "final_evaluation":
            continue
        record = JudgeRecord.model_validate(row["record"])
        records.append(record)
        domains[record.record_id] = str(row["domain"])
        if len(records) == limit:
            break
    if len(records) != limit:
        raise ValueError(f"final-evaluation pool contains only {len(records)} records; need {limit}")
    if len({record.record_id for record in records}) != len(records):
        raise ValueError("final-evaluation record IDs are not unique")
    return records, domains


def _prompt(record: JudgeRecord) -> dict[str, Any]:
    spec = build_decision_spec(record)
    return {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Return a JSON object with a legal label."},
            {"role": "user", "content": json.dumps(spec.provider_payload(), sort_keys=True)},
        ],
        "temperature": 0,
        "max_tokens": 128,
        "stream": True,
        "chat_template_kwargs": {"enable_thinking": False},
    }


def _stream_content(response: httpx.Response) -> tuple[str, str | None]:
    content: list[str] = []
    returned_model: str | None = None
    for raw_line in response.iter_lines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
        if line == "[DONE]":
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        raw_model = event.get("model")
        if raw_model is not None:
            returned_model = str(raw_model)
        choices = event.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            continue
        choice = choices[0]
        delta = choice.get("delta")
        message = choice.get("message")
        part = delta if isinstance(delta, dict) else message if isinstance(message, dict) else {}
        text = part.get("content") if isinstance(part, dict) else None
        if isinstance(text, str):
            content.append(text)
    return "".join(content), returned_model


def _error(record: JudgeRecord, *, status: ExecutionStatus, started: float, kind: str, **details: Any) -> JudgePrediction:
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=MODEL,
        protocol_version=PROTOCOL,
        execution_status=status,
        latency_ms=(time.perf_counter() - started) * 1000.0,
        provider_metadata={
            "provider": "yolo-auto",
            "model": MODEL,
            "streaming": True,
            "granularity": "one_record_per_request",
        },
        error={"kind": kind, **details},
    )


def _run_one(record: JudgeRecord, *, client: httpx.Client, url: str, api_key: str, timeout: float) -> JudgePrediction:
    started = time.perf_counter()
    try:
        with client.stream(
            "POST",
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=_prompt(record),
            timeout=timeout,
        ) as response:
            if response.status_code == 429:
                return _error(record, status=ExecutionStatus.RATE_LIMITED, started=started, kind="rate_limited")
            if response.status_code >= 400:
                return _error(
                    record,
                    status=ExecutionStatus.PROVIDER_ERROR,
                    started=started,
                    kind="http_status",
                    status_code=response.status_code,
                )
            content, returned_model = _stream_content(response)
    except httpx.TimeoutException:
        return _error(record, status=ExecutionStatus.PROVIDER_ERROR, started=started, kind="timeout")
    except httpx.HTTPError as exc:
        return _error(
            record,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            kind="transport_error",
            error_type=type(exc).__name__,
        )
    if returned_model is not None and returned_model != MODEL:
        return _error(
            record,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            kind="model_identity_mismatch",
            returned_model=returned_model,
        )
    try:
        prediction = normalize_typed_response(
            {"model": returned_model or MODEL, "choices": [{"message": {"content": content}}]},
            record,
            provider="yolo-auto",
            model=MODEL,
            latency_ms=(time.perf_counter() - started) * 1000.0,
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        return _error(record, status=ExecutionStatus.PARSE_ERROR, started=started, kind="label_not_found")
    prediction.provider_metadata.update({"streaming": True, "granularity": "one_record_per_request"})
    return prediction


def _checksums(root: Path) -> None:
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "checksums.sha256":
            continue
        entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
    (root / "checksums.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite existing retry output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    environment = {**_load_dotenv(Path(args.env_file) if args.env_file else None), **os.environ}
    api_key = environment.get("YOLO_AUTO_API_KEY") or environment.get("YOLO_API_KEY") or environment.get("QWEN_API_KEY")
    if not api_key:
        raise RuntimeError("Qwen credential is unavailable")
    base_url = (environment.get("YOLO_AUTO_BASE_URL") or environment.get("QWEN_API_URL") or "https://api.yolo-auto.com/v1").rstrip("/")
    records, domains = _load_records(Path(args.benchmark), args.limit)
    with httpx.Client() as client:
        predictions = [_run_one(record, client=client, url=f"{base_url}/chat/completions", api_key=api_key, timeout=args.timeout) for record in records]
    (output / "predictions.jsonl").write_text(
        "".join(prediction.model_dump_json() + "\n" for prediction in predictions), encoding="utf-8"
    )
    counts = dict(Counter(prediction.execution_status.value for prediction in predictions))
    results = {
        "experiment_id": EXPERIMENT_ID,
        "retry_id": output.name,
        "benchmark_fingerprint": BENCHMARK_FINGERPRINT,
        "model": MODEL,
        "limit": args.limit,
        "timeout_seconds": args.timeout,
        "streaming": True,
        "granularity": "one_record_per_request",
        "status_counts": counts,
        "record_ids_unique": len({prediction.record_id for prediction in predictions}) == len(predictions),
        "report": build_report(records, predictions, domain_by_record_id=domains),
        "created_at_utc": datetime.now(UTC).isoformat(),
    }
    (output / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "provider-status.json").write_text(
        json.dumps({"model": MODEL, "status_counts": counts, "base_url": base_url}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _checksums(output)
    return {"experiment_id": EXPERIMENT_ID, "retry_id": output.name, "status_counts": counts}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=Path("benchmark/eval-lab-select-v0.1.0"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args), sort_keys=True))


if __name__ == "__main__":
    main()
