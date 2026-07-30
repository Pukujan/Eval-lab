"""Print the Phoenix URL and the trace identifiers for recent runs (`make traces`)."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import load_settings  # noqa: E402


def main() -> int:
    settings = load_settings()
    phoenix = settings.phoenix_endpoint or "http://localhost:6006"

    print(f"Phoenix UI        : {phoenix}")
    print(f"Phoenix project   : {settings.phoenix_project_name}")
    print("Temporal Web UI   : http://localhost:8233")
    print(f"Audit store       : {settings.audit_database}")
    print()

    if not settings.audit_database.exists():
        print("No runs recorded yet. Run `make demo` first.")
        return 0

    connection = sqlite3.connect(str(settings.audit_database))
    try:
        rows = connection.execute(
            "SELECT run_id, payload FROM runs ORDER BY rowid DESC LIMIT 10"
        ).fetchall()
    finally:
        connection.close()

    if not rows:
        print("No runs recorded yet. Run `make demo` first.")
        return 0

    print(f"{'run id':<26} {'mode':<10} {'trace id':<34} workflow id")
    print("-" * 100)
    for run_id, payload in rows:
        record = json.loads(payload)
        trace_id = record.get("trace_id") or "(no trace recorded)"
        workflow_id = record.get("workflow_id") or "(local execution)"
        print(f"{run_id:<26} {record.get('execution_mode', '?'):<10} {trace_id:<34} {workflow_id}")

    print()
    print(f"Open a trace: {phoenix}/projects  (filter by the trace id above)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
