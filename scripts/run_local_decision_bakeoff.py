"""Run one pinned Jev-style model arm on the Mac and checkpoint every decision."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from eval_lab.judges.local_decision_models import (
        PROTOCOL_VERSION,
        normalize_choice_output,
        request_for_record,
    )
except ModuleNotFoundError:
    # A standalone runner copy on the Mac keeps this protocol module beside it.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from local_decision_models import (  # type: ignore[no-redef]
        PROTOCOL_VERSION,
        normalize_choice_output,
        request_for_record,
    )

EXP027 = "exp027-frozen-pool"
EXP028 = "exp028-legalbench-hearsay"
LABEL_ABSTAIN = "__insufficient_evidence__"


def load_records(path: Path, benchmark: str, partition: str, limit: int) -> list[dict[str, Any]]:
    rows = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    selected: list[dict[str, Any]] = []
    for row in rows:
        if benchmark == EXP027:
            if row.get("partition") != partition:
                continue
            record = row["record"]
        else:
            record = row
            if record.get("split") != "test" or partition != "test":
                continue
        selected.append(record)
        if limit and len(selected) >= limit:
            break
    if not selected:
        raise ValueError("no records matched the selected benchmark and partition")
    ids = [record["record_id"] for record in selected]
    if len(ids) != len(set(ids)):
        raise ValueError("selected records contain duplicate IDs")
    return selected


def _arm(arm_id: str, revisions_path: Path) -> dict[str, Any]:
    payload = json.loads(revisions_path.read_text(encoding="utf-8"))
    for item in payload["models"]:
        if item["arm_id"] == arm_id:
            return item
    raise ValueError(f"unknown arm: {arm_id}")


def _request_body(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "state": request["state"],
        "model": "kev-latest",
        "questions": {
            "decision": {
                "type": "choice",
                "instructions": request["question"],
                "criteria": {option["id"]: option["description"] for option in request["options"]},
            }
        },
    }


def _prediction(
    *,
    record_id: str,
    arm: dict[str, Any],
    status: str,
    label: str | None = None,
    probabilities: dict[str, float] | None = None,
    raw_scores: dict[str, float] | None = None,
    latency_ms: float | None = None,
    provider_metadata: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "judge_id": arm["model_id"],
        "protocol_version": PROTOCOL_VERSION,
        "label": label,
        "probabilities": probabilities,
        "raw_scores": raw_scores,
        "execution_status": status,
        "latency_ms": latency_ms,
        "provider_metadata": {
            "provider": "local",
            "arm_id": arm["arm_id"],
            "model_id": arm["model_id"],
            "model_revision": arm["model_revision"],
            "runtime_repository": arm["runtime_repository"],
            "runtime_revision": arm["runtime_revision"],
            "backend": arm["backend"],
            "precision": arm.get("precision"),
            "context_limit": arm["max_context_tokens"],
            **(provider_metadata or {}),
        },
        "error": error,
    }


def _backend_result(response: dict[str, Any], labels: list[str]) -> dict[str, Any]:
    answer = response.get("answers", {}).get("decision", {})
    selected = answer.get("choice", answer.get("selected_id", answer.get("selected_option_id")))
    probabilities = answer.get("probabilities", response.get("probabilities"))
    abstain_probability = answer.get("p_abstain", answer.get("abstention_probability"))
    raw_scores = answer.get("raw_scores", response.get("raw_scores"))
    normalized = normalize_choice_output(
        selected=selected,
        probabilities=probabilities,
        labels=labels,
        raw_scores=raw_scores,
    )
    if abstain_probability is not None:
        metadata = {"abstention_probability": float(abstain_probability)}
    else:
        metadata = {}
    normalized["metadata"] = metadata
    normalized["backend_latency_ms"] = response.get("latency_ms")
    normalized["input_tokens"] = response.get("usage", {}).get("input_tokens")
    normalized["raw_output"] = response
    return normalized


def _semif_predictor(arm: dict[str, Any]):
    from semif_phase1 import mlx_backend

    model, tokenizer, metadata = mlx_backend.load_model(
        arm["model_id"], arm["model_revision"], None, cache_limit_mib=256
    )

    def predict(request: dict[str, Any]) -> dict[str, Any]:
        row = {
            "id": request["record_id"],
            "state": request["state"],
            "question": request["question"],
            "options": request["options"],
        }
        started = time.perf_counter()
        result = mlx_backend.score(
            model, tokenizer, row, metadata, max_tokens=arm["max_context_tokens"]
        )
        selected_index = max(
            range(len(result["probabilities"])), key=result["probabilities"].__getitem__
        )
        return {
            "selected": request["labels"][selected_index],
            "probabilities": dict(zip(request["labels"], result["probabilities"], strict=True)),
            "raw_scores": dict(zip(request["labels"], result["option_logits"], strict=True)),
            "latency_ms": (time.perf_counter() - started) * 1000.0,
            "metadata": {
                "input_tokens": result.get("input_tokens"),
                "prompt_sha256": result.get("prompt_sha256"),
                "score_semantics": result.get("probability_status"),
                "runtime_metadata": metadata,
            },
        }

    return predict, metadata


def _kev_predictor(arm: dict[str, Any], workdir: Path):
    port = 8876
    log_path = workdir / "kev-server.log"
    log_handle = log_path.open("ab")
    model_ref = f"{arm['model_id']}@{arm['model_revision']}"
    process = subprocess.Popen(
        [sys.executable, "-m", "kev.serve", "--run", model_ref, "--port", str(port)],
        cwd=workdir,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        env=os.environ.copy(),
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 1800
    models: dict[str, Any] = {}
    while time.monotonic() < deadline:
        if process.poll() is not None:
            log_handle.close()
            raise RuntimeError(f"Kev server exited during model load; see {log_path}")
        try:
            models = _url_json(base_url + "/v1/models", method="GET")
            if models:
                break
        except Exception:  # noqa: BLE001 - server is still starting
            time.sleep(2)
    else:
        process.terminate()
        log_handle.close()
        raise TimeoutError(f"Kev server did not become ready; see {log_path}")

    def predict(request: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        response = _url_json(base_url + "/v1/systemone", _request_body(request))
        parsed = _backend_result(response, request["labels"])
        parsed["client_latency_ms"] = (time.perf_counter() - started) * 1000.0
        parsed["metadata"] = {**parsed.get("metadata", {}), "server_models": models}
        return parsed

    def close() -> None:
        process.terminate()
        try:
            process.wait(timeout=30)
        except Exception:  # noqa: BLE001 - best-effort process cleanup
            process.kill()
        log_handle.close()

    return predict, {"server_models": models, "server_log": str(log_path)}, close


def _laya_predictor(arm: dict[str, Any]):
    import laya
    from huggingface_hub import snapshot_download

    snapshot = snapshot_download(arm["model_id"], revision=arm["model_revision"])
    agent = laya.load(snapshot, device="mps")

    def predict(request: dict[str, Any]) -> dict[str, Any]:
        labels = request["labels"]
        question = {
            "type": "choice",
            "instructions": request["question"],
            "criteria": {option["id"]: option["description"] for option in request["options"]},
        }
        internal = {"decision": agent._to_internal(question)}
        full = agent._encode_state(
            request["state"], ["decision"], internal, max_len=100000, head_max_len=192
        )[0]["ids"]
        if len(full) > arm["max_context_tokens"]:
            raise ContextLimitError(len(full), arm["max_context_tokens"])
        started = time.perf_counter()
        result = agent.system_one(
            request["state"],
            {"decision": question},
            max_len=arm["max_context_tokens"],
            head_max_len=192,
        )
        parsed = _backend_result(result, labels)
        parsed["client_latency_ms"] = (time.perf_counter() - started) * 1000.0
        parsed["metadata"] = {
            **parsed.get("metadata", {}),
            "input_tokens": result.get("usage", {}).get("input_tokens"),
            "device": str(agent.device),
            "snapshot": snapshot,
        }
        return parsed

    return predict, {"snapshot": snapshot, "device": str(agent.device)}


def _verdict_predictor(arm: dict[str, Any]):
    from core.formatting import build_model_input, format_query
    from huggingface_hub import snapshot_download
    from rlcd import Choice, DecisionEngine, Option

    snapshot = snapshot_download(arm["model_id"], revision=arm["model_revision"])
    engine = DecisionEngine(
        model_name_or_path=snapshot,
        device="cpu",
        max_length=arm["max_context_tokens"],
    )

    def predict(request: dict[str, Any]) -> dict[str, Any]:
        query = Choice(
            id="decision",
            question=request["question"],
            options=tuple(Option(**option) for option in request["options"]),
        )
        _, labels, _ = format_query(str(request["state"]), query)
        prompt = build_model_input(query.question, str(request["state"]), labels)
        token_count = len(engine.tokenizer(prompt, truncation=False)["input_ids"])
        if token_count > arm["max_context_tokens"]:
            raise ContextLimitError(token_count, arm["max_context_tokens"])
        started = time.perf_counter()
        batch = engine.evaluate(str(request["state"]), [query])
        result = batch.results[0]
        raw_probabilities = dict(result.probabilities)
        selected = result.selected_id
        # Verdict adds an explicit abstention candidate. Keep its mass in metadata and
        # evaluate declared-label calibration conditionally on sufficient evidence.
        normalized = normalize_choice_output(
            selected=selected,
            probabilities=raw_probabilities,
            labels=request["labels"],
        )
        normalized["client_latency_ms"] = (time.perf_counter() - started) * 1000.0
        normalized["metadata"] = {
            "raw_probabilities_including_abstention": raw_probabilities,
            "abstention_probability": raw_probabilities.get(LABEL_ABSTAIN, 0.0),
            "is_abstention": bool(result.is_abstention),
            "calibration_status": result.calibration_status,
            "input_tokens": token_count,
            "snapshot": snapshot,
            "execution_mode": batch.execution_mode,
        }
        normalized["raw_output"] = {
            "selected_id": selected,
            "probabilities": raw_probabilities,
            "is_abstention": bool(result.is_abstention),
            "calibration_status": result.calibration_status,
            "latency_ms": result.latency_ms,
        }
        return normalized

    return predict, {"snapshot": snapshot, "device": "cpu", "max_length": arm["max_context_tokens"]}


class ContextLimitError(ValueError):
    def __init__(self, token_count: int, limit: int) -> None:
        super().__init__(f"{token_count} input tokens exceed {limit}; truncation is disabled")
        self.token_count = token_count
        self.limit = limit


def _url_json(
    url: str, payload: dict[str, Any] | None = None, *, method: str = "POST"
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"} if body is not None else {},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read())


def _versions() -> dict[str, str]:
    wanted = (
        "torch",
        "transformers",
        "mlx",
        "mlx-lm",
        "semif-phase1",
        "kev",
        "laya",
        "rlcd",
        "onnxruntime",
    )
    versions: dict[str, str] = {}
    for name in wanted:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return versions


def _write_lines(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        output.flush()
        os.fsync(output.fileno())


def run(args: argparse.Namespace) -> Path:
    arm = _arm(args.arm, args.model_revisions)
    records = load_records(args.input, args.benchmark, args.partition, args.limit)
    args.output.mkdir(parents=True, exist_ok=True)
    predictions_path = args.output / "predictions.jsonl"
    if predictions_path.exists() and not args.resume:
        raise FileExistsError(f"refusing to overwrite predictions: {predictions_path}")
    existing = (
        [
            json.loads(line)
            for line in predictions_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if args.resume and predictions_path.exists()
        else []
    )
    done = {row["record_id"] for row in existing}
    if len(done) != len(existing) or not done.issubset({record["record_id"] for record in records}):
        raise ValueError("resume file has duplicate or out-of-pool record IDs")
    remaining = [record for record in records if record["record_id"] not in done]
    if not remaining:
        print(f"All {len(records)} selected records already have predictions: {predictions_path}")
        return predictions_path
    (args.output / "run-config.json").write_text(
        json.dumps(
            {
                "arm": arm,
                "benchmark": args.benchmark,
                "partition": args.partition,
                "record_ids": [record["record_id"] for record in records],
                "selected_count": len(records),
                "protocol_version": PROTOCOL_VERSION,
                "runner_revision": args.runner_revision,
                "python": sys.version,
                "platform": sys.platform,
                "package_versions": _versions(),
                "resume": args.resume,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    close_model = lambda: None
    try:
        if arm["arm_id"].startswith("semif-"):
            predictor, model_metadata = _semif_predictor(arm)
        elif arm["arm_id"].startswith("kev-"):
            predictor, model_metadata, close_model = _kev_predictor(arm, args.output)
        elif arm["arm_id"] == "laya-421m":
            predictor, model_metadata = _laya_predictor(arm)
        elif arm["arm_id"] in {"verdict-1.4", "verdict-original"}:
            predictor, model_metadata = _verdict_predictor(arm)
        else:
            raise RuntimeError("this arm is pre-registered as hardware-infeasible")
    except Exception as exc:  # model load errors are preserved per selected record
        failures = [
            _prediction(
                record_id=record["record_id"],
                arm=arm,
                status="provider_error",
                error={
                    "kind": "model_load_error",
                    "type": type(exc).__name__,
                    "message": str(exc)[:500],
                },
                provider_metadata={"model_load_failed": True},
            )
            for record in remaining
        ]
        _write_lines(predictions_path, failures)
        raise

    metadata_path = args.output / "runtime-metadata.json"
    metadata_path.write_text(
        json.dumps(
            {"model_runtime": model_metadata, "package_versions": _versions()},
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        for index, record in enumerate(remaining, start=1):
            request = request_for_record(record, args.benchmark)
            started = time.perf_counter()
            try:
                output = predictor(request)
                result = (
                    output
                    if "ok" in output
                    else normalize_choice_output(
                        selected=output.get("selected"),
                        probabilities=output.get("probabilities"),
                        raw_scores=output.get("raw_scores"),
                        labels=request["labels"],
                    )
                )
                status = (
                    "ok"
                    if result.get("ok")
                    else "skipped"
                    if result.get("abstained")
                    else "parse_error"
                )
                error = (
                    None
                    if status == "ok"
                    else {
                        "kind": "abstention"
                        if result.get("abstained")
                        else "prediction_parse_error",
                        "reason": result.get("error"),
                    }
                )
                provider_metadata = {
                    **output.get("metadata", {}),
                    "raw_probabilities": result.get("raw_probabilities"),
                    "probability_semantics": result.get("probability_semantics"),
                    "raw_output": output.get("raw_output"),
                    "backend_latency_ms": output.get("latency_ms"),
                    "client_latency_ms": output.get("client_latency_ms"),
                }
                prediction = _prediction(
                    record_id=record["record_id"],
                    arm=arm,
                    status=status,
                    label=result.get("label") if status == "ok" else None,
                    probabilities=result.get("probabilities") if status == "ok" else None,
                    raw_scores=result.get("raw_scores") if status == "ok" else None,
                    latency_ms=(time.perf_counter() - started) * 1000.0,
                    provider_metadata=provider_metadata,
                    error=error,
                )
            except ContextLimitError as exc:
                prediction = _prediction(
                    record_id=record["record_id"],
                    arm=arm,
                    status="skipped",
                    latency_ms=(time.perf_counter() - started) * 1000.0,
                    error={
                        "kind": "context_limit",
                        "message": str(exc),
                        "tokens": exc.token_count,
                        "limit": exc.limit,
                    },
                )
            except Exception as exc:  # noqa: BLE001 - preserve per-record runtime status
                prediction = _prediction(
                    record_id=record["record_id"],
                    arm=arm,
                    status="provider_error",
                    latency_ms=(time.perf_counter() - started) * 1000.0,
                    error={
                        "kind": "local_runtime_error",
                        "type": type(exc).__name__,
                        "message": str(exc)[:500],
                    },
                )
            _write_lines(predictions_path, [prediction])
            if index % 25 == 0 or index == len(remaining):
                all_rows = [
                    json.loads(line)
                    for line in predictions_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                counts = Counter(row["execution_status"] for row in all_rows)
                progress = {
                    "arm_id": arm["arm_id"],
                    "selected_count": len(records),
                    "completed_count": len(all_rows),
                    "status_counts": dict(sorted(counts.items())),
                    "last_record_id": prediction["record_id"],
                    "updated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                (args.output / "progress.json").write_text(
                    json.dumps(progress, indent=2) + "\n", encoding="utf-8"
                )
                print(json.dumps(progress), flush=True)
    finally:
        close_model()
    return predictions_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", choices=(EXP027, EXP028), required=True)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--model-revisions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runner-revision", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    path = run(args)
    print(path)


if __name__ == "__main__":
    main()
