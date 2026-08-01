"""One bounded CKFF gateway request, with no retries and no redirects.

Two properties matter more than anything else this script does.

**It never retries.** A single request, no loop, no backoff. urllib's default
opener has no retry handler, and this builds its opener explicitly so that stays
true if the standard library changes.

**It never follows a redirect.** urllib's default opener *does* include
``HTTPRedirectHandler``, which copies request headers -- ``Authorization``
included -- into the redirected request. Unlike ``requests`` it does not strip
credentials when the redirect crosses to another host, and it permits an
``http://`` target. So the HTTPS check on the base URL below can be defeated by
any endpoint answering ``302 Location: http://elsewhere/``: the bearer token
would leave in cleartext, to a host nobody configured. Refusing every redirect
is the only version of this that holds without reasoning case by case, so the
opener installs a handler that raises instead of following, and the diagnostic
names *why* the target was refused -- downgrade, cross-origin, or simply that
redirects are not accepted here.

A redirect is never a legitimate answer for this endpoint anyway. A gateway that
starts issuing them has changed in a way that should stop the run, not be
absorbed by it.

Emits only metadata and a SHA-256 of the returned content: never the model's
reply, never a request header, never the key.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

#: Response headers safe to record. Everything else is dropped rather than
#: filtered, so a new header cannot reach an artifact by default.
RECORDED_RESPONSE_HEADERS = ("x-request-id",)

#: Anything key-shaped is redacted before an upstream error body is printed.
#: Actions masks the exact secret but not a truncated or reformatted rendering
#: of it, and a gateway auth error is both the likeliest first result of a
#: connectivity test and the likeliest to echo key material back.
_KEY_SHAPED = re.compile(r"sk-[A-Za-z0-9_\-]{6,}")

REQUEST_TIMEOUT_SECONDS = 120


class RedirectRefused(RuntimeError):
    """The gateway answered with a redirect, which this client will not follow."""


class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """Raise on every redirect instead of re-issuing the request.

    Subclassing rather than dropping the handler is deliberate: with no redirect
    handler at all a 3xx surfaces as a generic ``HTTPError`` and the reason is
    lost. Here the refusal can say whether the target was a scheme downgrade, a
    different origin, or neither -- the difference between "someone reconfigured
    the gateway" and "someone is trying to collect the key".
    """

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        raise RedirectRefused(
            f"gateway answered HTTP {code} redirecting to "
            f"{describe_redirect(req.full_url, newurl)}. This client does not "
            "follow redirects: urllib would copy the Authorization header to the "
            "target, including across origins and onto plain http, so a redirect "
            "is a credential-disclosure path rather than a routing detail"
        )


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urllib.parse.urlsplit(url)
    return (parsed.scheme, parsed.hostname or "", parsed.port)


def describe_redirect(from_url: str, to_url: str) -> str:
    """Name the target and why it is refused, without echoing the query string."""
    from_scheme, from_host, from_port = _origin(from_url)
    to_scheme, to_host, to_port = _origin(urllib.parse.urljoin(from_url, to_url))

    target = f"{to_scheme}://{to_host}" if to_host else to_url
    if from_scheme == "https" and to_scheme != "https":
        return f"{target} (refused: HTTPS-to-{to_scheme or 'unknown'} downgrade)"
    if (to_scheme, to_host, to_port) != (from_scheme, from_host, from_port):
        return f"{target} (refused: cross-origin)"
    return f"{target} (refused: redirects are not followed)"


def build_opener() -> urllib.request.OpenerDirector:
    """An opener that cannot retry and cannot follow a redirect."""
    opener = urllib.request.build_opener(_RefuseRedirects)
    for handler in opener.handlers:
        if type(handler) is urllib.request.HTTPRedirectHandler:  # pragma: no cover
            raise RuntimeError(
                "the default redirect-following handler is still installed; "
                "Authorization could reach a redirect target"
            )
    return opener


def require_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def validate_base_url(base_url: str) -> str:
    """Reject a base URL the request path cannot be trusted with."""
    base_url = base_url.rstrip("/")
    if not base_url.startswith("https://"):
        raise RuntimeError("CKFF_BASE_URL must use HTTPS")
    if "/v1" in base_url.removeprefix("https://"):
        raise RuntimeError("CKFF_BASE_URL must not include /v1")
    return base_url


def redact(text: str) -> str:
    return _KEY_SHAPED.sub("sk-REDACTED", text)


def post_json(
    url: str,
    payload: dict[str, Any],
    api_key: str,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> tuple[int, bytes, dict[str, str | None], float]:
    """One request, one attempt, no redirect. Returns status, body, headers, elapsed."""
    # S310 (permitted-scheme audit): the scheme is validated at the boundary by
    # validate_base_url, and _RefuseRedirects means no other scheme can be
    # reached afterwards — which is exactly the hole S310 exists to flag.
    request = urllib.request.Request(  # noqa: S310
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "eval-lab-ckff-smoke/1",
        },
        method="POST",
    )
    opener = build_opener()
    started = time.monotonic()
    try:
        with opener.open(request, timeout=timeout) as response:  # noqa: S310
            raw = response.read()
            status = response.status
            recorded = {name: response.headers.get(name) for name in RECORDED_RESPONSE_HEADERS}
    except RedirectRefused:
        raise
    except urllib.error.HTTPError as exc:
        body = redact(exc.read(500).decode("utf-8", errors="replace"))
        raise RuntimeError(f"gateway returned HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"gateway request failed: {exc.reason}") from exc
    except (TimeoutError, OSError) as exc:
        # urlopen wraps connect-phase OSError into URLError, but response.read()
        # runs afterwards and can still raise a bare TimeoutError or IncompleteRead.
        raise RuntimeError(f"gateway request failed while reading: {exc}") from exc
    return status, raw, recorded, round(time.monotonic() - started, 3)


def main() -> int:
    base_url = validate_base_url(require_environment("CKFF_BASE_URL"))
    api_key = require_environment("CKFF_API_KEY")
    model = require_environment("CKFF_MODEL")

    if len(api_key) < 16:
        raise RuntimeError("CKFF_API_KEY does not look like a usable restricted key")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with exactly OK."}],
        "temperature": 0,
        "max_tokens": 8,
    }

    status, raw, headers, elapsed = post_json(f"{base_url}/v1/chat/completions", payload, api_key)

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
        "request_id": headers.get("x-request-id"),
        "client_retry_count": 0,
        "redirects_followed": 0,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as exc:
        print(f"CKFF smoke check failed: {redact(str(exc))}", file=sys.stderr)
        raise SystemExit(1) from exc
