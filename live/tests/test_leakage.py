"""Leakage tests: the public API must never expose blind records or gold labels.

Four independent controls are asserted here, matching the architecture doc's
section 11:

* the response shape (:mod:`eval_lab_live.sanitize` walks every key);
* the read model (nothing in the ``live`` schema can hold a record or a label);
* the loader (no per-record row is written anywhere);
* the data itself (no blind record id appears in any response body).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from eval_lab_live.models import Prediction, PrivateBase, RunnerToken
from eval_lab_live.sanitize import (
    DENYLISTED_KEYS,
    LeakageError,
    assert_no_denylisted_keys,
    denylisted_keys,
    live_column_names,
    suspicious_columns,
)
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_ID = "eval-lab/judges-blind-760"

#: A committed list of blind record ids, used as a corpus of strings that must
#: not appear in a public response.  The ids encode the answer class
#: (``arc-single:Mercury_7221620:correct``), so leaking one leaks a gold label.
BLIND_IDS_FILE = (
    REPO_ROOT
    / "experiments"
    / "EXP-20260921-013-qwen-multidomain-holdout"
    / "blind-retry-record-ids.txt"
)

#: Every public route, so the checks below cannot miss one.
PUBLIC_PATHS = (
    "/api/v1/health",
    "/api/v1/version",
    "/api/v1/status",
    "/api/v1/projects",
    "/api/v1/datasets",
    "/api/v1/experiments",
    "/api/v1/judges",
    "/api/v1/metrics",
    "/api/v1/runs",
    "/api/v1/snapshots",
    "/api/v1/leaderboard",
    f"/api/v1/datasets/{DATASET_ID}",
    f"/api/v1/datasets/{DATASET_ID}/entities",
    f"/api/v1/datasets/{DATASET_ID}/observations",
    f"/api/v1/datasets/{DATASET_ID}/filters",
    f"/api/v1/datasets/{DATASET_ID}/levels",
    f"/api/v1/datasets/{DATASET_ID}/dimensions",
    "/api/v1/explore?level=breakdown",
    f"/api/v1/datasets/{DATASET_ID}?level=table",
)


@pytest.fixture(scope="module")
def blind_record_ids() -> list[str]:
    if not BLIND_IDS_FILE.is_file():  # pragma: no cover - the file is committed
        pytest.skip(f"missing blind id corpus: {BLIND_IDS_FILE}")
    ids = [
        line.strip()
        for line in BLIND_IDS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(ids) > 100
    return ids


def test_the_guard_itself_catches_a_planted_leak() -> None:
    """The denylist must not be vacuous."""
    planted = {"observations": [{"entity": "a", "gold_label": "pass"}]}
    assert denylisted_keys(planted) == ["$.observations[0].gold_label"]
    with pytest.raises(LeakageError):
        assert_no_denylisted_keys(planted)
    assert_no_denylisted_keys({"entity": "a", "label": "a judge's name", "n": 5})


def test_no_public_response_carries_a_denylisted_key(client: TestClient) -> None:
    for path in PUBLIC_PATHS:
        response = client.get(path)
        assert response.status_code == 200, (path, response.status_code)
        assert_no_denylisted_keys(response.json())


def test_no_public_response_carries_a_blind_record_id(
    client: TestClient, blind_record_ids: list[str]
) -> None:
    """A substring scan of the raw bodies: the strongest form of this check."""
    for path in PUBLIC_PATHS:
        body = client.get(path).text
        leaked = [record_id for record_id in blind_record_ids if record_id in body]
        assert not leaked, f"{path} leaks blind record ids: {leaked[:5]}"


def test_the_denylist_covers_the_fields_the_architecture_names() -> None:
    """``gold``, ``prompt``, ``candidate_*``, ``answer_key``, ``evidence`` (section 11)."""
    for field in ("gold", "gold_label", "prompt", "prompts", "answer_key", "evidence"):
        assert field in DENYLISTED_KEYS


def test_the_read_model_has_nowhere_to_put_a_record() -> None:
    """No column in the ``live`` schema looks like per-record content.

    This is the structural half of the control: even a query written by mistake
    has nothing to select.
    """
    assert suspicious_columns() == []
    columns = live_column_names()
    assert "record_count" in columns  # aggregates are fine
    assert "gold" not in columns and "prompt" not in columns


def test_private_tables_are_empty_after_a_backfill(session: Session) -> None:
    """Phase 2 imports no per-record row at all: the tables exist, and stay empty."""
    assert session.scalar(select(func.count()).select_from(Prediction)) == 0
    assert session.scalar(select(func.count()).select_from(RunnerToken)) == 0


def test_the_private_schema_is_separate_and_declared() -> None:
    """``predictions`` is the only per-record table, and it lives in ``private``."""
    names = {table.name: table.schema for table in PrivateBase.metadata.tables.values()}
    assert names == {"predictions": "private", "runner_tokens": "private"}


def test_no_route_mentions_a_private_table(client: TestClient) -> None:
    paths = " ".join(client.get("/api/openapi.json").json()["paths"])
    for forbidden in ("prediction", "runner_token", "gold", "record"):
        assert forbidden not in paths.lower()


def test_the_served_document_has_no_per_record_granularity(
    client: TestClient, blind_record_ids: list[str]
) -> None:
    """The finest grain is one row per arm, slice and metric -- never a record.

    Every observation is an aggregate over at least one entity and slice, so the
    document's cardinality is bounded by entities x slices x metrics rather than
    by the 760 records.
    """
    document = client.get(f"/api/v1/datasets/{DATASET_ID}").json()
    observations = document["observations"]
    cells = {
        (
            observation["entity"],
            observation["slice"],
            observation["sliceValue"],
            observation["metric"],
        )
        for observation in observations
    }
    assert len(cells) == len(observations), "an observation is not uniquely keyed by a cell"
    assert len(observations) < document["recordCount"] * 2
    assert not any(record_id in json.dumps(document) for record_id in blind_record_ids)
