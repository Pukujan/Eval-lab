"""The CKFF smoke client must never let a redirect carry the credential away.

Every test here runs against a throwaway HTTP server on loopback. No CKFF
request, no gateway, no network beyond 127.0.0.1 — a test that had to reach the
real gateway to prove the key is safe would be self-defeating.

The threat is specific and easy to miss. urllib's default opener follows
redirects and, unlike ``requests``, copies ``Authorization`` to the target even
when the target is a different host or plain ``http``. So the HTTPS check on the
base URL protects only the *first* hop. The decisive assertion below is not that
the client raised — it is that the redirect target's request log is **empty**.
"""

from __future__ import annotations

import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SMOKE_PATH = REPOSITORY_ROOT / ".github" / "actions" / "ckff-smoke" / "ckff_smoke.py"


def _load_smoke_module() -> Any:
    """Import the action script by path — it is not an installed package."""
    spec = importlib.util.spec_from_file_location("ckff_smoke", SMOKE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


smoke = _load_smoke_module()


class _RecordingServer:
    """A loopback HTTP server that records what it was actually sent."""

    def __init__(self, responder: Any) -> None:
        self.received: list[dict[str, Any]] = []
        received = self.received

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
                length = int(self.headers.get("content-length", 0))
                body = self.rfile.read(length) if length else b""
                received.append(
                    {
                        "path": self.path,
                        "headers": {k.lower(): v for k, v in self.headers.items()},
                        "body": body,
                    }
                )
                responder(self)

            def log_message(self, *args: Any) -> None:
                return

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> _RecordingServer:
        self._thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    @property
    def origin(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    @property
    def authorization_headers(self) -> list[str]:
        return [r["headers"].get("authorization", "") for r in self.received]


def _ok(handler: BaseHTTPRequestHandler) -> None:
    body = json.dumps(
        {
            "model": "gpt-5.6-luna",
            "choices": [{"message": {"content": "OK"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 1},
        }
    ).encode("utf-8")
    handler.send_response(200)
    handler.send_header("content-type", "application/json")
    handler.send_header("x-request-id", "req-test-1")
    handler.send_header("content-length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _redirect_to(location: str, code: int = 302) -> Any:
    def responder(handler: BaseHTTPRequestHandler) -> None:
        handler.send_response(code)
        handler.send_header("location", location)
        handler.send_header("content-length", "0")
        handler.end_headers()

    return responder


SECRET = "sk-test-restricted-virtual-key-000"


# ---------------------------------------------------------------------------
# The credential must not reach a redirect target
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
def test_the_secret_never_reaches_a_redirect_target(code: int) -> None:
    """The assertion that matters: the target logged no request at all."""
    with _RecordingServer(_ok) as target:
        with _RecordingServer(
            _redirect_to(f"{target.origin}/v1/chat/completions", code)
        ) as gateway:
            with pytest.raises(smoke.RedirectRefused):
                smoke.post_json(f"{gateway.origin}/v1/chat/completions", {}, SECRET, timeout=10)

        assert target.received == [], (
            "the redirect target received a request; urllib would have carried "
            "the Authorization header there"
        )
        assert SECRET not in "".join(target.authorization_headers)
        # The first hop legitimately carries the credential.
        assert any(SECRET in header for header in gateway.authorization_headers)


def test_a_cross_origin_redirect_is_refused_and_named() -> None:
    with _RecordingServer(_ok) as target:
        with _RecordingServer(_redirect_to(f"{target.origin}/v1/chat/completions")) as gateway:
            with pytest.raises(smoke.RedirectRefused, match="cross-origin"):
                smoke.post_json(f"{gateway.origin}/v1/chat/completions", {}, SECRET, timeout=10)
        assert target.received == []


def test_a_same_origin_redirect_is_still_refused() -> None:
    """Same origin is not a safe exception: it is still a second, unrecorded request."""
    with _RecordingServer(_redirect_to("/v1/chat/completions/moved")) as gateway:
        with pytest.raises(smoke.RedirectRefused, match="redirects are not followed"):
            smoke.post_json(f"{gateway.origin}/v1/chat/completions", {}, SECRET, timeout=10)
    assert len(gateway.received) == 1, "a redirect was followed"


def test_an_https_to_http_downgrade_is_named_as_a_downgrade() -> None:
    assert "downgrade" in smoke.describe_redirect(
        "https://gateway.example/v1/chat/completions", "http://gateway.example/v1/chat/completions"
    )
    assert "cross-origin" in smoke.describe_redirect(
        "https://gateway.example/v1/chat/completions", "https://elsewhere.example/collect"
    )
    assert "redirects are not followed" in smoke.describe_redirect(
        "https://gateway.example/v1/chat/completions", "https://gateway.example/moved"
    )


def test_the_opener_has_no_redirect_following_handler() -> None:
    opener = smoke.build_opener()
    for handler in opener.handlers:
        assert type(handler) is not __import__("urllib.request", fromlist=["x"]).HTTPRedirectHandler
    assert any(isinstance(h, smoke._RefuseRedirects) for h in opener.handlers)


def test_the_opener_installs_no_retry_handler() -> None:
    """Guards the other half of the contract while we are here."""
    names = [type(h).__name__ for h in smoke.build_opener().handlers]
    assert not [n for n in names if "Retry" in n]


# ---------------------------------------------------------------------------
# A normal direct request must still work
# ---------------------------------------------------------------------------


def test_a_direct_request_still_succeeds() -> None:
    with _RecordingServer(_ok) as gateway:
        status, raw, headers, elapsed = smoke.post_json(
            f"{gateway.origin}/v1/chat/completions",
            {"model": "gpt-5.6-luna", "messages": []},
            SECRET,
            timeout=10,
        )
    assert status == 200
    assert json.loads(raw)["choices"][0]["message"]["content"] == "OK"
    assert headers["x-request-id"] == "req-test-1"
    assert elapsed >= 0
    assert len(gateway.received) == 1, "exactly one request, no retry"


def test_only_allowlisted_response_headers_are_recorded() -> None:
    def responder(handler: BaseHTTPRequestHandler) -> None:
        handler.send_response(200)
        handler.send_header("set-cookie", "session=leak")
        handler.send_header("x-request-id", "req-test-2")
        handler.send_header("content-length", "2")
        handler.end_headers()
        handler.wfile.write(b"{}")

    with _RecordingServer(responder) as gateway:
        _, _, headers, _ = smoke.post_json(
            f"{gateway.origin}/v1/chat/completions", {}, SECRET, timeout=10
        )
    assert set(headers) == {"x-request-id"}


# ---------------------------------------------------------------------------
# Base-URL policy and error redaction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad", ["http://gateway.example", "gateway.example", "https://gateway.example/v1"]
)
def test_base_url_policy_rejects_unusable_values(bad: str) -> None:
    with pytest.raises(RuntimeError):
        smoke.validate_base_url(bad)


def test_base_url_policy_accepts_the_evaluation_endpoint() -> None:
    url = "https://litellm-eval-production.up.railway.app"
    assert smoke.validate_base_url(f"{url}/") == url


def test_an_upstream_error_body_cannot_echo_a_key() -> None:
    """Auth failures are the likeliest first result and the likeliest to echo a key."""

    def responder(handler: BaseHTTPRequestHandler) -> None:
        body = json.dumps({"error": f"Invalid key: Received API Key={SECRET}"}).encode("utf-8")
        handler.send_response(401)
        handler.send_header("content-length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    with _RecordingServer(responder) as gateway:
        with pytest.raises(RuntimeError) as excinfo:
            smoke.post_json(f"{gateway.origin}/v1/chat/completions", {}, SECRET, timeout=10)
    message = str(excinfo.value)
    assert SECRET not in message
    assert "sk-REDACTED" in message
