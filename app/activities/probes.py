"""Deterministic probe execution.

A probe is code, not prose, and it must give the same answer every time. Each one
runs in a subprocess with an explicit ``cwd``, a hard timeout, and a **scrubbed
environment** — an allowlist rather than the inherited parent env, so provider
credentials are structurally absent from anything the fixture can read
(threat model T-4, T-5).
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROBE_TIMEOUT_SECONDS = 120

#: The only environment variables a probe or test subprocess inherits.
_ENV_ALLOWLIST = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT")


def scrubbed_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    """A minimal environment for child processes.

    Built by allowlist. A denylist would leak every variable nobody thought to
    name, which over time is all of them.
    """
    import os

    env = {key: os.environ[key] for key in _ENV_ALLOWLIST if key in os.environ}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONHASHSEED"] = "0"
    if extra:
        env.update(extra)
    return env


@dataclass(frozen=True)
class ProbeExecution:
    """Raw result of running a probe."""

    probe_id: str
    exit_code: int
    stdout: str
    stderr: str
    observations: dict[str, object]
    timed_out: bool = False


def _run(
    command: list[str], cwd: Path, timeout: int = PROBE_TIMEOUT_SECONDS
) -> tuple[int, str, str, bool]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            env=scrubbed_environment(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 124, "", f"probe timed out after {timeout}s", True
    return completed.returncode, completed.stdout, completed.stderr, False


def concurrent_delivery_probe(working_copy: Path, workers: int = 2) -> ProbeExecution:
    """Force the check-then-write window open and report what happened.

    Discriminates the race hypothesis from "there is no duplicate check at all":
    both predict duplication here, but only one of them also predicts duplication
    under sequential redelivery.
    """
    database = working_copy / "probe-concurrent.db"
    database.unlink(missing_ok=True)

    exit_code, stdout, stderr, timed_out = _run(
        [sys.executable, "probe.py", str(database), str(workers)], working_copy
    )

    observations: dict[str, object] = {}
    if stdout.strip():
        try:
            observations = json.loads(stdout)
        except ValueError:
            observations = {"unparsed_stdout": stdout[:500]}

    return ProbeExecution(
        probe_id="P-concurrent-delivery",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        observations=observations,
        timed_out=timed_out,
    )


_SEQUENTIAL_SCRIPT = """
import json, sys
sys.path.insert(0, ".")
from src.effects import effect_count
from src.processor import Job
from src.store import ResultStore
from src.worker import deliver_sequentially

database = sys.argv[1]
ResultStore.initialise(database)
report = deliver_sequentially(database, Job("job-sequential", "payload"), times=3)
store = ResultStore(database)
try:
    rows = [r for r in store.raw_result_rows() if r[0] == "job-sequential"]
finally:
    store.close()
print(json.dumps({
    "raw_result_rows": len(rows),
    "effect_count": effect_count(database, "job-sequential"),
    "reported_commits": report.commit_count,
    "duplicate_processing": effect_count(database, "job-sequential") > 1,
}, sort_keys=True))
"""


def sequential_redelivery_probe(working_copy: Path) -> ProbeExecution:
    """Redeliver a job three times in sequence.

    This is the probe that **falsifies** the tempting "there is no duplicate
    check" hypothesis: the check exists and works when deliveries do not overlap.
    A run where this probe shows duplication would mean a different defect.
    """
    database = working_copy / "probe-sequential.db"
    database.unlink(missing_ok=True)

    exit_code, stdout, stderr, timed_out = _run(
        [sys.executable, "-c", _SEQUENTIAL_SCRIPT, str(database)], working_copy
    )

    observations: dict[str, object] = {}
    if stdout.strip():
        try:
            observations = json.loads(stdout)
        except ValueError:
            observations = {"unparsed_stdout": stdout[:500]}

    return ProbeExecution(
        probe_id="P-sequential-redelivery",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        observations=observations,
        timed_out=timed_out,
    )


def delivery_contract_probe(working_copy: Path) -> ProbeExecution:
    """Read the declared delivery model from the specification.

    Falsifies "the queue is broken": if delivery is declared at-least-once, then
    redelivery is the queue keeping its contract and the consumer is at fault.
    """
    invariants = working_copy / "INVARIANTS.md"
    text = invariants.read_text(encoding="utf-8") if invariants.is_file() else ""
    lowered = text.lower()

    if "at-least-once" in lowered:
        declared = "at-least-once"
    elif "exactly-once" in lowered:
        declared = "exactly-once"
    else:
        declared = "undeclared"

    return ProbeExecution(
        probe_id="P-delivery-contract",
        exit_code=0 if declared != "undeclared" else 1,
        stdout=declared,
        stderr="",
        observations={
            "declared_delivery_model": declared,
            "redelivery_is_contractual": declared == "at-least-once",
        },
    )


#: Probe id -> callable. The graph selects probes by id; nothing dispatches on
#: free text.
PROBE_REGISTRY = {
    "P-concurrent-delivery": concurrent_delivery_probe,
    "P-sequential-redelivery": sequential_redelivery_probe,
    "P-delivery-contract": delivery_contract_probe,
}
