"""Live Eval Lab backend (TASK-0060 phase 2).

A read-only public API over a Postgres database that holds every committed Eval
Lab run, serving the same ``research-chart-data`` v1 documents the papers embed.
See ``live/README.md``.

Importing this package does not require the ``live`` dependency group; only the
modules that touch FastAPI/SQLAlchemy do, and they are imported on demand.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
