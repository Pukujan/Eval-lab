from __future__ import annotations

import re
import sys
from pathlib import Path

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
    "checkpoints/CURRENT.md",
    "tasks/README.md",
    "experiments/README.md",
]

TASK_PATTERN = re.compile(r"^TASK-\d{4}-[a-z0-9-]+\.md$")
EXPERIMENT_PATTERN = re.compile(r"^EXP-\d{8}-\d{3}-[a-z0-9-]+$")


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
    check_experiments(failures)

    if failures:
        print("Repository contract FAILED:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("Repository contract OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
