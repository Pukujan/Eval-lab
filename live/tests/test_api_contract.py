"""Contract tests for the read API: shapes, filters, levels and cache headers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from eval_lab_live import repository as repo
from eval_lab_live.api import create_app
from eval_lab_live.config import IMMUTABLE_CACHE_CONTROL, LIVE_CACHE_CONTROL
from eval_lab_live.models import Artifact, Dataset, Experiment, Observation, Run, RunEntity
from eval_lab_live.sanitize import assert_no_denylisted_keys
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_ID = "eval-lab/judges-blind-760"
LEVELS = ["summary", "breakdown", "experiments", "runs", "table"]

ENTITY_KEYS = {
    "id",
    "label",
    "shortLabel",
    "headline",
    "experiment",
    "experimentIds",
    "deployment",
    "modelFamily",
    "modelId",
    "paramsB",
    "route",
    "harness",
    "settings",
    "settingsEvidence",
    "derived",
    "rankAllRecord",
    "sharedRankAllRecord",
    "recordCount",
    "resolved",
    "correct",
    "statusCounts",
}
OBSERVATION_KEYS = {"entity", "slice", "sliceValue", "metric", "value", "ciLow", "ciHigh", "n"}


# ------------------------------------------------------------------- meta
def test_health_is_liveness_only(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "service": "eval-lab-live", "version": "0.1.0-test"}


def test_health_and_status_are_not_cached(client: TestClient) -> None:
    for path in ("/api/v1/health", "/api/v1/status", "/api/v1/version"):
        assert client.get(path).headers["cache-control"] == "no-store", path


def test_version_reports_the_schema_it_serves(client: TestClient) -> None:
    body = client.get("/api/v1/version").json()
    assert body["apiVersion"] == "v1"
    assert body["schemaVersion"] == "1.0"
    assert body["buildCommit"] == "test-commit"
    # The commit the frozen dataset was exported from, read from the stored provenance.
    assert body["evalLabCommit"]


def test_status_counts_the_loaded_runs(client: TestClient, load_report: Any) -> None:
    body = client.get("/api/v1/status").json()
    assert body["ok"] is True and body["db"] is True
    assert body["runsTotal"] == load_report.runs
    assert body["datasetsTotal"] == 1
    assert body["minSliceRecords"] == 20


def test_status_survives_an_unreachable_database(settings: Any) -> None:
    """The frontend's offline banner needs a 200, not a 500."""
    # No session factory and no schema: the app builds an engine it cannot use.
    app = create_app(settings)
    with TestClient(app) as offline:
        body = offline.get("/api/v1/status").json()
    assert body["ok"] is False and body["db"] is False


# ---------------------------------------------------------------- catalog
def test_projects(client: TestClient) -> None:
    body = client.get("/api/v1/projects").json()
    assert [project["id"] for project in body] == ["eval-lab"]


def test_datasets_list(client: TestClient) -> None:
    body = client.get("/api/v1/datasets").json()
    assert len(body) == 1
    summary = body[0]
    assert summary["id"] == DATASET_ID
    assert summary["recordCount"] == 760
    assert summary["partition"] == "blind_holdout"
    assert summary["levels"] == LEVELS
    assert summary["entityCount"] == 26
    assert summary["observationCount"] == 657


def test_datasets_list_filters_by_project(client: TestClient) -> None:
    assert client.get("/api/v1/datasets", params={"project": "nope"}).json() == []


def test_experiments_are_imported(client: TestClient, session: Session) -> None:
    body = client.get("/api/v1/experiments").json()
    assert len(body) == session.scalar(select(func.count()).select_from(Experiment))
    assert all(experiment["shortId"].startswith("EXP-") for experiment in body)


def test_judges_are_keyed_by_model_and_route(client: TestClient) -> None:
    body = client.get("/api/v1/judges").json()
    assert body
    assert len({judge["id"] for judge in body}) == len(body)
    assert all(judge["id"] == judge["id"].lower() for judge in body)


def test_metrics_registry_matches_the_document(
    client: TestClient, committed: dict[str, Any]
) -> None:
    body = client.get("/api/v1/metrics").json()
    assert [metric["key"] for metric in body] == [
        measure["key"] for measure in committed["measures"]
    ]


# -------------------------------------------------------------- documents
def test_entities_endpoint_matches_the_document(
    client: TestClient, committed: dict[str, Any]
) -> None:
    body = client.get(f"/api/v1/datasets/{DATASET_ID}/entities").json()
    assert body == committed["entities"]
    for entity in body:
        assert set(entity) == ENTITY_KEYS


def test_entities_headline_filter(client: TestClient, committed: dict[str, Any]) -> None:
    body = client.get(f"/api/v1/datasets/{DATASET_ID}/entities", params={"headline": True}).json()
    assert [entity["id"] for entity in body] == [
        entity["id"] for entity in committed["entities"] if entity["headline"]
    ]
    assert 0 < len(body) < len(committed["entities"])


def test_observations_endpoint_matches_the_document(
    client: TestClient, committed: dict[str, Any]
) -> None:
    body = client.get(f"/api/v1/datasets/{DATASET_ID}/observations").json()
    assert body == committed["observations"]
    for observation in body:
        assert set(observation) == OBSERVATION_KEYS


def test_levels_and_dimensions_are_served(client: TestClient, committed: dict[str, Any]) -> None:
    levels = client.get(f"/api/v1/datasets/{DATASET_ID}/levels").json()
    assert [level["key"] for level in levels] == LEVELS
    assert levels == committed["levels"]

    dimensions = client.get(f"/api/v1/datasets/{DATASET_ID}/dimensions").json()
    assert dimensions == committed["dimensions"]


def test_filters_offer_only_live_values(client: TestClient, committed: dict[str, Any]) -> None:
    body = client.get(f"/api/v1/datasets/{DATASET_ID}/filters").json()
    assert sorted(body["entities"]) == sorted(entity["id"] for entity in committed["entities"])
    assert sorted(body["metrics"]) == sorted(measure["key"] for measure in committed["measures"])
    assert body["slices"] == ["mode", "overall", "taskSource"]
    assert body["levels"] == LEVELS
    assert set(body["slice_values"]["mode"]) == {
        observation["sliceValue"]
        for observation in committed["observations"]
        if observation["slice"] == "mode"
    }


# ----------------------------------------------------------------- levels
def test_level_summary_is_the_overall_slice(client: TestClient) -> None:
    body = client.get(f"/api/v1/datasets/{DATASET_ID}", params={"level": "summary"}).json()
    assert {observation["slice"] for observation in body["observations"]} == {"overall"}


def test_level_breakdown_excludes_the_overall_slice(client: TestClient) -> None:
    body = client.get(f"/api/v1/datasets/{DATASET_ID}", params={"level": "breakdown"}).json()
    slices = {observation["slice"] for observation in body["observations"]}
    assert "overall" not in slices and slices


def test_level_experiments_keeps_the_runs_array(client: TestClient) -> None:
    body = client.get(f"/api/v1/datasets/{DATASET_ID}", params={"level": "experiments"}).json()
    assert body["runs"]
    assert {observation["slice"] for observation in body["observations"]} == {"overall"}


def test_level_table_drops_the_runs_array(client: TestClient) -> None:
    """The ``table`` level is the cheapest view, so it omits per-run provenance."""
    body = client.get(f"/api/v1/datasets/{DATASET_ID}", params={"level": "table"}).json()
    assert body["runs"] == []


def test_unknown_level_is_a_client_error(client: TestClient) -> None:
    response = client.get(f"/api/v1/datasets/{DATASET_ID}", params={"level": "nope"})
    assert response.status_code == 400
    assert "unknown level" in response.json()["detail"]


# ---------------------------------------------------------------- filters
def test_entity_filter_narrows_the_document(client: TestClient, committed: dict[str, Any]) -> None:
    wanted = committed["entities"][0]["id"]
    body = client.get(f"/api/v1/datasets/{DATASET_ID}", params={"entity": wanted}).json()
    assert [entity["id"] for entity in body["entities"]] == [wanted]
    assert {observation["entity"] for observation in body["observations"]} == {wanted}


def test_metric_filter_narrows_the_observations(client: TestClient) -> None:
    body = client.get(
        f"/api/v1/datasets/{DATASET_ID}",
        params={"metric": "coverage", "level": "summary"},
    ).json()
    assert {observation["metric"] for observation in body["observations"]} == {"coverage"}


def test_slice_filters_narrow_the_observations(client: TestClient) -> None:
    body = client.get(
        f"/api/v1/datasets/{DATASET_ID}",
        params={"slice": "mode", "slice_value": "single"},
    ).json()
    assert {observation["slice"] for observation in body["observations"]} == {"mode"}
    assert {observation["sliceValue"] for observation in body["observations"]} == {"single"}


def test_a_filter_that_matches_nothing_is_a_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/datasets/{DATASET_ID}", params={"entity": "nope"})
    assert response.status_code == 404


def test_unknown_dataset_is_a_404(client: TestClient) -> None:
    assert client.get("/api/v1/datasets/nope").status_code == 404


# ----------------------------------------------------- min-slice suppression
def test_min_slice_suppression_drops_small_slices(session: Session) -> None:
    """The rule itself, exercised against the repository.

    ``slice_records`` is the only place a slice's *population* is recorded -- the
    per-observation ``n`` is a per-entity resolved count and cannot be used for
    this.  The frozen paper dataset opts out (see the test below), so the rule is
    checked by asking the repository for a suppressed view directly.

    The smallest slice in the paper is "Eval Lab synthetic (4 families)" at 20
    records, which the default threshold of 20 keeps, so this drives the rule at
    21: the population, not the entity, is what decides.
    """
    from eval_lab_live.models import Observation

    populations = _slice_populations(session)
    assert min(populations.values()) == 20
    threshold = 21
    kept = {cell for cell, records in populations.items() if records >= threshold}
    dropped = set(populations) - kept
    assert dropped == {("taskSource", "Eval Lab synthetic (4 families)")}

    entity_ids = list(
        session.scalars(select(Observation.entity_id).where(Observation.dataset_id == DATASET_ID))
    )
    filtered = repo.list_observations(
        session,
        DATASET_ID,
        sorted(set(entity_ids)),
        repo.DocumentFilters(level="breakdown"),
        min_slice_records=threshold,
        level="breakdown",
        limit=20000,
    )
    cells = {(observation.slice_dim, observation.slice_value) for observation in filtered}
    assert cells == kept


def _slice_populations(session: Session) -> dict[tuple[str, str], int]:
    """The population of every non-overall slice, and the invariant behind it.

    ``slice_records`` describes the *cell*, not the row, so every observation of
    one (slice, sliceValue) pair must carry the same value -- otherwise the rule
    would keep a cell for its accuracy row and drop it for its coverage row.
    """
    from eval_lab_live.models import Observation

    by_cell: dict[tuple[str, str], set[int]] = {}
    for dim, value, records in session.execute(
        select(Observation.slice_dim, Observation.slice_value, Observation.slice_records).where(
            Observation.dataset_id == DATASET_ID, Observation.slice_dim != "overall"
        )
    ).all():
        by_cell.setdefault((dim, value), set()).add(records)
    assert by_cell
    inconsistent = {cell: seen for cell, seen in by_cell.items() if len(seen) != 1}
    assert inconsistent == {}, f"slice_records is not a property of the cell: {inconsistent}"
    return {cell: next(iter(seen)) for cell, seen in by_cell.items()}


def test_the_published_dataset_opts_out_of_suppression(
    client: TestClient,
    session: Session,
    settings: Any,
    session_factory: Any,
    committed: dict[str, Any],
) -> None:
    """The 760-record holdout is served in full, exactly as the paper publishes it.

    All 760 records and their gold labels are in this public repository, so the
    min-slice rule protects nothing here, and a raised threshold would start
    hiding slices the paper prints.  The dataset row records that decision
    explicitly rather than relying on the configured default, so the served
    document keeps matching the paper whatever ``EVALLAB_LIVE_MIN_SLICE_RECORDS``
    is set to.
    """
    dataset = session.get(Dataset, DATASET_ID)
    assert dataset is not None
    assert dataset.min_slice_records == 0

    served = client.get(f"/api/v1/datasets/{DATASET_ID}").json()
    assert len(served["observations"]) == len(committed["observations"])

    # The same database, served by an app whose configured threshold would
    # suppress a published slice.  The override is the only reason it does not.
    strict = create_app(
        settings.model_copy(update={"min_slice_records": 21}), session_factory=session_factory
    )
    with TestClient(strict) as strict_client:
        under_a_strict_threshold = strict_client.get(f"/api/v1/datasets/{DATASET_ID}").json()
    assert under_a_strict_threshold == served
    assert min(_slice_populations(session).values()) < 21


def test_a_dataset_without_an_override_uses_the_configured_threshold(settings: Any) -> None:
    """The mechanism is live for future datasets: NULL means 'use the setting'.

    Built as a throwaway row rather than by mutating the loaded one, so this
    cannot leak into the other tests that share the session.
    """
    from eval_lab_live.api import _min_slice_records

    assert _min_slice_records(Dataset(id="x", min_slice_records=None), settings) == 20
    assert _min_slice_records(Dataset(id="x", min_slice_records=0), settings) == 0
    assert _min_slice_records(Dataset(id="x", min_slice_records=5), settings) == 5


def test_overall_slices_are_never_suppressed(session: Session) -> None:
    """The rule must not hide the headline numbers, whatever their population."""
    filtered = repo.list_observations(
        session,
        DATASET_ID,
        sorted(
            {
                entity_id
                for entity_id in session.scalars(
                    select(Observation.entity_id).where(Observation.dataset_id == DATASET_ID)
                )
            }
        ),
        repo.DocumentFilters(level="summary"),
        min_slice_records=10_000,
        level="summary",
        limit=20000,
    )
    assert filtered
    assert {observation.slice_dim for observation in filtered} == {"overall"}


# ------------------------------------------------------------ other views
def test_leaderboard_is_a_full_document(client: TestClient, committed: dict[str, Any]) -> None:
    body = client.get("/api/v1/leaderboard").json()
    assert body["datasetId"] == DATASET_ID
    assert len(body["entities"]) == len(committed["entities"])
    assert body["observations"]


def test_explore_accepts_the_same_filters_as_the_dataset_route(
    client: TestClient, committed: dict[str, Any]
) -> None:
    wanted = committed["entities"][1]["id"]
    body = client.get("/api/v1/explore", params={"entity": wanted, "level": "summary"}).json()
    assert [entity["id"] for entity in body["entities"]] == [wanted]


# ------------------------------------------------------------------- runs
def test_runs_are_listed(client: TestClient, load_report: Any) -> None:
    body = client.get("/api/v1/runs").json()
    assert len(body) == load_report.runs
    assert all(run["resultsPath"] for run in body)


def test_run_detail_and_provenance(client: TestClient, session: Session) -> None:
    # A run id can be a repository path (runs whose own id was not unique), so
    # this deliberately exercises both shapes, on runs that carry artifacts.
    def one_run_id(*conditions: Any) -> str | None:
        return session.scalars(
            select(Run.run_id)
            .join(Artifact, Artifact.run_id == Run.run_id)
            .where(*conditions)
            .order_by(Run.run_id)
        ).first()

    run_ids = [
        one_run_id(Run.source_run_id.is_(None)),
        one_run_id(Run.run_id.startswith("experiments/")),
    ]
    assert all(run_id is not None for run_id in run_ids)

    for run_id in run_ids:
        detail = client.get(f"/api/v1/runs/{run_id}").json()
        assert detail["runId"] == run_id
        assert detail["resultsSha256"]
        assert detail["artifacts"]

        graph = client.get(f"/api/v1/runs/{run_id}/provenance.jsonld").json()
        assert "@context" in graph and "@graph" in graph
        assert any(node["@id"] == f"urn:eval-lab:run:{run_id}" for node in graph["@graph"])
        assert any(node["@type"] == "prov:Activity" for node in graph["@graph"])


def test_unknown_run_is_a_404(client: TestClient) -> None:
    assert client.get("/api/v1/runs/nope").status_code == 404


def test_every_chart_run_is_linked_to_a_committed_run(
    session: Session, committed: dict[str, Any], load_report: Any
) -> None:
    """Each ``runs[]`` entry in the paper's document traces to an imported run."""
    links = session.execute(select(RunEntity.entity_id, RunEntity.artifact_path)).all()
    assert len(links) == len(committed["runs"])
    assert len(links) == load_report.run_entities


def test_snapshots_are_empty_until_phase_six(client: TestClient) -> None:
    """Snapshots arrive in phase 6; the endpoint exists and is honest about it."""
    assert client.get("/api/v1/snapshots").json() == []
    assert client.get("/api/v1/snapshots/nope").status_code == 404


# ------------------------------------------------------------ cache headers
def test_documents_are_cacheable_with_a_short_ttl(client: TestClient) -> None:
    response = client.get(f"/api/v1/datasets/{DATASET_ID}")
    assert response.headers["cache-control"] == LIVE_CACHE_CONTROL
    assert response.headers["cdn-cache-control"]
    assert response.headers["vercel-cache-tag"] == f"eval-lab-{DATASET_ID}"


def test_snapshot_documents_are_immutable(client: TestClient, session: Session) -> None:
    """Phase 6 freezes snapshots; this pins the header contract for when it lands."""
    from eval_lab_live.models import Snapshot

    snapshot = Snapshot(
        id="snap-test",
        schema_version="1.0",
        content={"kind": "dataset"},
        sha256="0" * 64,
        run_ids=[],
        all_runs_committed=True,
    )
    session.add(snapshot)
    session.commit()
    try:
        response = client.get("/api/v1/snapshots/snap-test")
        assert response.status_code == 200
        assert response.headers["cache-control"] == IMMUTABLE_CACHE_CONTROL
        assert response.json() == {"kind": "dataset"}
    finally:
        session.delete(snapshot)
        session.commit()


def test_openapi_documents_every_route(client: TestClient) -> None:
    paths = client.get("/api/openapi.json").json()["paths"]
    for path in (
        "/api/v1/health",
        "/api/v1/version",
        "/api/v1/status",
        "/api/v1/datasets",
        "/api/v1/datasets/{dataset_id}",
        "/api/v1/datasets/{dataset_id}/entities",
        "/api/v1/datasets/{dataset_id}/observations",
        "/api/v1/datasets/{dataset_id}/filters",
        "/api/v1/datasets/{dataset_id}/levels",
        "/api/v1/leaderboard",
        "/api/v1/explore",
        "/api/v1/runs",
        "/api/v1/runs/{run_id}",
        "/api/v1/snapshots",
    ):
        assert path in paths, path


@pytest.fixture(scope="module")
def committed() -> dict[str, Any]:
    return json.loads(
        (REPO_ROOT / "paper" / "data" / "judges-blind-760.json").read_text(encoding="utf-8")
    )


def test_contract_responses_never_carry_denylisted_keys(client: TestClient) -> None:
    """Every catalog response is walked for per-record vocabulary."""
    for path in (
        "/api/v1/datasets",
        f"/api/v1/datasets/{DATASET_ID}",
        f"/api/v1/datasets/{DATASET_ID}/entities",
        f"/api/v1/datasets/{DATASET_ID}/observations",
        f"/api/v1/datasets/{DATASET_ID}/filters",
        "/api/v1/experiments",
        "/api/v1/judges",
        "/api/v1/metrics",
        "/api/v1/runs",
        "/api/v1/leaderboard",
    ):
        assert_no_denylisted_keys(client.get(path).json())
