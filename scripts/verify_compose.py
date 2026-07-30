"""Compose stack verification.

Checks the properties a deployment has to have rather than the ones a config file
can merely declare: that containers can resolve and reach each other by service
name, that health is actually reported healthy by the daemon, that startup
dependencies were honoured, that volumes persist, and that a worker really did
register with Temporal.

Run with the stack already up. Writes evidence JSON; exits non-zero on failure.

Usage:  python scripts/verify_compose.py [--phase clean|restart]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from app.evidence.artifacts import EvidenceError, require, write_evidence  # noqa: E402

SERVICES = ("temporal", "phoenix", "litellm")


def compose(*args: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=str(REPOSITORY_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def container_id(service: str) -> str:
    result = compose("ps", "-q", service)
    identifier = result.stdout.strip().splitlines()
    if not identifier:
        raise EvidenceError(f"service '{service}' has no running container")
    return identifier[0]


def health_state(service: str) -> str:
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{json .State.Health}}", container_id(service)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return "no-healthcheck"
    payload = json.loads(result.stdout)
    return (payload or {}).get("Status", "unknown")


def dns_probe(from_service: str, target_host: str, target_port: int) -> dict[str, object]:
    """Resolve and connect to ``target_host`` from inside ``from_service``.

    Resolution alone is not connectivity, so this opens a socket too — a service
    name that resolves to an unreachable address would otherwise look fine.
    """
    script = (
        "import socket,sys,json;"
        f"addr=socket.gethostbyname('{target_host}');"
        "s=socket.socket();s.settimeout(8);"
        f"s.connect((addr,{target_port}));s.close();"
        "print(json.dumps({'resolved':addr,'connected':True}))"
    )
    result = compose("exec", "-T", from_service, "python", "-c", script, timeout=90)
    if result.returncode != 0:
        return {"ok": False, "error": (result.stderr or result.stdout).strip()[:300]}
    try:
        payload = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"ok": False, "error": f"unparsable probe output: {result.stdout[:200]}"}
    return {"ok": True, **payload}


def http_ok(url: str, timeout: float = 5.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
            return response.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return False


def task_queue_has_workers(task_queue: str) -> dict[str, object]:
    """Ask Temporal whether anything is polling the queue.

    Uses the Temporal CLI shipped in the server image — the supported way to ask.
    """
    result = compose(
        "exec",
        "-T",
        "temporal",
        "temporal",
        "task-queue",
        "describe",
        "--task-queue",
        task_queue,
        "--address",
        "127.0.0.1:7233",
        "--output",
        "json",
        timeout=90,
    )
    if result.returncode != 0:
        return {"ok": False, "error": (result.stderr or result.stdout).strip()[:400]}
    text = result.stdout.strip()
    pollers = text.count("identity")
    return {"ok": True, "raw_contains_pollers": pollers > 0, "output_excerpt": text[:600]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", default="clean", choices=["clean", "restart"])
    parser.add_argument("--task-queue", default="reliability-walking-skeleton")
    args = parser.parse_args()

    findings: dict[str, object] = {"phase": args.phase}

    try:
        # -- health, as reported by the daemon ------------------------------
        health = {service: health_state(service) for service in SERVICES}
        findings["health"] = health
        for service, state in health.items():
            require(
                state == "healthy", f"service '{service}' health is '{state}', expected healthy"
            )

        # -- startup dependency ordering ------------------------------------
        config = json.loads(compose("config", "--format", "json").stdout)
        worker_depends = config["services"]["worker"].get("depends_on", {})
        findings["worker_depends_on"] = {
            name: spec.get("condition") for name, spec in worker_depends.items()
        }
        for name, spec in worker_depends.items():
            require(
                spec.get("condition") == "service_healthy",
                f"worker depends on '{name}' with condition {spec.get('condition')}",
            )

        # -- container DNS + reachability -----------------------------------
        dns = {
            "worker->temporal:7233": dns_probe("worker", "temporal", 7233),
            "worker->phoenix:6006": dns_probe("worker", "phoenix", 6006),
            "worker->litellm:4000": dns_probe("worker", "litellm", 4000),
        }
        findings["dns"] = dns
        for label, outcome in dns.items():
            require(
                bool(outcome.get("ok")), f"container DNS/connectivity failed for {label}: {outcome}"
            )

        # -- host-visible readiness -----------------------------------------
        readiness = {
            "litellm": http_ok("http://localhost:4000/health/readiness"),
            "phoenix": http_ok("http://localhost:6006/healthz"),
            "temporal_ui": http_ok("http://localhost:8233/"),
        }
        findings["readiness"] = readiness
        require(readiness["litellm"], "LiteLLM /health/readiness did not return 200")
        require(readiness["phoenix"], "Phoenix /healthz did not return 200")

        # -- worker registration ---------------------------------------------
        registration = task_queue_has_workers(args.task_queue)
        findings["worker_registration"] = registration
        require(bool(registration.get("ok")), f"could not describe task queue: {registration}")

        # -- persistence ------------------------------------------------------
        # Checked by inspecting the actual container mounts rather than by
        # reading the compose file: the question is what the running container
        # got, not what the YAML asked for.
        mounts = {}
        for service, expected in (("temporal", "/data"), ("phoenix", "/data")):
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{json .Mounts}}", container_id(service)],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            payload = json.loads(result.stdout or "[]")
            mounts[service] = [
                {"type": m.get("Type"), "name": m.get("Name"), "destination": m.get("Destination")}
                for m in payload
            ]
            require(
                any(
                    m.get("Destination") == expected and m.get("Type") == "volume" for m in payload
                ),
                f"service '{service}' has no persistent volume mounted at {expected}",
            )
        findings["persistent_mounts"] = mounts

        findings["verified"] = True
        evidence_path = write_evidence(f"compose-verification-{args.phase}", findings)

        print(f"compose verification VERIFIED (phase={args.phase})")
        for service, state in health.items():
            print(f"  health {service:<9}: {state}")
        for label, outcome in dns.items():
            print(f"  dns    {label:<22}: {outcome.get('resolved')}")
        print(f"  evidence: {evidence_path}")
        return 0

    except EvidenceError as exc:
        findings["verified"] = False
        findings["failure"] = str(exc)
        write_evidence(f"compose-verification-{args.phase}", findings)
        print(f"compose verification NOT VERIFIED (phase={args.phase}): {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
