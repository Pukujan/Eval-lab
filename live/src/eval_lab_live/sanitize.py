"""Leakage guards for the public read API.

Three independent controls keep per-record data and gold labels out of public
responses (``docs/architecture/live-app.md`` section 11):

1. **The database.**  Per-record rows live in the ``private`` schema, which the
   API's role has no grant on.  A bug in a query cannot return them: the server
   refuses.  ``live/tests/test_roles_pg.py`` proves it against a real Postgres.
2. **The read model.**  Nothing in the ``live`` schema has a column for record
   text, a prompt, a gold label or a per-record label -- see
   :func:`live_column_names`, which the tests assert against.
3. **The response shape.**  Chart endpoints return ``research-chart-data`` v1
   documents, whose ``observation`` object has ``additionalProperties: false``,
   so an extra column cannot ride along.  :func:`assert_no_denylisted_keys` is
   the belt to that braces: it walks a payload and fails on any key that could
   only be there to carry per-record data.

This module is deliberately dependency-free and is used from tests, not from the
request path, so it never costs a live request anything.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from eval_lab_live.models import LiveBase

#: Key names that must never appear in a public response.  Checked
#: case-insensitively against every key of every nested object.
#:
#: Note what is *absent*: ``label`` (a judge's display label is public),
#: ``records`` (``population.records`` is the population size), ``slice`` and
#: ``n``.  Those are aggregate vocabulary, not per-record data.
DENYLISTED_KEYS = frozenset(
    {
        "answer_key",
        "answerkey",
        "blind_ids",
        "blind_record_ids",
        "candidate",
        "candidates",
        "evidence",
        "gold",
        "gold_label",
        "goldlabel",
        "item_text",
        "items",
        "per_record",
        "prediction",
        "predictions",
        "probabilities",
        "prompt",
        "prompts",
        "raw_scores",
        "record_id",
        "record_ids",
        "record_text",
        "recordid",
        "records_detail",
        "reference_answer",
        "responses",
        "transcript",
        "transcripts",
    }
)

#: Substrings that would give a column away even under another name.
DENYLISTED_COLUMN_FRAGMENTS = ("prompt", "gold", "record_id", "record_text", "answer_key")


class LeakageError(AssertionError):
    """Raised when a payload carries something the public API must not serve."""


def walk_keys(payload: Any, path: str = "$") -> Iterator[tuple[str, str]]:
    """Yield ``(json path, key)`` for every object key in a nested payload."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield f"{path}.{key}", str(key)
            yield from walk_keys(value, f"{path}.{key}")
    elif isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            yield from walk_keys(value, f"{path}[{index}]")


def denylisted_keys(payload: Any) -> list[str]:
    """Every ``json path`` whose key is denylisted, in document order."""
    return [path for path, key in walk_keys(payload) if key.strip().lower() in DENYLISTED_KEYS]


def assert_no_denylisted_keys(payload: Any) -> None:
    """Fail if any nested object key could carry per-record data."""
    offenders = denylisted_keys(payload)
    if offenders:
        raise LeakageError(
            "public response contains denylisted keys: " + ", ".join(sorted(offenders))
        )


def live_column_names() -> set[str]:
    """Every column name in the public-safe ``live`` schema.

    The tests assert that none of them looks like a per-record field, which is
    what makes the "the read model has nowhere to put a gold label" claim
    checkable rather than aspirational.
    """
    names: set[str] = set()
    for table in LiveBase.metadata.tables.values():
        names.update(column.name for column in table.columns)
    return names


def suspicious_columns() -> list[str]:
    """``live`` columns whose name suggests per-record content (expected empty)."""
    return sorted(
        name
        for name in live_column_names()
        if any(fragment in name.lower() for fragment in DENYLISTED_COLUMN_FRAGMENTS)
    )


__all__ = [
    "DENYLISTED_COLUMN_FRAGMENTS",
    "DENYLISTED_KEYS",
    "LeakageError",
    "assert_no_denylisted_keys",
    "denylisted_keys",
    "live_column_names",
    "suspicious_columns",
    "walk_keys",
]
