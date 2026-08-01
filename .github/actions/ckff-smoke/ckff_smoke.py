from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request


def require_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def main() -> int:
    base_url = require_environment("CKFF_BASE_URL").rstrip("/")
    api_key = require_environment("CKFF_API_KEY")
    model = require_environment("CKFF_MODEL")

    if not base_url.startswith("https://"):
        raise RuntimeError("CKFF_BASE_URL must use HTTPS")
    if "/v1" in base_url.removeprefix("https://"):
        raise RuntimeError("CKFF_BASE_URL must not include /v1")
    if len(api_key) < 16:
        raise RuntimeError("CKFF_API_KEY does not look like a usable restricted key")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with exactly OK."}],
        "temperature": 0,
        "max_tokens": 8,
    }
    request = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "eval-lab-ckff-smoke/1",
        },
        method="POST",
    )

    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
            raw = response.read()
            status = response.status
            request_id = response.headers.get("x-request-id")
    except urllib.error.HTTPError as exc:
        body = exc.read(500).decode("utf-8", errors="replace")
        raise RuntimeError(f"gateway returned HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"gateway request failed: {exc.reason}") from exc

    elapsed = round(time.monotonic() - started, 3)
    response_payload = json.loads(raw)
    choices = response_payload.get("choices") or []
    if not choices:
        raise RuntimeError("gateway response contained no choices")

    content = str(choices[0].get("message", {}).get("content", ""))
    usage = response_payload.get("usage") or {}
    summary = {
        "status": status,
        "requested_model": model,
        "resolved_model": response_payload.get("model"),
        "elapsed_seconds": elapsed,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "request_id": request_id,
        "client_retry_count": 0,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as exc:
        print(f"CKFF smoke check failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
