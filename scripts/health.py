"""Verify every local service (`make health`).

Reports one line per service. Exit code is non-zero if any *required* service is
unreachable. Services are checked through the endpoint the Compose healthcheck
uses, so `make health` and Docker agree rather than testing two different things.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from app.config import load_settings  # noqa: E402

TIMEOUT = 4.0


@dataclass(frozen=True)
class Check:
    name: str
    url: str
    detail: str


def _http_ok(url: str) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:  # noqa: S310
            return response.status == 200, f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return False, f"unreachable ({exc.__class__.__name__})"


def _temporal_ok(address: str) -> tuple[bool, str]:
    import asyncio

    async def probe() -> tuple[bool, str]:
        try:
            from temporalio.client import Client

            await asyncio.wait_for(Client.connect(address), timeout=TIMEOUT)
        except Exception as exc:  # noqa: BLE001
            return False, f"unreachable ({exc.__class__.__name__})"
        return True, "frontend responded"

    return asyncio.run(probe())


def main() -> int:
    settings = load_settings()
    results: list[tuple[str, bool, str]] = []

    ok, detail = _temporal_ok(settings.temporal_address)
    results.append((f"temporal      {settings.temporal_address}", ok, detail))

    ok, detail = _http_ok("http://localhost:8233/")
    results.append(("temporal-ui   http://localhost:8233", ok, detail))

    phoenix = settings.phoenix_endpoint or "http://localhost:6006"
    ok, detail = _http_ok(f"{phoenix.rstrip('/')}/healthz")
    results.append((f"phoenix       {phoenix}", ok, detail))

    ok, detail = _http_ok(f"{settings.litellm_base_url.rstrip('/')}/health/readiness")
    results.append((f"litellm       {settings.litellm_base_url}", ok, detail))

    width = max(len(name) for name, _, _ in results)
    healthy = 0
    for name, ok, detail in results:
        mark = "OK  " if ok else "DOWN"
        healthy += int(ok)
        print(f"[{mark}] {name.ljust(width)}  {detail}")

    print(f"\n{healthy}/{len(results)} services healthy")

    if healthy != len(results):
        print(
            "\nServices are down. The mock-provider path still works without them: "
            "the gateway falls back to in-process LiteLLM dispatch and the runner "
            "to the degraded local executor (ADR-0006, ADR-0011). Runs made that "
            "way are marked NON_DURABLE_EXECUTION and prove nothing about "
            "durability."
        )
        return 1
    return 0


if __name__ == "__main__":
    if "--json" in sys.argv:
        settings = load_settings()
        print(json.dumps({"temporal": settings.temporal_address}, indent=2))
    raise SystemExit(main())
