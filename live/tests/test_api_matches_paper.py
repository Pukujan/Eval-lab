"""The proof that the API serves the paper's own numbers.

``paper/data/judges-blind-760.json`` is what the papers embed and what
``schemas/research-chart-data.v1.schema.json`` describes.  This module asserts
that ``GET /api/v1/datasets/{id}`` rebuilds that document from the database,
key for key, and that the served bytes validate against the schema.

The one deliberate exception is ``provenance``.  That block records *when* the
export ran, from *which commit*, with the SHA-256 of each input at that moment.
It is a description of the frozen export, not a derivable number, so the loader
stores the committed block verbatim and the API serves it unchanged -- which is
exactly what a paper reader sees.  Everything a chart plots is recomputed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from eval_lab_live import chartdata
from eval_lab_live import repository as repo
from eval_lab_live.loader import DATASET_FILE, build_dataset_document, compare_documents
from eval_lab_live.models import Dataset
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from pyshacl import validate as shacl_validate
from rdflib import Graph
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = REPO_ROOT / "schemas" / "research-chart-data.v1.schema.json"
SHACL_SHAPES = REPO_ROOT / "schemas" / "chart-provenance.shapes.ttl"

#: Every top-level key of the document, so a new one cannot slip in unnoticed.
EXPECTED_KEYS = {
    "@context",
    "id",
    "type",
    "kind",
    "schemaVersion",
    "datasetId",
    "title",
    "description",
    "experimentId",
    "recordCount",
    "population",
    "provenance",
    "levels",
    "dimensions",
    "measures",
    "entities",
    "observations",
    "aggregates",
    "comparisons",
    "experiments",
    "runs",
    "notes",
}


@pytest.fixture(scope="module")
def committed() -> dict[str, Any]:
    return json.loads((REPO_ROOT / DATASET_FILE).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def served(client: TestClient, committed: dict[str, Any]) -> dict[str, Any]:
    response = client.get(f"/api/v1/datasets/{committed['datasetId']}")
    assert response.status_code == 200, response.text
    return response.json()


def test_recomputation_still_matches_the_committed_export() -> None:
    """The loader's own guard, asserted directly.

    If the paper's numbers ever drift from a fresh render of the export script,
    this fails here rather than silently publishing different numbers.
    """
    computed, committed_document = build_dataset_document(REPO_ROOT)
    assert compare_documents(computed, committed_document) is None


def test_api_document_matches_the_paper(served: dict[str, Any], committed: dict[str, Any]) -> None:
    """Every key of the served document equals the committed file's, but provenance."""
    assert set(served) == EXPECTED_KEYS
    assert set(committed) == EXPECTED_KEYS

    differing = sorted(
        key
        for key in EXPECTED_KEYS
        if key != "provenance" and served.get(key) != committed.get(key)
    )
    assert not differing, f"served document differs from the paper on: {differing}"


def test_api_serves_the_committed_provenance_verbatim(
    served: dict[str, Any], committed: dict[str, Any]
) -> None:
    """The provenance block describes the frozen export, so it is served as-is."""
    assert served["provenance"] == committed["provenance"]


def test_served_document_validates_against_the_schema(served: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(served), key=lambda error: list(error.path))
    assert not errors, "\n".join(
        f"{'/'.join(str(part) for part in error.path)}: {error.message}" for error in errors
    )


def test_served_document_validates_against_the_provenance_shapes(
    served: dict[str, Any],
) -> None:
    """SHACL over the JSON-LD graph, as ``tests/test_chart_data_export.py`` does."""
    graph = Graph().parse(data=json.dumps(served), format="json-ld")
    conforms, _, report = shacl_validate(
        graph, shacl_graph=Graph().parse(SHACL_SHAPES, format="turtle")
    )
    assert conforms, report


def test_observation_objects_carry_exactly_the_schema_keys(served: dict[str, Any]) -> None:
    """``additionalProperties: false`` on observations, asserted on real data.

    This is what stops the internal ``slice_records`` column (the min-slice
    denominator) from ever reaching a client.
    """
    expected = {"entity", "slice", "sliceValue", "metric", "value", "ciLow", "ciHigh", "n"}
    observations = served["observations"]
    assert observations, "the document has no observations to check"
    for observation in observations:
        assert set(observation) == expected


def test_the_api_rebuilds_the_document_from_the_tables(
    session_factory: sessionmaker[Session], served: dict[str, Any], committed: dict[str, Any]
) -> None:
    """The API's output comes from the tables, not from re-reading the JSON file.

    ``build_document`` runs against the live rows and is compared with what the
    HTTP endpoint returned, so the endpoint cannot be a file proxy in disguise.
    """
    with session_factory() as session:
        dataset = session.get(Dataset, committed["datasetId"])
        assert dataset is not None
        rebuilt = chartdata.build_document(
            session,
            dataset,
            filters=repo.DocumentFilters(),
            min_slice_records=0,
            max_entities=200,
            max_observations=20000,
        )
    assert rebuilt == served


def test_record_count_is_the_blind_holdout_size(served: dict[str, Any]) -> None:
    """A sanity check that reads like the paper: 760 blind records, no more."""
    assert served["recordCount"] == 760
    assert served["population"]["records"] == 760
    assert served["population"]["partition"] == "blind_holdout"


def test_no_per_record_endpoint_exists(client: TestClient, committed: dict[str, Any]) -> None:
    """There is deliberately no way to ask the API for a single blind record."""
    dataset_id = committed["datasetId"]
    # Positive control: the sibling sub-resource does resolve, so the 404s below
    # are "no such route" rather than the whole prefix being unreachable.
    assert client.get(f"/api/v1/datasets/{dataset_id}/entities").status_code == 200
    for path in (
        f"/api/v1/datasets/{dataset_id}/records",
        f"/api/v1/datasets/{dataset_id}/records/blind-0001",
        "/api/v1/records",
        "/api/v1/predictions",
    ):
        assert client.get(path).status_code == 404, path
