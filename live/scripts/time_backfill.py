"""Print where the backfill spends its time.

The loader recomputes the paper's dataset through ``scripts/export_chart_data.py``,
which shells out to ``git``.  On a checkout where ``git status`` is slow (large
untracked trees, an antivirus scanner, a network drive) that dominates, and the
test suite looks hung when it is merely waiting.  Run this to see:

    uv run --locked --extra live python live/scripts/time_backfill.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _stamp(label: str, start: float) -> float:
    elapsed = time.perf_counter() - start
    print(f"{label}: {elapsed:.1f}s", flush=True)
    return time.perf_counter()


def main() -> int:
    for entry in (str(REPO_ROOT), str(REPO_ROOT / "scripts")):
        if entry not in sys.path:
            sys.path.insert(0, entry)

    start = time.perf_counter()
    import scripts.export_chart_data as exporter

    start = _stamp("import exporter", start)

    info = exporter.git_info()
    start = _stamp(f"git_info (HEAD {info['commit'][:8]}, dirty={info['dirty']})", start)

    document = exporter.build_dataset(info)
    start = _stamp(
        f"build_dataset ({len(document['entities'])} entities, "
        f"{len(document['observations'])} observations)",
        start,
    )

    from eval_lab_live import loader

    loader.build_dataset_document(REPO_ROOT)
    _stamp("loader.build_dataset_document (recomputes + compares)", start)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
