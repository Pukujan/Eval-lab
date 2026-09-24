from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    from .check_workspace_policy import workspace_violations
except ImportError:  # Running this file directly from the scripts directory.
    from check_workspace_policy import workspace_violations

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "PROJECT.md",
    "AGENTS.md",
    "docs/PDD.md",
    "docs/SDD.md",
    "docs/TDD.md",
    "docs/HANDOFF_PROTOCOL.md",
    "docs/EXPERIMENT_PROTOCOL.md",
    "docs/CI_CD.md",
    "docs/PROGRAM_PLAN.md",
    "docs/VALIDATION_MATRIX.md",
    "docs/LUNA_PROGRAM_HANDOFF.md",
    "docs/ACCESS_MODEL_MATRIX.md",
    "docs/WORKSPACE_POLICY.md",
    "checkpoints/CURRENT.md",
    "uv.lock",
    "tasks/README.md",
    "tasks/TASK-0001-bootstrap-lab.md",
    "tasks/TASK-0002-canonical-schema-fixtures.md",
    "tasks/TASK-0003-jev-objective-baseline.md",
    "tasks/TASK-0004-metrics-calibration.md",
    "tasks/TASK-0005-public-benchmark.md",
    "tasks/TASK-0006-lightweight-local-baseline.md",
    "tasks/TASK-0007-external-judge-teacher-bakeoff.md",
    "tasks/TASK-0008-teacher-hard-negatives.md",
    "tasks/TASK-0009-small-judge-training.md",
    "tasks/TASK-0010-selective-escalation.md",
    "docs/TASK-0010-METAMORPHIC-DIFFERENTIAL.md",
    "docs/TASK-0010-OPENROUTER-JEV.md",
    "docs/RESEARCH_ARTIFACT_STANDARD.md",
    "benchmark/README.md",
    "paper/README.md",
    "benchmark/eval-lab-select-v0.1.0/benchmark.yaml",
    "benchmark/eval-lab-select-v0.1.0/README.md",
    "paper/references.bib",
    "paper/paper.md",
    "paper/archive/README.md",
    "paper/archive/selective-escalation/main.tex",
    "CITATION.cff",
    "experiments/README.md",
]

TASK_PATTERN = re.compile(r"^TASK-\d{4}-[a-z0-9-]+\.md$")
EXPERIMENT_PATTERN = re.compile(r"^EXP-\d{8}-\d{3}-[a-z0-9-]+$")

PROGRAM_TASKS = {
    "TASK-0002-canonical-schema-fixtures.md": "TASK-0001",
    "TASK-0003-jev-objective-baseline.md": "TASK-0002",
    "TASK-0004-metrics-calibration.md": "TASK-0002",
    "TASK-0005-public-benchmark.md": "TASK-0002",
    "TASK-0006-lightweight-local-baseline.md": "TASK-0005",
    "TASK-0007-external-judge-teacher-bakeoff.md": "TASK-0006",
    "TASK-0008-teacher-hard-negatives.md": "TASK-0007",
    "TASK-0009-small-judge-training.md": "TASK-0008",
    "TASK-0010-selective-escalation.md": "TASK-0009",
}

PROGRAM_HEADINGS = (
    "## Goal",
    "## Inputs",
    "## Outputs",
    "## Acceptance criteria",
    "## Validation",
    "## Stop conditions",
    "## Checkpoint log",
    "## Handoff",
)


def error(message: str, failures: list[str]) -> None:
    failures.append(message)


def check_required_files(failures: list[str]) -> None:
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).is_file():
            error(f"missing required file: {rel}", failures)


def check_tasks(failures: list[str]) -> None:
    tasks_dir = ROOT / "tasks"
    if not tasks_dir.is_dir():
        error("missing tasks directory", failures)
        return

    for path in tasks_dir.glob("TASK-*.md"):
        if not TASK_PATTERN.match(path.name):
            error(f"invalid task filename: {path.name}", failures)
            continue
        text = path.read_text(encoding="utf-8")
        for heading in ("## Goal", "## Acceptance criteria", "## Checkpoint log", "## Handoff"):
            if heading not in text:
                error(f"{path}: missing heading {heading}", failures)

    for filename, dependency in PROGRAM_TASKS.items():
        path = tasks_dir / filename
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for heading in PROGRAM_HEADINGS:
            if heading not in text:
                error(f"{path}: missing program heading {heading}", failures)
        if dependency not in text:
            error(f"{path}: expected dependency marker {dependency}", failures)


def check_program_checkpoint(failures: list[str]) -> None:
    current = ROOT / "checkpoints" / "CURRENT.md"
    if not current.is_file():
        return
    text = current.read_text(encoding="utf-8")
    if "TASK-0010" not in text:
        error(
            "CURRENT checkpoint must identify TASK-0010 as the active/next research gate", failures
        )

    program = ROOT / "docs" / "PROGRAM_PLAN.md"
    if program.is_file():
        program_text = program.read_text(encoding="utf-8")
        for task_id in (
            "TASK-0002",
            "TASK-0003",
            "TASK-0004",
            "TASK-0005",
            "TASK-0006",
            "TASK-0007",
            "TASK-0008",
            "TASK-0009",
            "TASK-0010",
        ):
            if task_id not in program_text:
                error(f"PROGRAM_PLAN missing {task_id}", failures)


def check_workspace(failures: list[str]) -> None:
    for violation in workspace_violations(ROOT, canonical_root=ROOT):
        error(violation, failures)


def check_experiments(failures: list[str]) -> None:
    root = ROOT / "experiments"
    if not root.is_dir():
        error("missing experiments directory", failures)
        return

    for path in root.iterdir():
        if not path.is_dir():
            continue
        if not EXPERIMENT_PATTERN.match(path.name):
            error(f"invalid experiment directory: {path.name}", failures)
            continue

        readme = path / "README.md"
        manifest = path / "experiment.yaml"
        if not readme.is_file():
            error(f"{path.name}: missing README.md", failures)
        if not manifest.is_file():
            error(f"{path.name}: missing experiment.yaml", failures)
            continue

        manifest_text = manifest.read_text(encoding="utf-8")
        if "status: completed" in manifest_text:
            for required in ("results.json", "report.md"):
                if not (path / required).is_file():
                    error(f"{path.name}: completed experiment missing {required}", failures)


def main() -> int:
    failures: list[str] = []
    check_required_files(failures)
    check_tasks(failures)
    check_program_checkpoint(failures)
    check_experiments(failures)
    check_workspace(failures)

    if failures:
        print("Repository contract FAILED:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("Repository contract OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
