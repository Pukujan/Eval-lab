"""Repository inspection, restricted to what a solver may see.

Every read goes through :func:`app.domain.fixtures.solver_visible_paths`, which is
an allowlist. Nothing here can reach ``reference/`` or ``tests_hidden/`` even by
accident, because those paths are never in the returned set (threat model T-1).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from app.config import FIXTURE_ROOT
from app.domain.fixtures import (
    SOLVER_FORBIDDEN_DIRECTORIES,
    solver_visible_paths,
)


@dataclass(frozen=True)
class RepositoryInspection:
    """What the investigation learned by looking at the repository."""

    root: str
    visible_files: tuple[str, ...]
    declared_invariants: tuple[str, ...]
    delivery_model: str
    content_digest: str
    #: Directories that exist but were deliberately not read.
    withheld_directories: tuple[str, ...]


def _read_declared_invariants(root: Path) -> tuple[tuple[str, ...], str]:
    """Pull invariant statements and the delivery model out of INVARIANTS.md."""
    invariants_file = root / "INVARIANTS.md"
    if not invariants_file.is_file():
        return (), "undeclared"

    text = invariants_file.read_text(encoding="utf-8")
    statements = tuple(
        line.lstrip("> ").strip()
        for line in text.splitlines()
        if line.startswith("> ") and line.strip() != ">"
    )

    delivery_model = "undeclared"
    lowered = text.lower()
    if "at-least-once" in lowered:
        delivery_model = "at-least-once"
    elif "exactly-once" in lowered:
        delivery_model = "exactly-once"

    return statements, delivery_model


def inspect_repository(root: str | Path | None = None) -> RepositoryInspection:
    """Read the solver-visible surface of the fixture repository."""
    base = Path(root or FIXTURE_ROOT).resolve()
    visible = solver_visible_paths(base)

    digest = hashlib.sha256()
    relative: list[str] = []
    for path in visible:
        relative.append(str(path.relative_to(base)).replace("\\", "/"))
        digest.update(path.read_bytes())

    statements, delivery_model = _read_declared_invariants(base)

    withheld = tuple(
        directory for directory in SOLVER_FORBIDDEN_DIRECTORIES if (base / directory).is_dir()
    )

    return RepositoryInspection(
        root=str(base),
        visible_files=tuple(relative),
        declared_invariants=statements,
        delivery_model=delivery_model,
        content_digest=digest.hexdigest(),
        withheld_directories=withheld,
    )
