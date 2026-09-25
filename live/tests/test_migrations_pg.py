"""Postgres-only tests: migrations, and the role separation that backstops leakage.

Skipped unless ``EVALLAB_LIVE_TEST_DATABASE_URL`` points at a Postgres the test
may migrate as an owner.  CI sets it from a ``postgres:17`` service container;
locally, ``cd live && docker compose up -d db`` gives you one:

    EVALLAB_LIVE_TEST_DATABASE_URL=postgresql+psycopg://evallab:evallab@localhost:55432/evallab \\
        python -m pytest live/tests/test_migrations_pg.py -q

The second half of this module is the leakage backstop from the architecture
doc's section 11: the API's role must be *unable* to read ``private``, so a bug
in a query cannot return per-record rows.  A test on SQLite cannot show this,
which is why it lives here.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from eval_lab_live.models import LiveBase, PrivateBase
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ProgrammingError

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = REPO_ROOT / "live" / "alembic.ini"

PUBLIC_RO = "evallab_public_ro"
INGEST_RW = "evallab_ingest_rw"

#: Throwaway passwords for a local/CI test database.  Never used anywhere else.
TEST_PASSWORDS = {PUBLIC_RO: "evallab_public_ro_test", INGEST_RW: "evallab_ingest_rw_test"}

LIVE_TABLES = set(LiveBase.metadata.tables)
PRIVATE_TABLES = set(PrivateBase.metadata.tables)


def _config(url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url)
    return config


def _ensure_roles(engine: Engine, database: str) -> None:
    """Create the two application roles if the connecting user may.

    Mirrors ``live/docker/bootstrap/10-roles.sh`` so the local path and the
    compose path agree.  CI's service container connects as its superuser, so
    this runs there too; a non-superuser role skips it (see the caller).
    """
    with engine.begin() as connection:
        for role, password in TEST_PASSWORDS.items():
            exists = connection.execute(
                text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": role}
            ).scalar()
            if not exists:
                connection.execute(text(f"CREATE ROLE \"{role}\" LOGIN PASSWORD '{password}'"))
        connection.execute(
            text(f'GRANT CONNECT ON DATABASE "{database}" TO {PUBLIC_RO}, {INGEST_RW}')
        )


@pytest.fixture(scope="module")
def migrated(pg_url: str) -> Iterator[str]:
    """Bring the database to ``head`` twice, through ``base``, as the owner."""
    database = make_url(pg_url).database or "postgres"
    owner = create_engine(pg_url, future=True, isolation_level="AUTOCOMMIT")
    try:
        _ensure_roles(owner, database)
    except ProgrammingError:  # pragma: no cover - a non-superuser CI role
        pass

    config = _config(pg_url)
    # A clean slate, so this is a real test of the migration chain rather than of
    # whatever the previous run left behind.
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield pg_url
    command.downgrade(config, "base")
    owner.dispose()


def test_the_migration_creates_both_schemas(migrated: str) -> None:
    engine = create_engine(migrated, future=True)
    try:
        inspector = inspect(engine)
        assert set(inspector.get_schema_names()) >= {"live", "private"}
        assert set(inspector.get_table_names(schema="live")) >= LIVE_TABLES
        assert set(inspector.get_table_names(schema="private")) >= PRIVATE_TABLES
    finally:
        engine.dispose()


def test_every_model_table_exists_with_every_column(migrated: str) -> None:
    """The hand-written DDL and the ORM metadata must agree, column for column."""
    engine = create_engine(migrated, future=True)
    try:
        inspector = inspect(engine)
        for table in list(LiveBase.metadata.tables.values()) + list(
            PrivateBase.metadata.tables.values()
        ):
            actual = {
                column["name"] for column in inspector.get_columns(table.name, schema=table.schema)
            }
            expected = {column.name for column in table.columns}
            assert actual == expected, f"{table.schema}.{table.name}: {actual ^ expected}"
    finally:
        engine.dispose()


def test_alembic_records_its_version_in_the_live_schema(migrated: str) -> None:
    engine = create_engine(migrated, future=True)
    try:
        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM live.alembic_version")
            ).scalar()
        assert revision == "0002_roles"
    finally:
        engine.dispose()


def test_the_downgrade_removes_the_schemas_objects(migrated: str) -> None:
    """``upgrade``/``downgrade`` round-trips, which CI runs on every PR."""
    engine = create_engine(migrated, future=True)
    config = _config(migrated)
    try:
        command.downgrade(config, "base")
        inspector = inspect(engine)
        remaining = set(inspector.get_table_names(schema="live")) & LIVE_TABLES
        assert remaining == set()
    finally:
        command.upgrade(config, "head")
        engine.dispose()


# --------------------------------------------------------------- role separation
def test_the_public_role_can_read_the_public_schema(migrated: str) -> None:
    engine = _as_role(migrated, PUBLIC_RO)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM live.datasets")).scalar() == 0
            assert connection.execute(text("SELECT count(*) FROM live.observations")).scalar() == 0
    finally:
        engine.dispose()


def test_the_public_role_cannot_read_the_private_schema(migrated: str) -> None:
    """The leakage backstop: ``SELECT`` on a per-record table is refused by the server."""
    engine = _as_role(migrated, PUBLIC_RO)
    try:
        with engine.connect() as connection:
            for statement in (
                "SELECT count(*) FROM private.predictions",
                "SELECT count(*) FROM private.runner_tokens",
            ):
                with pytest.raises(ProgrammingError) as failure:
                    connection.execute(text(statement))
                assert "permission denied" in str(failure.value).lower(), statement
    finally:
        engine.dispose()


def test_the_public_role_cannot_create_objects(migrated: str) -> None:
    """No DDL, so a compromised API process cannot add a table it could read."""
    engine = _as_role(migrated, PUBLIC_RO)
    try:
        with engine.connect() as connection, pytest.raises(ProgrammingError):
            connection.execute(text("CREATE TABLE live.smuggled (id int)"))
    finally:
        engine.dispose()


def test_the_ingest_role_can_write_both_schemas(migrated: str) -> None:
    """The loader needs DML on ``live`` and on the per-record schema (phase 3)."""
    engine = _as_role(migrated, INGEST_RW)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO live.projects (id, name, created_at) "
                    "VALUES ('probe', 'probe', now()) ON CONFLICT (id) DO NOTHING"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO private.predictions (run_id, record_id, label) "
                    "VALUES ('probe', 'probe', 'pass')"
                )
            )
            connection.execute(text("DELETE FROM private.predictions WHERE run_id = 'probe'"))
            connection.execute(text("DELETE FROM live.projects WHERE id = 'probe'"))
    finally:
        engine.dispose()


def test_the_catalog_confirms_the_grant_boundary(migrated: str) -> None:
    """Both directions, read from Postgres itself rather than from a query attempt.

    The reverse check matters as much as the first: a role that had lost its
    ``SELECT`` on ``live`` would make the leakage tests pass for the wrong
    reason.
    """
    engine = create_engine(migrated, future=True)
    try:
        with engine.connect() as connection:

            def privilege(function: str, target: str, what: str) -> bool:
                return bool(
                    connection.execute(
                        text(f"SELECT {function}('{PUBLIC_RO}', '{target}', '{what}')")
                    ).scalar()
                )

            assert not privilege("has_schema_privilege", "private", "USAGE")
            assert not privilege("has_schema_privilege", "live", "CREATE")
            assert privilege("has_schema_privilege", "live", "USAGE")
            for table in sorted(PRIVATE_TABLES):
                assert not privilege("has_table_privilege", f"private.{table}", "SELECT"), table
            for table in sorted(LIVE_TABLES):
                assert privilege("has_table_privilege", f"live.{table}", "SELECT"), table
            # PUBLIC (i.e. every role) must not reach the private schema either.
            assert not connection.execute(
                text("SELECT has_schema_privilege('public', 'private', 'USAGE')")
            ).scalar()
    finally:
        engine.dispose()


def _as_role(url: str, role: str) -> Engine:
    return create_engine(
        make_url(url).set(username=role, password=TEST_PASSWORDS[role]),
        future=True,
        isolation_level="AUTOCOMMIT",
    )
