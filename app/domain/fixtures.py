"""The fixture manifest: what a solver may see, and what it may never touch.

The central decision here is that :func:`solver_visible_paths` is an **allowlist**.
A denylist fails open — add a new secret file and it leaks by default, silently,
and nothing tells you. An allowlist fails closed: a new file is invisible until
someone publishes it deliberately (threat model T-1).
"""

from __future__ import annotations

from pathlib import Path

from app.config import FIXTURE_ROOT
from app.domain.schemas import InvariantKind, ProblemSpecification, SystemInvariant

#: Directories a solver role is allowed to read. Everything else is invisible.
SOLVER_VISIBLE_DIRECTORIES: tuple[str, ...] = ("src",)

#: Individual files a solver role is allowed to read.
SOLVER_VISIBLE_FILES: tuple[str, ...] = ("INVARIANTS.md",)

#: Never readable by a solver: the answer key and the hidden acceptance tests.
SOLVER_FORBIDDEN_DIRECTORIES: tuple[str, ...] = ("reference", "tests_hidden", "patches")

#: A patch touching any of these is rejected outright, whatever the tests say.
PROHIBITED_PATHS: tuple[str, ...] = (
    "tests_visible",
    "tests_hidden",
    "reference",
    "patches",
    "probe.py",
    "INVARIANTS.md",
)

PRIMARY_INVARIANT_STATEMENT = (
    "One logical job identifier may produce at most one committed processing result."
)


def solver_visible_paths(root: Path | None = None) -> tuple[Path, ...]:
    """Every path a solver role may read, resolved under ``root``.

    Visible test files are included so a solver can see the failing test; hidden
    tests and the reference implementation are structurally excluded.
    """
    base = (root or FIXTURE_ROOT).resolve()
    visible: list[Path] = []

    for directory in (*SOLVER_VISIBLE_DIRECTORIES, "tests_visible"):
        target = base / directory
        if target.is_dir():
            visible.extend(sorted(p for p in target.rglob("*.py") if "__pycache__" not in p.parts))

    for filename in SOLVER_VISIBLE_FILES:
        candidate = base / filename
        if candidate.is_file():
            visible.append(candidate)

    return tuple(visible)


def is_prohibited(relative_path: str) -> bool:
    """Whether a patch may not modify ``relative_path``."""
    normalised = relative_path.replace("\\", "/").lstrip("./")
    return any(
        normalised == prohibited or normalised.startswith(f"{prohibited}/")
        for prohibited in PROHIBITED_PATHS
    )


def build_problem_specification(
    specification_id: str = "spec-duplicate-job-processing",
) -> ProblemSpecification:
    """The structured bug report the walking skeleton is driven by."""
    return ProblemSpecification(
        specification_id=specification_id,
        title="Duplicate processing of a redelivered job",
        reported_symptom=(
            "Under at-least-once delivery, a job occasionally appears twice in the "
            "committed results and downstream systems observe the effect twice."
        ),
        repository_path=str(FIXTURE_ROOT),
        expected_behaviour=(
            "Redelivery of a job identifier must not produce a second committed "
            "processing result or a second externally visible effect, including when "
            "two workers process the identifier concurrently."
        ),
        invariants=(
            SystemInvariant(
                invariant_id="INV-1",
                statement=PRIMARY_INVARIANT_STATEMENT,
                kind=InvariantKind.PRIMARY,
                check_reference="fixtures/duplicate-job-processing/probe.py::raw_result_rows",
            ),
            SystemInvariant(
                invariant_id="INV-2",
                statement=(
                    "The irreversible external effect executes at most once per "
                    "logical job identifier."
                ),
                check_reference="fixtures/duplicate-job-processing/src/effects.py::effect_count",
            ),
            SystemInvariant(
                invariant_id="INV-3",
                statement=(
                    "Redelivering a job after the previous delivery completed commits "
                    "no new result."
                ),
                check_reference=(
                    "fixtures/duplicate-job-processing/tests_visible/test_processing.py"
                    "::test_sequential_redelivery_is_idempotent"
                ),
            ),
        ),
        prohibited_paths=PROHIBITED_PATHS,
    )
