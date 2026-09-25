"""Engine, session factory and schema helpers.

The same models run on Postgres 17 (production and the CI service container) and
on SQLite (the fast unit-test path).  SQLite has no schemas, so a SQLite engine
here attaches two in-memory databases named ``live`` and ``private`` to the main
connection; the models then use their real schema names on both backends and
nothing in the query layer needs a dialect branch.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from eval_lab_live.models import LiveBase, PrivateBase

SQLITE_PREFIXES = ("sqlite:", "sqlite+")


def _is_sqlite(url: str) -> bool:
    return url.startswith(SQLITE_PREFIXES)


def create_db_engine(url: str, *, echo: bool = False) -> Engine:
    """Build an engine that works for both Postgres and SQLite."""
    if not _is_sqlite(url):
        return create_engine(url, echo=echo, pool_pre_ping=True, future=True)

    engine = create_engine(
        url,
        echo=echo,
        future=True,
        # One physical connection, so the attached in-memory schemas are shared
        # by every session.
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _attach_schemas(dbapi_connection: Any, _record: Any) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("ATTACH DATABASE ':memory:' AS live")
            cursor.execute("ATTACH DATABASE ':memory:' AS private")
        finally:
            cursor.close()

    return engine


def create_schema(engine: Engine) -> None:
    """Create both schemas.  Migrations own this in production; tests use it."""
    LiveBase.metadata.create_all(engine)
    PrivateBase.metadata.create_all(engine)


def drop_schema(engine: Engine) -> None:
    PrivateBase.metadata.drop_all(engine)
    LiveBase.metadata.drop_all(engine)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


__all__ = [
    "create_db_engine",
    "create_schema",
    "drop_schema",
    "make_session_factory",
    "session_scope",
]
