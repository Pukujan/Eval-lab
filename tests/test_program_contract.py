from scripts.check_repo_contract import ROOT

TASK_FILES = {
    "TASK-0002": "TASK-0002-canonical-schema-fixtures.md",
    "TASK-0003": "TASK-0003-jev-objective-baseline.md",
    "TASK-0004": "TASK-0004-metrics-calibration.md",
    "TASK-0005": "TASK-0005-public-benchmark.md",
    "TASK-0006": "TASK-0006-lightweight-local-baseline.md",
    "TASK-0007": "TASK-0007-external-judge-teacher-bakeoff.md",
    "TASK-0008": "TASK-0008-teacher-hard-negatives.md",
    "TASK-0009": "TASK-0009-small-judge-training.md",
    "TASK-0010": "TASK-0010-selective-escalation.md",
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
    for task_id in TASK_FILES:
        assert task_id in program

    access = read("docs/ACCESS_MODEL_MATRIX.md")
    assert "jev-1.13-free" in access
    assert "https://yolo-auto.com/v1" in access
    assert "qwen3.8-flash" in access
    assert "SuperGrok" in access
    assert "Luna" in access
    assert "Sol" in access


def test_current_checkpoint_points_to_task_0002() -> None:
    current = read("checkpoints/CURRENT.md")
    assert "TASK-0001" in current
    assert "complete" in current.lower()
    assert "TASK-0010" in current
    assert "Next atomic action" in current


def test_task_dependencies_are_declared() -> None:
    expected = {
        "TASK-0002": "TASK-0001",
        "TASK-0003": "TASK-0002",
        "TASK-0004": "TASK-0002",
        "TASK-0005": "TASK-0002",
        "TASK-0006": "TASK-0005",
        "TASK-0007": "TASK-0006",
        "TASK-0008": "TASK-0007",
        "TASK-0009": "TASK-0008",
        "TASK-0010": "TASK-0009",
    }
    for task_id, dependency in expected.items():
        text = (ROOT / "tasks" / TASK_FILES[task_id]).read_text(encoding="utf-8")
        assert dependency in text


def test_luna_handoff_covers_full_program() -> None:
    handoff = read("docs/LUNA_PROGRAM_HANDOFF.md")
    assert "TASK-0002" in handoff
    assert "TASK-0009" in handoff
    assert "TASK-0010" in handoff
    assert "qwen3.8-flash" in handoff


def test_jev_task_hard_pins_free_model() -> None:
    task = read("tasks/TASK-0003-jev-objective-baseline.md")
    assert "jev-1.13-free" in task
    assert "Never automatically fall back" in task


def test_yolo_auto_task_uses_exact_provider_contract() -> None:
    task = read("tasks/TASK-0007-external-judge-teacher-bakeoff.md")
    assert "https://yolo-auto.com/v1" in task
    assert "qwen3.8-flash" in task
    assert "YOLO_AUTO_API_KEY" in task


def test_task_0010_research_release_contract() -> None:
    task = read("tasks/TASK-0010-selective-escalation.md")
    standard = read("docs/RESEARCH_ARTIFACT_STANDARD.md")
    differential = read("docs/TASK-0010-METAMORPHIC-DIFFERENTIAL.md")
    assert "typesafe/jev-1.13" in task
    assert "EvalLab-Select v0.1.0" in task
    for term in ("RO-Crate 1.3", "PROV-O", "SHACL", "CFF 1.2.0"):
        assert term in standard
    assert "M-01" in differential
    assert "D-01" in differential
