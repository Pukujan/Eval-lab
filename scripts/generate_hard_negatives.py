"""Generate and independently verify TASK-0008 teacher hard negatives."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from eval_lab.datasets.synthetic import generate_synthetic_fixtures
from eval_lab.schema import JudgeRecord, Split
from eval_lab.verifiers.arithmetic import verify_arithmetic
from eval_lab.verifiers.code_output import verify_code_output
from eval_lab.verifiers.multiple_choice import verify_multiple_choice
from eval_lab.verifiers.structured import verify_structured_output

MODEL_ID = "qwen3.8-flash"
CONTEXT_LIMIT = 4096
VERIFIERS: dict[str, Callable[[str, Any], Any]] = {
    "arithmetic-v1": verify_arithmetic,
    "multiple-choice-v1": verify_multiple_choice,
    "structured-output-v1": verify_structured_output,
    "code-output-v1": verify_code_output,
}
DOMAIN_FAILURE_MODE = {
    "arithmetic": "arithmetic_near_miss",
    "multiple_choice": "multiple_choice_distractor",
    "structured": "structured_field_mutation",
    "code_output": "code_output_mutation",
}


def _load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _teacher_prompt(source: Any, record: JudgeRecord) -> str:
    criterion = "\n".join(
        f"- {item.criterion_id}: {item.description}" for item in record.rubric
    )
    return (
        "Generate one plausible but incorrect candidate answer for this objective problem. "
        "The correct answer is intentionally not provided. Preserve the requested answer format. "
        "Return only JSON with string fields candidate, failure_mode, and rationale. "
        "Do not include the answer key or claim the candidate is correct.\n\n"
        f"Domain: {source.domain}\n"
        f"Question: {source.prompt}\n"
        f"Rubric:\n{criterion}\n"
        "Candidate JSON:"
    )


def _parse_payload(content: str) -> dict[str, str] | None:
    candidates = [content.strip()]
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        required = ("candidate", "failure_mode", "rationale")
        if not all(isinstance(payload.get(key), str) for key in required):
            continue
        if not payload["candidate"].strip():
            continue
        return {key: payload[key].strip() for key in required}
    return None


def _failure_mode(domain: str, proposed: str) -> str:
    allowed = set(DOMAIN_FAILURE_MODE.values()) | {"unsupported_claim", "format_confusion", "other"}
    return proposed if proposed in allowed else DOMAIN_FAILURE_MODE[domain]


def _prediction_error(
    *,
    source: Any,
    request_id: str,
    status: str,
    reason: str,
    elapsed_ms: float,
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "source_problem_id": source.source_problem_id,
        "source_split": source.split.value,
        "domain": source.domain,
        "status": status,
        "reason": reason,
        "latency_ms": round(elapsed_ms, 3),
    }


def _generate_one(
    source: Any,
    record: JudgeRecord,
    *,
    env: dict[str, str],
    request_id: str,
    timeout: float,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    started = time.perf_counter()
    api_key = env.get("YOLO_AUTO_API_KEY") or env.get("QWEN_API_KEY")
    base_url = env.get("QWEN_API_URL", "https://yolo-auto.com/v1").rstrip("/")
    prompt = _teacher_prompt(source, record)
    request = {
        "request_id": request_id,
        "provider": "yolo-auto",
        "model_id": MODEL_ID,
        "source_problem_id": source.source_problem_id,
        "source_split": source.split.value,
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "context_limit": CONTEXT_LIMIT,
    }
    if not api_key:
        return request, _prediction_error(
            source=source,
            request_id=request_id,
            status="provider_error",
            reason="missing_credential",
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": MODEL_ID,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 256,
                "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout=timeout,
        )
    except httpx.TimeoutException:
        return request, _prediction_error(
            source=source,
            request_id=request_id,
            status="provider_error",
            reason="timeout",
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    except httpx.HTTPError as exc:
        return request, _prediction_error(
            source=source,
            request_id=request_id,
            status="provider_error",
            reason=type(exc).__name__,
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    if response.status_code == 429:
        return request, _prediction_error(
            source=source,
            request_id=request_id,
            status="rate_limited",
            reason=str(response.headers.get("retry-after", "unknown")),
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    if response.status_code >= 400:
        return request, _prediction_error(
            source=source,
            request_id=request_id,
            status="provider_error",
            reason=f"http_{response.status_code}",
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    try:
        payload = response.json()
        returned_model = str(payload.get("model", ""))
        content = ((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    except (ValueError, IndexError, AttributeError, TypeError):
        return request, _prediction_error(
            source=source,
            request_id=request_id,
            status="parse_error",
            reason="invalid_json_response",
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    request["returned_model"] = returned_model
    if returned_model != MODEL_ID:
        return request, _prediction_error(
            source=source,
            request_id=request_id,
            status="provider_error",
            reason="model_identity_mismatch",
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    parsed = _parse_payload(str(content))
    if parsed is None:
        return request, _prediction_error(
            source=source,
            request_id=request_id,
            status="parse_error",
            reason="structured_payload_not_found",
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    request["status"] = "ok"
    request["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
    request["failure_mode"] = _failure_mode(source.domain, parsed["failure_mode"])
    request["rationale_length"] = len(parsed["rationale"])
    request["_candidate"] = parsed["candidate"]
    request["_rationale"] = parsed["rationale"]
    return request, None


def _verify_candidate(source: Any, candidate: str) -> dict[str, Any]:
    verifier_id = str(source.source_metadata["verifier"])
    verifier = VERIFIERS[verifier_id]
    result = verifier(candidate, source.reference_answer)
    return {
        "is_correct": bool(result.is_correct),
        "verifier_id": result.verifier_id,
        "evidence": result.evidence,
    }


def _clean_request(request: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in request.items() if not key.startswith("_")}


def _ansi_clean(value: str) -> str:
    return re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\a]*\a", "", value)


def _run_opencode_audit(model: str, batch: list[dict[str, Any]], *, timeout: float) -> dict[str, Any]:
    compact = [
        {
            "record_id": item["record_id"],
            "prompt": item["record"]["prompt"],
            "candidate_a": item["record"]["candidate_a"],
            "candidate_b": item["record"].get("candidate_b"),
            "local_label": (item.get("local_prediction") or {}).get("label"),
        }
        for item in batch
    ]
    if len(compact) == 1:
        prompt = (
            "You are auditing one objective judge case. Do not create an answer key. "
            "Return exactly one JSON object that copies the record_id and contains assessment "
            "(keep_for_review, likely_error, or ambiguous) and concise review_notes.\n\n"
            + json.dumps(compact[0], sort_keys=True)
        )
    else:
        prompt = (
            "Review this batch of objective judge cases. Do not infer or create answer keys. "
            "Return only a JSON array with one object per record containing record_id, assessment, "
            "and concise review_notes. assessment must be one of keep_for_review, likely_error, or ambiguous.\n\n"
            + json.dumps(compact, sort_keys=True)
        )
    executable = shutil.which("opencode") or "opencode"
    process = subprocess.Popen(
        [
            executable,
            "run",
            "--model",
            model,
            "--format",
            "json",
            "--log-level",
            "ERROR",
            "--dir",
            str(Path.cwd()),
            prompt,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            text=True,
            check=False,
        )
        return {"status": "provider_error", "model": model, "reason": "timeout", "items": []}
    output = _ansi_clean((stdout or "") + "\n" + (stderr or ""))
    text_parts: list[str] = []
    for line in output.splitlines():
        try:
            event = json.loads(line.strip())
        except json.JSONDecodeError:
            continue
        if event.get("type") == "text":
            part = event.get("part") or {}
            if isinstance(part.get("text"), str):
                text_parts.append(part["text"])
    text = "\n".join(text_parts)
    match = re.search(r"\[.*\]", text, re.DOTALL) or re.search(r"\{.*\}", text, re.DOTALL)
    if process.returncode != 0 or not match:
        return {
            "status": "parse_error" if process.returncode == 0 else "provider_error",
            "model": model,
            "reason": "audit_json_not_found" if process.returncode == 0 else f"process_exit_{process.returncode}",
            "items": [],
        }
    try:
        parsed = json.loads(match.group(0))
        items = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        items = []
    expected = {item["record_id"] for item in batch}
    valid = [
        item
        for item in items
        if isinstance(item, dict)
        and item.get("record_id") in expected
        and item.get("assessment") in {"keep_for_review", "likely_error", "ambiguous"}
        and isinstance(item.get("review_notes"), str)
    ]
    if {item["record_id"] for item in valid} != expected:
        return {"status": "parse_error", "model": model, "reason": "incomplete_audit_batch", "items": valid}
    return {"status": "ok", "model": model, "reason": None, "items": valid}


def _audit_batch(
    path: Path, model: str, *, timeout: float, single_item_requests: bool = False
) -> dict[str, Any]:
    batch = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not single_item_requests:
        result = _run_opencode_audit(model, batch, timeout=timeout)
        result["input_record_ids"] = [item["record_id"] for item in batch]
        return result
    items: list[dict[str, Any]] = []
    for item in batch:
        result = _run_opencode_audit(model, [item], timeout=timeout)
        items.extend(result.get("items", []))
        if result.get("status") != "ok":
            return {
                "status": result.get("status"),
                "model": model,
                "reason": result.get("reason"),
                "items": items,
                "input_record_ids": [entry["record_id"] for entry in batch],
            }
    return {
        "status": "ok",
        "model": model,
        "reason": None,
        "items": items,
        "input_record_ids": [entry["record_id"] for entry in batch],
    }


def _write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(value, sort_keys=True) for value in values) + "\n",
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> Path:
    output_dir = Path(args.output_dir)
    experiment_id = output_dir.name
    existing = {path.name for path in output_dir.iterdir()} if output_dir.exists() else set()
    if existing - {"README.md", "experiment.yaml"}:
        raise FileExistsError(f"refusing to overwrite existing experiment: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    env = {**_load_dotenv(Path(args.env_file)), **os.environ}
    fixture = generate_synthetic_fixtures()
    sources = sorted((source for source in fixture.sources if source.split is not Split.TEST), key=lambda item: item.source_problem_id)
    if args.limit:
        sources = sources[: args.limit]
    single_by_source = {
        record.source_problem_id: record
        for record in fixture.records
        if record.mode.value == "single"
    }
    requests: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    stopped_reason: str | None = None
    for index, source in enumerate(sources, 1):
        request_id = f"teacher-{index:03d}-{source.source_problem_id}"
        if stopped_reason:
            rejected.append(
                _prediction_error(
                    source=source,
                    request_id=request_id,
                    status="skipped",
                    reason=stopped_reason,
                    elapsed_ms=0,
                )
            )
            continue
        request, error = _generate_one(
            source,
            single_by_source[source.source_problem_id],
            env=env,
            request_id=request_id,
            timeout=args.timeout,
        )
        if error:
            rejected.append(error)
            requests.append(_clean_request(request))
            if error["status"] in {"rate_limited"}:
                stopped_reason = error["reason"]
            continue
        candidate = request.pop("_candidate")
        rationale = request.pop("_rationale")
        verification = _verify_candidate(source, candidate)
        request["verification"] = verification
        if verification["is_correct"]:
            rejected.append(
                {
                    **_clean_request(request),
                    "status": "rejected",
                    "reason": "teacher_candidate_verified_correct",
                    "candidate": candidate,
                }
            )
            requests.append(_clean_request(request))
            continue
        accepted.append(
            {
                "record_id": f"hard-negative:{source.source_problem_id}:001",
                "source_problem_id": source.source_problem_id,
                "split": source.split.value,
                "domain": source.domain,
                "prompt": source.prompt,
                "candidate": candidate,
                "failure_mode": request["failure_mode"],
                "teacher": {
                    "provider": "yolo-auto",
                    "model_id": MODEL_ID,
                    "request_id": request["request_id"],
                    "rationale": rationale,
                },
                "gold": {
                    "label": "fail",
                    "provenance": "deterministic_verifier",
                    "evidence": verification["evidence"],
                    "verifier_id": verification["verifier_id"],
                },
            }
        )
        requests.append(_clean_request(request))
    audit_input = Path(args.audit_input)
    luna = _audit_batch(audit_input / "luna_audit_batch.jsonl", "opencode/gpt-5.6-luna", timeout=args.audit_timeout)
    sol = _audit_batch(
        audit_input / "sol_hard_disagreement_batch.jsonl",
        "opencode/gpt-5.6-sol",
        timeout=args.audit_timeout,
        single_item_requests=True,
    )
    taxonomy = Counter(item["failure_mode"] for item in accepted)
    rejection_counts = Counter(item["reason"] for item in rejected)
    metadata = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "provider": "yolo-auto",
        "model_id": MODEL_ID,
        "base_url": env.get("QWEN_API_URL", "https://yolo-auto.com/v1"),
        "context_limit": CONTEXT_LIMIT,
        "source_count": len(sources),
        "source_splits": Counter(source.split.value for source in sources),
        "source_domains": Counter(source.domain for source in sources),
        "request_count": len(requests),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "luna_audit": {key: value for key, value in luna.items() if key != "items"},
        "sol_audit": {key: value for key, value in sol.items() if key != "items"},
        "runtime": {"platform": platform.platform(), "python": platform.python_version()},
    }
    summary = {
        "experiment_id": experiment_id,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "verification_rate": len(accepted) / len(requests) if requests else 0.0,
        "failure_mode_counts": dict(sorted(taxonomy.items())),
        "rejection_reason_counts": dict(sorted(rejection_counts.items())),
        "source_split_coverage": dict(Counter(item["split"] for item in accepted)),
        "source_domain_coverage": dict(Counter(item["domain"] for item in accepted)),
        "teacher_paths": {
            "yolo_auto": {"status": "completed", "accepted": len(accepted)},
            "supergrok": {
                "status": "unavailable_provider_blocked",
                "model": "opencode/grok-4.6",
                "reason": "TASK-0007 integration timed out",
            },
            "luna": {key: value for key, value in luna.items() if key != "items"},
            "sol": {key: value for key, value in sol.items() if key != "items"},
        },
    }
    _write_jsonl(output_dir / "teacher_request_manifest.jsonl", requests)
    _write_jsonl(output_dir / "verified_hard_negatives.jsonl", accepted)
    _write_jsonl(output_dir / "rejected_generations.jsonl", rejected)
    _write_jsonl(output_dir / "rubric_paraphrases.jsonl", [
        {
            "domain": domain,
            "source": "deterministic-template",
            "criterion_id": "objective-correctness",
            "paraphrase": text,
            "objective_gold_unchanged": True,
        }
        for domain, text in {
            "arithmetic": "The response must equal the numeric answer key.",
            "multiple_choice": "The response must select the answer-key option.",
            "structured": "The response must match the required JSON object exactly.",
            "code_output": "The response must match the expected normalized output.",
        }.items()
    ])
    (output_dir / "teacher_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    (output_dir / "failure_mode_taxonomy.json").write_text(
        json.dumps(
            {
                "modes": sorted(set(DOMAIN_FAILURE_MODE.values()) | {"unsupported_claim", "format_confusion", "other"}),
                "accepted_counts": dict(sorted(taxonomy.items())),
                "rejected_counts": dict(sorted(rejection_counts.items())),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "teacher_disagreement_summary.json").write_text(
        json.dumps(summary["teacher_paths"], indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    _write_jsonl(output_dir / "luna_audit_results.jsonl", luna["items"])
    _write_jsonl(output_dir / "sol_audit_results.jsonl", sol["items"])
    (output_dir / "results.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    report = [
        "# TASK-0008 Verified Teacher-Assisted Hard Negatives",
        "",
        f"Generated source families: {len(sources)}; accepted independently verified hard negatives: {len(accepted)}.",
        "",
        f"Verification rate among requests: {summary['verification_rate']:.3f}. Test sources were excluded.",
        "",
        f"Failure modes: {dict(sorted(taxonomy.items()))}",
        f"Rejection reasons: {dict(sorted(rejection_counts.items()))}",
        "",
        f"Luna audit status: {luna['status']}; Sol audit status: {sol['status']}.",
        "SuperGrok was recorded as unavailable/provider-blocked from TASK-0007 and was not substituted silently.",
        "",
        "## Limitations",
        "",
        "Teacher proposals are weak supervision metadata. Every accepted candidate is independently rejected by a deterministic verifier before entering the corpus, and no test source is included.",
    ]
    (output_dir / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = {
        "id": experiment_id,
        "status": "completed",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "code_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip(),
        "seed": 20260920,
        "context_limit": CONTEXT_LIMIT,
        "dataset": {
            "name": "eval-lab-synthetic-objective-v1",
            "fingerprint": generate_synthetic_fixtures().fingerprint,
            "source_problem_ids": [source.source_problem_id for source in sources],
            "excluded_test_source_count": 4,
        },
        "teacher_model": MODEL_ID,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "audit_paths": ["opencode/gpt-5.6-luna", "opencode/gpt-5.6-sol"],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--audit-timeout", type=float, default=120)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument(
        "--audit-input",
        default="experiments/EXP-20260920-003-external-judge-bakeoff",
    )
    parser.add_argument(
        "--output-dir",
        default="experiments/EXP-20260920-004-teacher-hard-negatives",
    )
    args = parser.parse_args()
    print(run(args))


if __name__ == "__main__":
    main()
