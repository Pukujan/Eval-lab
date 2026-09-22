"""Run one frozen matched arm set for a declared experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from eval_lab.escalation.providers import normalize_typed_response
from eval_lab.escalation.spec import build_decision_spec
from eval_lab.reporting import build_report
from eval_lab.schema import (
    ExecutionStatus,
    JudgePrediction,
    JudgeRecord,
    JudgmentMode,
    PairwiseLabel,
)

EXPERIMENT_ID = "EXP-20260921-015-grok-luna-qwen-bakeoff"
PROTOCOL = "eval-lab-system-one-v1"
POOL = Path("experiments") / EXPERIMENT_ID
ARMS = {
    "grok": {
        "provider": "xai-grok-build-cli",
        "requested_model": "grok-4.6",
        "route": "direct_grok_build_cli_subscription",
    },
    "luna": {
        "provider": "codex",
        "requested_model": "gpt-5.6-luna",
        "route": "direct_codex_chatgpt_subscription",
    },
    "qwen_flash": {
        "provider": "yolo-auto",
        "requested_model": "qwen3.8-flash",
        "route": "yolo_auto_openai_compatible",
    },
    "sol": {
        "provider": "codex",
        "requested_model": "gpt-5.6-sol",
        "route": "direct_codex_chatgpt_subscription",
    },
}


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


def _load_pool(
    pool: Path,
    partition: str,
    limit: int,
    record_ids_file: Path | None,
) -> tuple[list[dict[str, Any]], list[JudgeRecord], dict[str, str]]:
    rows = [
        json.loads(line)
        for line in (pool / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    requested_ids = None
    if record_ids_file is not None:
        requested_ids = {
            line.strip()
            for line in record_ids_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        if not requested_ids:
            raise ValueError("record ID file is empty")
    selected = [
        row
        for row in rows
        if (partition == "all" or row["partition"] == partition)
        and (requested_ids is None or row["record"]["record_id"] in requested_ids)
    ]
    if requested_ids is None and limit:
        selected = selected[:limit]
    expected = len(requested_ids) if requested_ids is not None else len(selected)
    if not selected or len(selected) != expected:
        raise ValueError(f"selected pool has {len(selected)} records; expected {expected}")
    records = [JudgeRecord.model_validate(row["record"]) for row in selected]
    if len({record.record_id for record in records}) != len(records):
        raise ValueError("selected pool contains duplicate record IDs")
    domains = {record.record_id: str(row.get("dataset", "unknown")) for row, record in zip(selected, records, strict=True)}
    if requested_ids is not None and {record.record_id for record in records} != requested_ids:
        raise ValueError("record ID file contains an ID outside the selected partition")
    return selected, records, domains


def _nested_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _nested_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _nested_mappings(child)
    elif isinstance(value, str) and value.strip().startswith(("{", "[")):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return
        if isinstance(decoded, (Mapping, list)):
            yield from _nested_mappings(decoded)


def _json_fragments(text: str) -> Iterable[Mapping[str, Any]]:
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, Mapping):
            yield value


def _legal_labels(record: JudgeRecord) -> set[str]:
    if record.mode is JudgmentMode.SINGLE:
        return {"pass", "fail"}
    return {item.value for item in PairwiseLabel}


def parse_label(text: str, record: JudgeRecord) -> str | None:
    """Extract one legal label from a direct CLI response/event stream."""

    legal = _legal_labels(record)
    for fragment in _json_fragments(text):
        for mapping in _nested_mappings(fragment):
            for key in ("label", "verdict", "prediction", "choice", "class", "value"):
                value = mapping.get(key)
                if isinstance(value, Mapping):
                    value = next(
                        (value.get(candidate) for candidate in ("label", "choice", "value") if candidate in value),
                        None,
                    )
                if value is None:
                    continue
                candidate = str(value).strip()
                normalized = candidate.upper() if record.mode is JudgmentMode.PAIRWISE else candidate.lower()
                if normalized in legal:
                    return normalized
    normalized = text.upper() if record.mode is JudgmentMode.PAIRWISE else text.lower()
    token_pattern = r"\b(?:A|B|TIE)\b" if record.mode is JudgmentMode.PAIRWISE else r"\b(?:PASS|FAIL)\b"
    tokens = re.findall(token_pattern, normalized)
    for token in reversed(tokens):
        candidate = token if record.mode is JudgmentMode.PAIRWISE else token.lower()
        if candidate in legal:
            return candidate
    return None


def _surfaced_models(text: str) -> list[str]:
    models: set[str] = set()
    for fragment in _json_fragments(text):
        for mapping in _nested_mappings(fragment):
            for key in ("model", "model_id", "modelID", "modelId", "resolved_model"):
                value = mapping.get(key)
                if isinstance(value, str) and value:
                    models.add(value)
            model_usage = mapping.get("modelUsage")
            if isinstance(model_usage, Mapping):
                models.update(str(key) for key in model_usage if str(key))
    return sorted(models)


def _prompt(record: JudgeRecord) -> str:
    decision = build_decision_spec(record)
    payload = {"record_id": decision.record_id, **decision.provider_payload()}
    labels = ", ".join(decision.legal_labels)
    return (
        "You are a strictly typed objective evaluation judge. "
        f"Return exactly one JSON object with label set to one of [{labels}]. "
        "Do not include explanation, markdown, or additional keys.\n\n"
        + json.dumps(payload, sort_keys=True)
    )


def _grok_json_schema(record: JudgeRecord) -> str:
    return json.dumps(
        {
            "type": "object",
            "properties": {"label": {"type": "string", "enum": sorted(_legal_labels(record))}},
            "required": ["label"],
            "additionalProperties": False,
        },
        separators=(",", ":"),
    )


def _prediction(
    record: JudgeRecord,
    *,
    arm_id: str,
    provider: str,
    model: str,
    route: str,
    status: ExecutionStatus,
    started: float,
    label: str | None = None,
    error: dict[str, Any] | None = None,
    surfaced_model_ids: list[str] | None = None,
) -> JudgePrediction:
    return JudgePrediction(
        record_id=record.record_id,
        judge_id=model,
        protocol_version=PROTOCOL,
        label=label,
        execution_status=status,
        latency_ms=(time.perf_counter() - started) * 1000.0,
        provider_metadata={
            "provider": provider,
            "arm_id": arm_id,
            "requested_model": model,
            "route": route,
            "typed_spec_id": "eval-lab-system-one",
            "typed_spec_version": "0.1.0",
            "surfaced_model_ids": surfaced_model_ids or [],
        },
        error=error,
    )


def _stream_metadata(stream_format: str, event_count: int) -> dict[str, Any]:
    return {
        "streaming": True,
        "stream_format": stream_format,
        "stream_event_count": event_count,
    }


def _with_stream_metadata(
    prediction: JudgePrediction,
    *,
    stream_format: str,
    event_count: int,
) -> JudgePrediction:
    prediction.provider_metadata.update(_stream_metadata(stream_format, event_count))
    return prediction


def _stream_reader(pipe: Any, stream_name: str, events: queue.Queue[tuple[str, str | None]]) -> None:
    try:
        for line in iter(pipe.readline, ""):
            events.put((stream_name, line))
    finally:
        events.put((stream_name, None))


def _run_streaming_process(
    command: list[str],
    *,
    environment: dict[str, str],
    timeout: float,
    input_text: str | None = None,
    on_stdout_line: Callable[[str], None] | None = None,
) -> tuple[int | None, str, str, bool, int]:
    """Run a CLI while consuming stdout/stderr incrementally.

    The direct Grok and Codex CLIs emit newline-delimited events. Dedicated
    reader threads prevent either pipe from filling while the parent process
    receives stdout events as they arrive. The returned transcript remains
    available for the existing typed-label parser.
    """

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE if input_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=environment,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    if input_text is not None and process.stdin is not None:
        try:
            process.stdin.write(input_text)
            process.stdin.close()
        except OSError:
            pass

    events: queue.Queue[tuple[str, str | None]] = queue.Queue()
    readers = [
        threading.Thread(target=_stream_reader, args=(process.stdout, "stdout", events), daemon=True),
        threading.Thread(target=_stream_reader, args=(process.stderr, "stderr", events), daemon=True),
    ]
    for reader in readers:
        reader.start()

    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    closed: set[str] = set()
    event_count = 0
    timed_out = False
    deadline = time.monotonic() + timeout
    while len(closed) < 2:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            break
        try:
            stream_name, line = events.get(timeout=min(0.25, remaining))
        except queue.Empty:
            continue
        if line is None:
            closed.add(stream_name)
            continue
        if stream_name == "stdout":
            stdout_parts.append(line)
            event_count += 1
            if on_stdout_line is not None:
                on_stdout_line(line)
        else:
            stderr_parts.append(line)

    if timed_out:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            text=True,
            check=False,
        )
    try:
        process.wait(timeout=2 if timed_out else max(0.1, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            text=True,
            check=False,
        )
        timed_out = True
    for reader in readers:
        reader.join(timeout=1)
    return process.returncode, "".join(stdout_parts), "".join(stderr_parts), timed_out, event_count


def _isolated_grok_leader_socket() -> Path:
    return Path(tempfile.gettempdir()) / f"eval-lab-grok-{os.getpid()}-{threading.get_ident()}-{uuid.uuid4().hex}.sock"


def _run_codex_one(
    record: JudgeRecord,
    *,
    arm_id: str,
    model: str,
    route: str,
    environment: dict[str, str],
    timeout: float,
) -> JudgePrediction:
    """Run Codex CLI directly with the authenticated ChatGPT subscription."""

    started = time.perf_counter()
    executable = environment.get("CODEX_EXE") or shutil.which("codex") or "codex"
    command = [
        executable,
        "exec",
        "--model",
        model,
        "--cd",
        str(Path.cwd()),
        "--sandbox",
        "read-only",
        "--ephemeral",
        "--json",
        "-",
    ]
    try:
        returncode, stdout, stderr, timed_out, event_count = _run_streaming_process(
            command,
            environment=environment,
            input_text=_prompt(record),
            timeout=timeout,
        )
    except OSError as exc:
        return _with_stream_metadata(
            _prediction(
                record,
                arm_id=arm_id,
                provider="codex",
                model=model,
                route=route,
                status=ExecutionStatus.PROVIDER_ERROR,
                started=started,
                error={"kind": "process_error", "type": type(exc).__name__},
            ),
            stream_format="codex-jsonl",
            event_count=0,
        )
    if timed_out:
        return _with_stream_metadata(
            _prediction(
                record,
                arm_id=arm_id,
                provider="codex",
                model=model,
                route=route,
                status=ExecutionStatus.PROVIDER_ERROR,
                started=started,
                error={"kind": "timeout"},
            ),
            stream_format="codex-jsonl",
            event_count=event_count,
        )
    output = stdout + "\n" + stderr
    surfaced = _surfaced_models(output)
    thread_id: str | None = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
            thread_id = event["thread_id"]
    metadata = {"codex_cli": "codex", "thread_id": thread_id} if thread_id else {"codex_cli": "codex"}
    if returncode != 0:
        lower = output.lower()
        status = ExecutionStatus.RATE_LIMITED if "429" in lower or "rate limit" in lower else ExecutionStatus.PROVIDER_ERROR
        kind = "rate_limited" if status is ExecutionStatus.RATE_LIMITED else "process_exit"
        prediction = _prediction(
            record,
            arm_id=arm_id,
            provider="codex",
            model=model,
            route=route,
            status=status,
            started=started,
            error={"kind": kind, "returncode": returncode},
            surfaced_model_ids=surfaced,
        )
        prediction.provider_metadata.update(metadata)
        return _with_stream_metadata(prediction, stream_format="codex-jsonl", event_count=event_count)
    label = parse_label(output, record)
    if label is None:
        prediction = _prediction(
            record,
            arm_id=arm_id,
            provider="codex",
            model=model,
            route=route,
            status=ExecutionStatus.PARSE_ERROR,
            started=started,
            error={"kind": "label_not_found"},
            surfaced_model_ids=surfaced,
        )
        prediction.provider_metadata.update(metadata)
        return _with_stream_metadata(prediction, stream_format="codex-jsonl", event_count=event_count)
    prediction = _prediction(
        record,
        arm_id=arm_id,
        provider="codex",
        model=model,
        route=route,
        status=ExecutionStatus.OK,
        started=started,
        label=label,
        surfaced_model_ids=surfaced,
    )
    prediction.provider_metadata.update(metadata)
    return _with_stream_metadata(prediction, stream_format="codex-jsonl", event_count=event_count)


def _run_grok_build_one(
    record: JudgeRecord,
    *,
    arm_id: str,
    model: str,
    route: str,
    environment: dict[str, str],
    timeout: float,
) -> JudgePrediction:
    """Run the direct xAI Grok Build CLI through the subscription session."""

    started = time.perf_counter()
    executable = environment.get("GROK_EXE") or shutil.which("grok") or "grok"
    leader_socket = _isolated_grok_leader_socket()
    command = [
        executable,
        "--model",
        model,
        "--output-format",
        "streaming-json",
        "--json-schema",
        _grok_json_schema(record),
        "--max-turns",
        "1",
        "--disable-web-search",
        "--verbatim",
        "--no-subagents",
        "--no-plan",
        "--permission-mode",
        "dontAsk",
        "--leader-socket",
        str(leader_socket),
        f"--single={_prompt(record)}",
    ]
    try:
        returncode, stdout, stderr, timed_out, event_count = _run_streaming_process(
            command,
            environment=environment,
            timeout=timeout,
        )
    except OSError as exc:
        prediction = _prediction(
            record,
            arm_id=arm_id,
            provider="xai-grok-build-cli",
            model=model,
            route=route,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "process_error", "type": type(exc).__name__},
        )
        return _with_stream_metadata(prediction, stream_format="grok-streaming-json", event_count=0)
    finally:
        leader_socket.unlink(missing_ok=True)
    if timed_out:
        prediction = _prediction(
            record,
            arm_id=arm_id,
            provider="xai-grok-build-cli",
            model=model,
            route=route,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "timeout"},
        )
        return _with_stream_metadata(prediction, stream_format="grok-streaming-json", event_count=event_count)
    output = stdout + "\n" + stderr
    surfaced = _surfaced_models(output)
    if returncode != 0:
        lower = output.lower()
        status = ExecutionStatus.RATE_LIMITED if "429" in lower or "rate limit" in lower else ExecutionStatus.PROVIDER_ERROR
        kind = "rate_limited" if status is ExecutionStatus.RATE_LIMITED else "process_exit"
        prediction = _prediction(
            record,
            arm_id=arm_id,
            provider="xai-grok-build-cli",
            model=model,
            route=route,
            status=status,
            started=started,
            error={"kind": kind, "returncode": returncode},
            surfaced_model_ids=surfaced,
        )
        return _with_stream_metadata(prediction, stream_format="grok-streaming-json", event_count=event_count)
    label = parse_label(output, record)
    if label is None:
        prediction = _prediction(
            record,
            arm_id=arm_id,
            provider="xai-grok-build-cli",
            model=model,
            route=route,
            status=ExecutionStatus.PARSE_ERROR,
            started=started,
            error={"kind": "label_not_found"},
            surfaced_model_ids=surfaced,
        )
        return _with_stream_metadata(prediction, stream_format="grok-streaming-json", event_count=event_count)
    prediction = _prediction(
        record,
        arm_id=arm_id,
        provider="xai-grok-build-cli",
        model=model,
        route=route,
        status=ExecutionStatus.OK,
        started=started,
        label=label,
        surfaced_model_ids=surfaced,
    )
    return _with_stream_metadata(prediction, stream_format="grok-streaming-json", event_count=event_count)


def _run_grok_build_arm(
    records: list[JudgeRecord],
    *,
    arm_id: str,
    model: str,
    route: str,
    environment: dict[str, str],
    timeout: float,
    workers: int,
    prediction_path: Path,
    progress_path: Path,
    existing_predictions: list[JudgePrediction] | None = None,
) -> list[JudgePrediction]:
    return _run_parallel_arm(
        records,
        arm_id=arm_id,
        provider="xai-grok-build-cli",
        model=model,
        route=route,
        workers=workers,
        prediction_path=prediction_path,
        progress_path=progress_path,
        existing_predictions=existing_predictions,
        evaluate=lambda record: _run_grok_build_one(
            record,
            arm_id=arm_id,
            model=model,
            route=route,
            environment=environment,
            timeout=timeout,
        ),
    )


def _run_parallel_arm(
    records: list[JudgeRecord],
    *,
    arm_id: str,
    provider: str,
    model: str,
    route: str,
    workers: int,
    prediction_path: Path,
    progress_path: Path,
    evaluate: Callable[[JudgeRecord], JudgePrediction],
    existing_predictions: list[JudgePrediction] | None = None,
) -> list[JudgePrediction]:
    """Evaluate records concurrently and checkpoint each normalized result."""

    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    existing = existing_predictions or []
    expected_ids = {record.record_id for record in records}
    by_record_id = {prediction.record_id: prediction for prediction in existing}
    if len(by_record_id) != len(existing) or not set(by_record_id).issubset(expected_ids):
        raise ValueError(f"{arm_id} resume checkpoint has duplicate or out-of-pool records")
    if existing_predictions is None:
        prediction_path.write_text("", encoding="utf-8")

    def safe_evaluate(record: JudgeRecord) -> JudgePrediction:
        try:
            return evaluate(record)
        except Exception as exc:  # noqa: BLE001  # keep one unexpected provider/adapter fault local to its record
            return _prediction(
                record,
                arm_id=arm_id,
                provider=provider,
                model=model,
                route=route,
                status=ExecutionStatus.PROVIDER_ERROR,
                started=time.perf_counter(),
                error={"kind": "runner_exception", "type": type(exc).__name__},
            )

    def checkpoint(prediction: JudgePrediction, handle: Any) -> None:
        by_record_id[prediction.record_id] = prediction
        handle.write(prediction.model_dump_json() + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        progress_path.write_text(
            json.dumps(
                {
                    "arm_id": arm_id,
                    "provider": provider,
                    "route": route,
                    "requested_model": model,
                    "streaming": True,
                    "workers": workers,
                    "record_count": len(records),
                    "completed_count": len(by_record_id),
                    "status_counts": dict(sorted(Counter(item.execution_status.value for item in by_record_id.values()).items())),
                    "last_record_id": prediction.record_id,
                    "updated_at_utc": datetime.now(UTC).isoformat(),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    pending_records = [record for record in records if record.record_id not in by_record_id]
    with prediction_path.open("a", encoding="utf-8") as handle:
        if workers <= 1:
            for record in pending_records:
                checkpoint(safe_evaluate(record), handle)
        else:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(safe_evaluate, record): record.record_id for record in pending_records}
                for future in as_completed(futures):
                    checkpoint(future.result(), handle)

    if set(by_record_id) != expected_ids:
        raise RuntimeError(f"arm {arm_id} did not produce one result per record")
    return [by_record_id[record.record_id] for record in records]


def _run_codex_arm(
    records: list[JudgeRecord],
    *,
    arm_id: str,
    model: str,
    route: str,
    environment: dict[str, str],
    timeout: float,
    workers: int,
    prediction_path: Path,
    progress_path: Path,
    existing_predictions: list[JudgePrediction] | None = None,
) -> list[JudgePrediction]:
    return _run_parallel_arm(
        records,
        arm_id=arm_id,
        provider="codex",
        model=model,
        route=route,
        workers=workers,
        prediction_path=prediction_path,
        progress_path=progress_path,
        existing_predictions=existing_predictions,
        evaluate=lambda record: _run_codex_one(
            record,
            arm_id=arm_id,
            model=model,
            route=route,
            environment=environment,
            timeout=timeout,
        ),
    )


def _qwen_payload(record: JudgeRecord, model: str) -> dict[str, Any]:
    decision = build_decision_spec(record)
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return a JSON object with a legal label."},
            {"role": "user", "content": json.dumps(decision.provider_payload(), sort_keys=True)},
        ],
        "temperature": 0,
        "stream": True,
    }


def _qwen_stream_response(
    response: httpx.Response,
    *,
    record: JudgeRecord,
) -> tuple[str, list[str], dict[str, Any] | None, int]:
    parts: list[str] = []
    surfaced: set[str] = set()
    usage: dict[str, Any] | None = None
    event_count = 0
    for raw_line in response.iter_lines():
        line = raw_line.decode() if isinstance(raw_line, bytes) else raw_line
        line = line.strip()
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
        if not isinstance(event, Mapping):
            continue
        event_count += 1
        model_id = event.get("model")
        if isinstance(model_id, str) and model_id:
            surfaced.add(model_id)
        raw_usage = event.get("usage")
        if isinstance(raw_usage, Mapping):
            usage = {str(key): value for key, value in raw_usage.items()}
        choices = event.get("choices")
        if not isinstance(choices, list):
            continue
        for choice in choices:
            if not isinstance(choice, Mapping):
                continue
            delta = choice.get("delta") or choice.get("message")
            if not isinstance(delta, Mapping):
                continue
            content = delta.get("content")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, Mapping) and isinstance(block.get("text"), str):
                        parts.append(block["text"])
    if not parts:
        raise ValueError(f"stream contained no message content for {record.record_id}")
    return "".join(parts), sorted(surfaced), usage, event_count


def _run_qwen_one(
    record: JudgeRecord,
    *,
    arm_id: str,
    model: str,
    route: str,
    api_key: str | None,
    base_url: str,
    client: httpx.Client,
    timeout: float,
) -> JudgePrediction:
    started = time.perf_counter()
    if not api_key:
        return _with_stream_metadata(
            _prediction(
                record,
                arm_id=arm_id,
                provider="yolo-auto",
                model=model,
                route=route,
                status=ExecutionStatus.SKIPPED,
                started=started,
                error={"kind": "missing_api_key"},
            ),
            stream_format="openai-sse",
            event_count=0,
        )
    try:
        with client.stream(
            "POST",
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            json=_qwen_payload(record, model),
        ) as response:
            if response.status_code == 429:
                prediction = _prediction(
                    record,
                    arm_id=arm_id,
                    provider="yolo-auto",
                    model=model,
                    route=route,
                    status=ExecutionStatus.RATE_LIMITED,
                    started=started,
                    error={"kind": "rate_limited", "status_code": response.status_code},
                )
                return _with_stream_metadata(prediction, stream_format="openai-sse", event_count=0)
            if response.status_code >= 400:
                prediction = _prediction(
                    record,
                    arm_id=arm_id,
                    provider="yolo-auto",
                    model=model,
                    route=route,
                    status=ExecutionStatus.PROVIDER_ERROR,
                    started=started,
                    error={"kind": "provider_error", "status_code": response.status_code},
                )
                return _with_stream_metadata(prediction, stream_format="openai-sse", event_count=0)
            content, surfaced, usage, event_count = _qwen_stream_response(response, record=record)
        response_payload: dict[str, Any] = {
            "model": surfaced[-1] if surfaced else model,
            "choices": [{"message": {"content": content}}],
        }
        if usage is not None:
            response_payload["usage"] = usage
        prediction = normalize_typed_response(
            response_payload,
            record,
            provider="yolo-auto",
            model=model,
            latency_ms=(time.perf_counter() - started) * 1000.0,
        )
        prediction.provider_metadata.update(
            {
                "arm_id": arm_id,
                "requested_model": model,
                "route": route,
                "base_url": base_url,
                "surfaced_model_ids": surfaced,
            }
        )
        return _with_stream_metadata(prediction, stream_format="openai-sse", event_count=event_count)
    except httpx.TimeoutException:
        prediction = _prediction(
            record,
            arm_id=arm_id,
            provider="yolo-auto",
            model=model,
            route=route,
            status=ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "timeout"},
        )
        return _with_stream_metadata(prediction, stream_format="openai-sse", event_count=0)
    except (httpx.HTTPError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        prediction = _prediction(
            record,
            arm_id=arm_id,
            provider="yolo-auto",
            model=model,
            route=route,
            status=ExecutionStatus.PARSE_ERROR if isinstance(exc, (TypeError, ValueError, json.JSONDecodeError)) else ExecutionStatus.PROVIDER_ERROR,
            started=started,
            error={"kind": "parse_error" if isinstance(exc, (TypeError, ValueError, json.JSONDecodeError)) else "adapter_error", "type": type(exc).__name__},
        )
        return _with_stream_metadata(prediction, stream_format="openai-sse", event_count=0)


def _run_qwen_arm(
    records: list[JudgeRecord],
    *,
    arm_id: str,
    model: str,
    route: str,
    environment: dict[str, str],
    timeout: float,
    workers: int,
    prediction_path: Path,
    progress_path: Path,
    existing_predictions: list[JudgePrediction] | None = None,
) -> list[JudgePrediction]:
    api_key = environment.get("YOLO_AUTO_API_KEY") or environment.get("YOLO_API_KEY") or environment.get("QWEN_API_KEY")
    base_url = environment.get("YOLO_AUTO_BASE_URL") or environment.get("QWEN_API_URL") or "https://api.yolo-auto.com/v1"
    clients: list[httpx.Client] = []
    clients_lock = threading.Lock()
    thread_state = threading.local()

    def evaluate(record: JudgeRecord) -> JudgePrediction:
        client = getattr(thread_state, "client", None)
        if client is None:
            client = httpx.Client(timeout=timeout)
            thread_state.client = client
            with clients_lock:
                clients.append(client)
        return _run_qwen_one(
            record,
            arm_id=arm_id,
            model=model,
            route=route,
            api_key=api_key,
            base_url=base_url,
            client=client,
            timeout=timeout,
        )

    try:
        return _run_parallel_arm(
            records,
            arm_id=arm_id,
            provider="yolo-auto",
            model=model,
            route=route,
            workers=workers,
            prediction_path=prediction_path,
            progress_path=progress_path,
            evaluate=evaluate,
            existing_predictions=existing_predictions,
        )
    finally:
        for client in clients:
            client.close()


def _wilson(successes: int, trials: int) -> dict[str, float] | None:
    if trials == 0:
        return None
    z = 1.959963984540054
    estimate = successes / trials
    denominator = 1 + z * z / trials
    center = (estimate + z * z / (2 * trials)) / denominator
    margin = z * (estimate * (1 - estimate) / trials + z * z / (4 * trials * trials)) ** 0.5 / denominator
    return {"lower": max(0.0, center - margin), "upper": min(1.0, center + margin)}


def _arm_summary(
    records: list[JudgeRecord],
    predictions: list[JudgePrediction],
    domains: dict[str, str],
    arm: dict[str, str],
) -> dict[str, Any]:
    resolved = [
        (record, prediction)
        for record, prediction in zip(records, predictions, strict=True)
        if prediction.execution_status is ExecutionStatus.OK and prediction.label is not None
    ]
    correct = sum(record.gold.label == prediction.label for record, prediction in resolved)
    surfaced = sorted(
        {
            surfaced
            for prediction in predictions
            for surfaced in prediction.provider_metadata.get("surfaced_model_ids", [])
        }
    )
    error_kinds = Counter(
        str((prediction.error or {}).get("kind") or (prediction.error or {}).get("type") or "unknown")
        for prediction in predictions
        if prediction.execution_status is not ExecutionStatus.OK
    )
    usage = [
        prediction.provider_metadata.get("usage")
        for prediction in predictions
        if isinstance(prediction.provider_metadata.get("usage"), dict)
    ]
    report = build_report(records, predictions, domain_by_record_id=domains)
    return {
        "provider": arm["provider"],
        "route": arm["route"],
        "requested_model": arm["requested_model"],
        "surfaced_model_ids": surfaced,
        "record_count": len(records),
        "resolved_count": len(resolved),
        "correct_count": correct,
        "resolved_coverage": len(resolved) / len(records) if records else 0.0,
        "unresolved_rate": (len(records) - len(resolved)) / len(records) if records else 0.0,
        "accuracy": correct / len(resolved) if resolved else None,
        "accuracy_wilson_95": _wilson(correct, len(resolved)),
        "native_probability_count": sum(prediction.probabilities is not None for prediction in predictions),
        "usage_metadata_count": len(usage),
        "status_counts": dict(sorted(Counter(prediction.execution_status.value for prediction in predictions).items())),
        "error_kinds": dict(sorted(error_kinds.items())),
        "metrics": report,
    }


def _differential(
    records: list[JudgeRecord], predictions: dict[str, list[JudgePrediction]]
) -> dict[str, Any]:
    by_arm = {
        arm: {prediction.record_id: prediction for prediction in values}
        for arm, values in predictions.items()
    }
    arms = sorted(predictions)
    pairs: dict[str, dict[str, Any]] = {}
    for left_index, left in enumerate(arms):
        for right in arms[left_index + 1 :]:
            comparable = 0
            agreement = 0
            for record in records:
                first = by_arm[left][record.record_id]
                second = by_arm[right][record.record_id]
                if (
                    first.execution_status is ExecutionStatus.OK
                    and second.execution_status is ExecutionStatus.OK
                    and first.label is not None
                    and second.label is not None
                ):
                    comparable += 1
                    agreement += int(first.label == second.label)
            pairs[f"{left}__vs__{right}"] = {
                "comparable_count": comparable,
                "agreement_count": agreement,
                "agreement_rate": agreement / comparable if comparable else None,
            }
    return {"arms": arms, "pairs": pairs}


def _checksums(root: Path) -> None:
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "checksums.sha256":
            continue
        entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
    (root / "checksums.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


def _load_prediction_checkpoint(
    path: Path,
    *,
    records: list[JudgeRecord],
    arm_id: str,
) -> list[JudgePrediction]:
    if not path.is_file():
        return []
    predictions = [
        JudgePrediction.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    expected_ids = {record.record_id for record in records}
    ids = [prediction.record_id for prediction in predictions]
    if len(ids) != len(set(ids)) or not set(ids).issubset(expected_ids):
        raise ValueError(f"{arm_id} checkpoint contains duplicate or out-of-pool record IDs")
    return predictions


def _run(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output)
    if output.exists() and any(output.iterdir()) and not args.resume:
        raise FileExistsError(f"refusing to overwrite non-empty output: {output}")
    if args.resume and (output / "results.json").is_file():
        raise FileExistsError(f"refusing to resume an already finalized output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    prediction_dir = output / "predictions"
    prediction_dir.mkdir(exist_ok=True)
    progress_dir = output / "progress"
    progress_dir.mkdir(exist_ok=True)
    pool = Path(args.pool)
    selected_rows, records, domains = _load_pool(pool, args.partition, args.limit, args.record_ids_file)
    environment = {**_load_dotenv(Path(args.env_file) if args.env_file else None), **os.environ}
    selected_arms = tuple(args.models.split(",")) if args.models else ("grok", "luna", "qwen_flash")
    unknown = sorted(set(selected_arms) - set(ARMS))
    if unknown:
        raise ValueError(f"unknown arm(s): {unknown}")
    predictions: dict[str, list[JudgePrediction]] = {}
    reports: dict[str, Any] = {}
    for arm_id in selected_arms:
        arm = ARMS[arm_id]
        existing_predictions = (
            _load_prediction_checkpoint(
                prediction_dir / f"{arm_id}.jsonl",
                records=records,
                arm_id=arm_id,
            )
            if args.resume
            else None
        )
        if arm_id == "grok":
            arm_predictions = _run_grok_build_arm(
                records,
                arm_id=arm_id,
                model=arm["requested_model"],
                route=arm["route"],
                environment=environment,
                timeout=args.timeout,
                workers=args.workers,
                prediction_path=prediction_dir / f"{arm_id}.jsonl",
                progress_path=progress_dir / f"{arm_id}.json",
                existing_predictions=existing_predictions,
            )
        elif arm["provider"] == "codex":
            arm_predictions = _run_codex_arm(
                records,
                arm_id=arm_id,
                model=arm["requested_model"],
                route=arm["route"],
                environment=environment,
                timeout=args.timeout,
                workers=args.workers,
                prediction_path=prediction_dir / f"{arm_id}.jsonl",
                progress_path=progress_dir / f"{arm_id}.json",
                existing_predictions=existing_predictions,
            )
        else:
            arm_predictions = _run_qwen_arm(
                records,
                arm_id=arm_id,
                model=arm["requested_model"],
                route=arm["route"],
                environment=environment,
                timeout=args.timeout,
                workers=args.workers,
                prediction_path=prediction_dir / f"{arm_id}.jsonl",
                progress_path=progress_dir / f"{arm_id}.json",
                existing_predictions=existing_predictions,
            )
        predictions[arm_id] = arm_predictions
        (prediction_dir / f"{arm_id}.jsonl").write_text(
            "".join(prediction.model_dump_json() + "\n" for prediction in arm_predictions),
            encoding="utf-8",
        )
        reports[arm_id] = _arm_summary(records, arm_predictions, domains, arm)

    manifest = json.loads((pool / "pool-manifest.json").read_text(encoding="utf-8"))
    results = {
        "experiment_id": args.experiment_id,
        "run_id": output.name,
        "status": "completed_with_provider_statuses",
        "partition": args.partition,
        "source_pool": {
            "records_fingerprint": manifest["records_fingerprint"],
            "blind_record_ids_fingerprint": manifest["blind_record_ids_fingerprint"],
            "typed_question_spec_fingerprint": manifest["typed_question_spec_fingerprint"],
        },
        "record_count": len(records),
        "execution": {
            "workers": args.workers,
            "streaming": True,
            "stream_formats": {
                "grok": "grok-streaming-json",
                "luna": "codex-jsonl",
                "sol": "codex-jsonl",
                "qwen_flash": "openai-sse",
            },
        },
        "record_ids_unique": len({record.record_id for record in records}) == len(records),
        "provider_pool_order_sha256": hashlib.sha256(
            "\n".join(row["record"]["record_id"] for row in selected_rows).encode("utf-8")
        ).hexdigest(),
        "arms": reports,
        "differential": _differential(records, predictions),
        "environment": {"platform": platform.platform(), "python": platform.python_version()},
        "created_at_utc": datetime.now(UTC).isoformat(),
    }
    (output / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "differential.json").write_text(
        json.dumps(results["differential"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "provider-status.json").write_text(
        json.dumps(
            {
                "experiment_id": args.experiment_id,
                "run_id": output.name,
                "partition": args.partition,
                "arms": {
                    arm_id: {
                        "provider": report["provider"],
                        "route": report["route"],
                        "requested_model": report["requested_model"],
                        "surfaced_model_ids": report["surfaced_model_ids"],
                        "status_counts": report["status_counts"],
                        "error_kinds": report["error_kinds"],
                    }
                    for arm_id, report in reports.items()
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        f"# {args.experiment_id} — {output.name}",
        "",
        f"Partition: `{args.partition}`; matched records: `{len(records)}`.",
        "",
        "| Arm | Requested model | Surfaced IDs | Resolved | Coverage | Accuracy | Wilson 95% | Statuses |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for arm_id, report in reports.items():
        surfaced = ", ".join(report["surfaced_model_ids"]) or "(none surfaced)"
        lines.append(
            f"| `{arm_id}` | `{report['requested_model']}` | `{surfaced}` | "
            f"{report['resolved_count']}/{report['record_count']} | {report['resolved_coverage']:.4f} | "
            f"{report['accuracy']} | `{report['accuracy_wilson_95']}` | `{report['status_counts']}` |"
        )
    lines.extend(
        [
            "",
            "Provider failures, rate limits, parse errors, and skipped records remain unresolved and receive no fallback label.",
            "Native probability and risk/coverage metrics are reported only when a valid probability map is returned.",
            "",
            f"Same-record agreement: `{json.dumps(results['differential']['pairs'], sort_keys=True)}`.",
        ]
    )
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _checksums(output)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", type=Path, default=POOL)
    parser.add_argument("--experiment-id", default=EXPERIMENT_ID)
    parser.add_argument("--partition", choices=("public_selection", "blind_holdout", "all"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--record-ids-file", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--models", help="comma-separated arm IDs; default: grok,luna,qwen_flash")
    parser.add_argument("--resume", action="store_true", help="resume normalized per-arm checkpoints in an existing run directory")
    args = parser.parse_args()
    if args.limit < 0 or args.workers <= 0:
        raise SystemExit("--limit must be non-negative and --workers must be positive")
    result = _run(args)
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "run_id": result["run_id"],
                "partition": result["partition"],
                "record_count": result["record_count"],
                "arms": {arm: report["status_counts"] for arm, report in result["arms"].items()},
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
