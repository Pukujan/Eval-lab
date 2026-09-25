"""Loader tests: the backfill is complete, idempotent and refuses to drift.

The loader is the only writer, so these are the tests that make "the database is
a rebuildable projection of git" checkable.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from eval_lab_live import loader
from eval_lab_live.db import create_db_engine, create_schema, make_session_factory, session_scope
from eval_lab_live.models import (
    Activity,
    Aggregate,
    Arm,
    Artifact,
    Comparison,
    Dataset,
    Dimension,
    Experiment,
    Judge,
    Level,
    Metric,
    Observation,
    Project,
    Run,
    RunEntity,
)
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_ID = "eval-lab/judges-blind-760"

COUNTED = (
    Project,
    Dataset,
    Experiment,
    Judge,
    Arm,
    Metric,
    Level,
    Dimension,
    Observation,
    Comparison,
    Aggregate,
    Run,
    RunEntity,
    Artifact,
    Activity,
)


@pytest.fixture(scope="module")
def counts(session: Session) -> dict[str, int]:
    return {
        model.__name__: session.scalar(select(func.count()).select_from(model)) for model in COUNTED
    }


def test_every_committed_experiment_is_imported(counts: dict[str, int], repo_root: Path) -> None:
    directories = [path for path in (repo_root / "experiments").glob("EXP-*") if path.is_dir()]
    assert directories
    assert counts["Experiment"] == len(directories)


def test_every_committed_run_is_imported(
    counts: dict[str, int], load_report: Any, repo_root: Path
) -> None:
    """No ``results.json`` is dropped, including the ones with no ``run_id``.

    Two pairs of committed runs share a ``run_id`` (``canary-cb_deepseek_v41_
    flash-20260922`` in EXP-023 and EXP-024, ``grok_46-typed_schema`` twice
    inside EXP-025), because a runner id is unique inside its experiment and not
    across the repository.  Those are re-keyed by their run directory, not
    dropped, and the runner's value survives in ``source_run_id``.
    """
    committed = list((repo_root / "experiments").glob("EXP-*/**/results.json"))
    assert len(committed) > 100
    assert load_report.runs == len(committed)
    assert counts["Run"] == len(committed)
    assert load_report.runs_without_id > 0, "older runners wrote no run_id; they must still load"
    assert load_report.duplicate_run_ids == 2
    assert not [item for item in load_report.skipped if "duplicate run_id" in item]


def test_a_duplicate_run_id_is_re_keyed_by_its_directory(session: Session, repo_root: Path) -> None:
    """The re-keyed row keeps the value the runner wrote, and is reachable."""
    rekeyed = session.scalars(
        select(Run).where(Run.source_run_id.is_not(None)).order_by(Run.run_id)
    ).all()
    assert len(rekeyed) == 2
    for run in rekeyed:
        assert run.run_id.endswith(run.source_run_id or "")
        assert run.run_id.startswith("experiments/EXP-")
        assert (repo_root / run.run_id).is_dir()


def test_every_chart_run_path_traces_to_an_imported_run(load_report: Any) -> None:
    """Each ``runs[]`` entry of the paper's document resolves to a real run row."""
    unresolved = [item for item in load_report.skipped if "no imported run covers it" in item]
    assert unresolved == []
    assert load_report.run_entities == 27


def test_the_dataset_is_decomposed_into_tidy_tables(
    counts: dict[str, int], committed: dict[str, Any]
) -> None:
    assert counts["Arm"] == len(committed["entities"])
    assert counts["Observation"] == len(committed["observations"])
    assert counts["Comparison"] == len(committed["comparisons"])
    assert counts["Metric"] == len(committed["measures"])
    assert counts["Level"] == len(committed["levels"])
    assert counts["Dimension"] == len(committed["dimensions"])
    assert counts["Dataset"] == 1


def test_observations_carry_the_slice_population(session: Session) -> None:
    """``slice_records`` is populated from the all-record-accuracy denominator."""
    rows = session.execute(
        select(Observation.slice_dim, Observation.slice_records).where(
            Observation.dataset_id == DATASET_ID
        )
    ).all()
    assert rows
    assert all(records >= 0 for _, records in rows)
    overall = {records for dim, records in rows if dim == "overall"}
    assert overall == {760}


def test_the_frozen_provenance_is_stored_verbatim(
    session: Session, committed: dict[str, Any]
) -> None:
    dataset = session.get(Dataset, DATASET_ID)
    assert dataset is not None
    assert dataset.provenance == committed["provenance"]
    assert dataset.canonical_id == committed["id"]
    assert dataset.record_count == committed["recordCount"]


def test_the_loader_refuses_to_publish_numbers_that_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tampered dataset file must abort the load, not publish quietly."""
    committed = json.loads((REPO_ROOT / loader.DATASET_FILE).read_text(encoding="utf-8"))
    committed["recordCount"] = 761
    tampered = tmp_path / "judges-blind-760.json"
    tampered.write_text(json.dumps(committed), encoding="utf-8")
    monkeypatch.setattr(loader, "DATASET_FILE", str(tampered))

    with pytest.raises(loader.LoadError, match="recordCount"):
        loader.build_dataset_document(REPO_ROOT)


def test_provenance_is_the_only_excluded_key() -> None:
    """The comparison is strict: one changed number is a mismatch."""
    assert (
        loader.compare_documents({"a": 1, "provenance": {"x": 1}}, {"a": 1, "provenance": {"y": 2}})
        is None
    )
    assert loader.compare_documents({"a": 1}, {"a": 2}) == "key 'a' differs"
    assert loader.compare_documents({"a": 1}, {}) == "key 'a' differs"


@pytest.fixture(scope="module")
def reloaded(settings: Any) -> Iterator[tuple[sessionmaker[Session], dict[str, int]]]:
    """Load twice into a fresh database and count the rows each time."""
    engine: Engine = create_db_engine(settings.database_url)
    create_schema(engine)
    factory = make_session_factory(engine)
    first: dict[str, int] = {}
    second: dict[str, int] = {}
    with session_scope(factory) as session:
        loader.load_repository(session, repo_root=REPO_ROOT)
        first = {
            model.__name__: session.scalar(select(func.count()).select_from(model))
            for model in COUNTED
        }
    with session_scope(factory) as session:
        loader.load_repository(session, repo_root=REPO_ROOT)
        second = {
            model.__name__: session.scalar(select(func.count()).select_from(model))
            for model in COUNTED
        }
    yield factory, {"first": first, "second": second}  # type: ignore[misc]
    engine.dispose()


def test_the_loader_is_idempotent(
    reloaded: tuple[sessionmaker[Session], dict[str, dict[str, int]]],
) -> None:
    """Re-running the backfill must not duplicate a single row.

    ``observations`` and ``comparisons`` have surrogate keys, so this is what
    proves the loader clears and rebuilds them rather than inserting again.
    """
    _, runs = reloaded
    assert runs["first"] == runs["second"]
    assert runs["first"]["Observation"] > 0


def test_a_reset_load_matches_an_incremental_load(
    reloaded: tuple[sessionmaker[Session], dict[str, dict[str, int]]],
) -> None:
    factory, runs = reloaded
    with session_scope(factory) as session:
        loader.load_repository(session, repo_root=REPO_ROOT, reset=True)
        after_reset = {
            model.__name__: session.scalar(select(func.count()).select_from(model))
            for model in COUNTED
        }
    assert after_reset == runs["second"]


def test_the_document_is_identical_from_a_fresh_database(
    reloaded: tuple[sessionmaker[Session], dict[str, dict[str, int]]], committed: dict[str, Any]
) -> None:
    """Byte-for-byte: a second database yields the same chart-data document."""
    from eval_lab_live import chartdata
    from eval_lab_live import repository as repo

    factory, _ = reloaded
    with session_scope(factory) as session:
        dataset = session.get(Dataset, DATASET_ID)
        assert dataset is not None
        document = chartdata.build_document(
            session,
            dataset,
            filters=repo.DocumentFilters(),
            min_slice_records=0,
            max_entities=200,
            max_observations=20000,
        )
    assert document["observations"] == committed["observations"]
    assert document["entities"] == committed["entities"]
    assert document["runs"] == committed["runs"]


@pytest.fixture(scope="module")
def committed() -> dict[str, Any]:
    return json.loads((REPO_ROOT / loader.DATASET_FILE).read_text(encoding="utf-8"))
