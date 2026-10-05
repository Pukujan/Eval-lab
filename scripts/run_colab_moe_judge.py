"""Label-only judge runner for the Google Colab T4 compute path.

Serves a GGUF with ``llama-server``, then for each frozen typed-choice request
asks the model for exactly one legal label under a GBNF grammar.  Every
prediction is appended to the output JSONL and fsynced immediately, so a killed
free-tier session resumes by skipping record IDs already present.  No gold label
is read.

The request protocol is the frozen EXP-027 typed-choice protocol
(``eval_lab.judges.local_decision_models.request_for_record``); requests are
built offline by ``scripts/build_colab_moe_requests.py``.

Reasoning models (for example Ornith) put grammar-constrained output in
``reasoning_content`` when thinking is enabled, leaving ``content`` empty.  This
runner disables the chat template's thinking block and, as a belt-and-braces
measure, falls back to ``reasoning_content`` if ``content`` is empty.

Usage (on the Colab VM):
    python3 run_colab_moe_judge.py \
        --model /content/ornith.gguf \
        --requests /content/requests_blind.jsonl \
        --output /content/pred_ornith_blind.jsonl \
        --arm-id ornith-1.5-35b-a3b
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, cast

LLAMA = "/content/llama/llama-b11399"
CUDART = "/content/llama/cudart-llama-b11399-bin-ubuntu-cuda-12.8-x64"
SERVER_LOG = "/content/llama-server.log"

SYSTEM = (
    "You are a strict grading judge. You receive a decision request and must "
    "answer with exactly one of the legal labels. Reply with the label only."
)


def grammar_for(labels: list[str]) -> str:
    """A GBNF grammar that admits exactly one of ``labels`` and nothing else."""
    return "root ::= " + " | ".join(f'"{label}"' for label in labels) + "\n"


def user_prompt(req: dict) -> str:
    opts = "\n".join(f"- {o['id']}: {o['description']}" for o in req["options"])
    labels = " | ".join(req["labels"])
    return (
        f"Question: {req['question']}\n\n"
        f"Options:\n{opts}\n\n"
        f"Item:\n{req['state']}\n\n"
        f"Answer with exactly one legal label ({labels}) and nothing else."
    )


def extract_label(message: dict, labels: list[str]) -> tuple[str | None, str]:
    """Return ``(label, raw_text)`` from a chat message.

    ``content`` is preferred; ``reasoning_content`` is used only when ``content``
    is empty.  A model that emitted a legal label in either channel is resolved;
    anything else is a parse failure.
    """
    text = (message.get("content") or message.get("reasoning_content") or "").strip()
    return (text if text in labels else None), text


def post(url: str, payload: dict, timeout: float) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        return cast(dict[str, Any], json.loads(resp.read().decode("utf-8")))


def wait_ready(base: str, proc: subprocess.Popen, timeout: float = 900.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("llama-server exited during startup")
        try:
            with urllib.request.urlopen(base + "/health", timeout=5) as resp:
                if json.loads(resp.read().decode("utf-8")).get("status") == "ok":
                    return
        except Exception:  # noqa: BLE001 - server is still starting
            time.sleep(3)
    raise TimeoutError("llama-server did not become ready")


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def run(args: argparse.Namespace) -> None:
    base = f"http://127.0.0.1:{args.port}"
    requests = load_jsonl(args.requests)
    if args.limit:
        requests = requests[: args.limit]

    done: set[str] = set()
    if args.output.exists():
        done = {row["record_id"] for row in load_jsonl(args.output)}
    todo = [r for r in requests if r["record_id"] not in done]
    print(f"arm={args.arm_id} total={len(requests)} done={len(done)} todo={len(todo)}", flush=True)
    if not todo:
        print("nothing to do")
        return

    env = {
        **os.environ,
        "LD_LIBRARY_PATH": f"{LLAMA}:{CUDART}:/usr/lib64-nvidia:/usr/local/cuda/lib64:"
        + os.environ.get("LD_LIBRARY_PATH", ""),
    }
    with open(SERVER_LOG, "ab") as log:
        proc = subprocess.Popen(
            [
                f"{LLAMA}/llama-server",
                "-m",
                args.model,
                "-ngl",
                "99",
                "-t",
                "2",
                "-c",
                str(args.ctx),
                "--host",
                "127.0.0.1",
                "--port",
                str(args.port),
                "-np",
                "1",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
        )
        try:
            wait_ready(base, proc)
            print("server ready", flush=True)
            with args.output.open("a", encoding="utf-8") as out:
                for i, req in enumerate(todo, 1):
                    started = time.perf_counter()
                    row: dict = {
                        "record_id": req["record_id"],
                        "mode": req["mode"],
                        "legal_labels": req["labels"],
                        "arm_id": args.arm_id,
                    }
                    try:
                        resp = post(
                            base + "/v1/chat/completions",
                            {
                                "messages": [
                                    {"role": "system", "content": SYSTEM},
                                    {"role": "user", "content": user_prompt(req)},
                                ],
                                "grammar": grammar_for(req["labels"]),
                                "temperature": 0.0,
                                "max_tokens": 8,
                                "cache_prompt": True,
                                "chat_template_kwargs": {"enable_thinking": False},
                            },
                            timeout=args.request_timeout,
                        )
                        label, text = extract_label(resp["choices"][0]["message"], req["labels"])
                        row.update(
                            execution_status="ok" if label is not None else "parse_error",
                            label=label,
                            raw_output=text[:200],
                            usage=resp.get("usage"),
                        )
                    except Exception as exc:  # noqa: BLE001 - preserve per-record status
                        row.update(
                            execution_status="provider_error",
                            label=None,
                            error={"kind": type(exc).__name__, "message": str(exc)[:300]},
                        )
                    row["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    out.flush()
                    os.fsync(out.fileno())
                    if i % 10 == 0 or i == len(todo):
                        print(
                            f"  {i}/{len(todo)} {row['execution_status']} {row.get('label')}",
                            flush=True,
                        )
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("=== RUNNER DONE ===", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--model", required=True)
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arm-id", required=True)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--ctx", type=int, default=8192)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--request-timeout", type=float, default=240.0)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
