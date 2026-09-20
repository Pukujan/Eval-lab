from scripts.check_repo_contract import ROOT

TASK_FILES = {
    "TASK-0002": "TASK-0002-canonical-schema-fixtures.md",
    "TASK-0003": "TASK-0003-jev-objective-baseline.md",
    "TASK-0004": "TASK-0004-metrics-calibration.md",
    "TASK-0005": "TASK-0005-public-benchmark.md",
    "TASK-0006": "TASK-0006-lightweight-local-baseline.md",
}

REQUIRED_PROGRAM_HEADINGS = (
    "## Goal",
    "## Inputs",
    "## Outputs",
    "## Acceptance criteria",
    "## Validation",
    "## Stop conditions",
    "## Checkpoint log",
    "## Handoff",
)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_all_program_tasks_exist_with_execution_contracts() -> None:
    for task_id, filename in TASK_FILES.items():
        path = ROOT / "tasks" / filename
        assert path.is_file(), task_id
        text = path.read_text(encoding="utf-8")
        for heading in REQUIRED_PROGRAM_HEADINGS:
            assert heading in text, f"{task_id} missing {heading}"


def test_program_docs_cover_entire_sequence() -> None:
    program = read("docs/PROGRAM_PLAN.md")
    pdd = read("docs/PDD.md")
    for task_id in TASK_FILES:
        assert task_id in program
    for deliverable in ("canonical", "Jev", "calibration", "ARC-Challenge", "Qwen"):
        assert deliverable in pdd


def test_current_checkpoint_points_to_task_0002() -> None:
    current = read("checkpoints/CURRENT.md")
    assert "TASK-0001" in current
    assert "complete" in current.lower()
    assert "TASK-0002" in current
    assert "Next atomic action" in current


def test_task_dependencies_are_declared() -> None:
    expected = {
        "TASK-0002": "TASK-0001",
        "TASK-0003": "TASK-0002",
        "TASK-0004": "TASK-0002",
        "TASK-0005": "TASK-0002",
        "TASK-0006": "TASK-0005",
    }
    for task_id, dependency in expected.items():
        text = (ROOT / "tasks" / TASK_FILES[task_id]).read_text(encoding="utf-8")
        assert dependency in text


def test_validation_matrix_covers_all_tasks() -> None:
    matrix = read("docs/VALIDATION_MATRIX.md")
    for task_id in TASK_FILES:
        assert task_id in matrix


def test_luna_handoff_exists_and_is_bounded() -> None:
    handoff = read("docs/LUNA_PROGRAM_HANDOFF.md")
    assert "TASK-0002" in handoff
    assert "TASK-0006" in handoff
    assert "fine-tuning" in handoff
