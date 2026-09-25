"""Shared fixtures for the live backend tests.

The heavy fixture is :func:`database`: it builds a fresh SQLite database (two
attached in-memory databases named ``live`` and ``private``, so the models keep
their real schema names) and runs the full backfill over the checkout.  It is
session-scoped because the backfill recomputes the paper's dataset through
``scripts/export_chart_data.py`` -- which is the whole point of the test, and is
not cheap.  Everything else derives from it, so the backfill runs exactly once.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from eval_lab_live.api import create_app
from eval_lab_live.config import Settings
from eval_lab_live.db import create_db_engine, create_schema, make_session_factory, session_scope
from eval_lab_live.loader import LoadReport, load_repository
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

#: ``live/tests/conftest.py`` -> the repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]

#: Postgres-only tests (migrations, role separation) skip without this.
PG_ENV = "EVALLAB_LIVE_TEST_DATABASE_URL"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        repo_root=REPO_ROOT,
        build_commit="test-commit",
        service_version="0.1.0-test",
        default_project="eval-lab",
    )


@pytest.fixture(scope="session")
def database(settings: Settings) -> Iterator[tuple[sessionmaker[Session], LoadReport]]:
    """A fully backfilled throwaway database, built once per test session."""
    engine: Engine = create_db_engine(settings.database_url)
    create_schema(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as session:
        report = load_repository(session, repo_root=settings.repo_root)
    yield factory, report
    engine.dispose()


@pytest.fixture(scope="session")
def session_factory(database: tuple[sessionmaker[Session], LoadReport]) -> sessionmaker[Session]:
    return database[0]


@pytest.fixture(scope="session")
def load_report(database: tuple[sessionmaker[Session], LoadReport]) -> LoadReport:
    return database[1]


@pytest.fixture(scope="session")
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_scope(session_factory) as open_session:
        yield open_session


@pytest.fixture(scope="session")
def client(settings: Settings, session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    app = create_app(settings, session_factory=session_factory)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def pg_url() -> str:
    url = os.environ.get(PG_ENV)
    if not url:
        pytest.skip(f"set {PG_ENV} to run the Postgres migration and role tests")
    return url
