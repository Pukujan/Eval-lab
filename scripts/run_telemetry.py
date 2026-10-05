"""Build, verify, and report the run telemetry ledger (TASK-0062).

Offline only: reads committed ``experiments/`` artifacts, makes no model or
provider calls, and hand-types no numbers.  Outputs (both committed):

* ``telemetry/runs.v1.jsonl``: one record per run unit, deterministic.
* ``telemetry/FINDINGS.md``: repository-wide findings computed from the ledger.

The record shape is pinned by ``schemas/run-telemetry.v1.schema.json`` and the
derivation lives in ``src/eval_lab/telemetry.py``.

Usage:
    uv run --locked python scripts/run_telemetry.py rebuild    # write both files
    uv run --locked python scripts/run_telemetry.py findings   # write FINDINGS only
    uv run --locked python scripts/run_telemetry.py verify     # schema + invariants
    uv run --locked python scripts/run_telemetry.py --check    # fail if stale
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from eval_lab.telemetry import build_records, dumps_jsonl, render_findings
except ImportError:  # executed as a file from the repository root
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from eval_lab.telemetry import build_records, dumps_jsonl, render_findings

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = Path("telemetry/runs.v1.jsonl")
FINDINGS_PATH = Path("telemetry/FINDINGS.md")
SCHEMA_PATH = Path("schemas/run-telemetry.v1.schema.json")


def _expected() -> tuple[str, str]:
    records = build_records(ROOT)
    return dumps_jsonl(records), render_findings(records)


def _load_ledger() -> list[dict[str, Any]]:
    text = (ROOT / LEDGER_PATH).read_text(encoding="utf-8")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        raw: object = json.loads(line)
        if not isinstance(raw, dict):
            raise TypeError(f"{LEDGER_PATH}:{line_number}: record is not a JSON object")
        records.append({str(key): value for key, value in raw.items()})
    return records


def _schema_errors(records: list[dict[str, Any]]) -> list[str]:
    import jsonschema

    schema = json.loads((ROOT / SCHEMA_PATH).read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors: list[str] = []
    for index, record in enumerate(records):
        for error in sorted(validator.iter_errors(record), key=lambda item: list(item.path)):
            location = "/".join(str(part) for part in error.path) or "<root>"
            errors.append(f"record {index} ({record.get('run_path')}) {location}: {error.message}")
    return errors


def verify() -> int:
    failures: list[str] = []
    records = _load_ledger()
    failures.extend(_schema_errors(records))

    keys = [str(record.get("run_path")) for record in records]
    if len(set(keys)) != len(keys):
        failures.append("ledger has duplicate run_path values (the key must be unique)")
    if keys != sorted(keys):
        failures.append("ledger is not sorted by run_path")

    if failures:
        print("Run telemetry ledger FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"Run telemetry ledger OK: {len(records)} records, schema valid, keys unique")
    return 0


def _write(path: Path, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {path}")


def _read_normalized(path: Path) -> str | None:
    if not path.is_file():
        return None
    # Git may check text files out with platform line endings; compare on LF.
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def check() -> int:
    ledger_text, findings_text = _expected()
    stale: list[str] = []
    for path, expected in ((LEDGER_PATH, ledger_text), (FINDINGS_PATH, findings_text)):
        if _read_normalized(ROOT / path) != expected:
            stale.append(str(path))
    if stale:
        print("Run telemetry is stale: " + ", ".join(stale))
        print("Run: uv run --locked python scripts/run_telemetry.py rebuild")
        return 1
    print("Run telemetry is current.")
    return verify()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        choices=("rebuild", "findings", "verify"),
        help="rebuild writes both outputs; findings writes FINDINGS only; verify checks the ledger",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the committed ledger or findings are stale (used in CI)",
    )
    args = parser.parse_args()

    if args.check:
        if args.command is not None:
            parser.error("--check does not combine with a command")
        return check()
    if args.command == "rebuild":
        ledger_text, findings_text = _expected()
        _write(LEDGER_PATH, ledger_text)
        _write(FINDINGS_PATH, findings_text)
        return verify()
    if args.command == "findings":
        _, findings_text = _expected()
        _write(FINDINGS_PATH, findings_text)
        return 0
    if args.command == "verify":
        return verify()
    parser.error("choose a command (rebuild, findings, verify) or --check")
    return 2


if __name__ == "__main__":
    sys.exit(main())
