from pathlib import Path

from scripts.check_repo_contract import ROOT, main


def test_contract_validator_passes() -> None:
    assert main() == 0


def test_project_contract_points_to_current_checkpoint() -> None:
    project = (ROOT / "PROJECT.md").read_text(encoding="utf-8")
    checkpoint = ROOT / "checkpoints" / "CURRENT.md"
    assert "Git is project memory" in project
    assert checkpoint.is_file()


def test_active_bootstrap_task_has_required_sections() -> None:
    task = (ROOT / "tasks" / "TASK-0001-bootstrap-lab.md").read_text(encoding="utf-8")
    for heading in ("## Goal", "## Acceptance criteria", "## Checkpoint log", "## Handoff"):
        assert heading in task
