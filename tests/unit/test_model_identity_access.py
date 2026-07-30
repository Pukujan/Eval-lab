"""Model-identity access tests.

The negative is the point: ordinary workflow components must be unable to reach
real vendor/model identities (ADR-0008, threat model T-2).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.domain.schemas import ModelRole, PrivilegedModelIdentity
from app.models.blinding import (
    IdentityLeakError,
    assert_blinded,
    blind_models,
    find_identity_leaks,
    generate_pseudonym,
)
from app.storage.audit import AuditStore, AuditStoreError
from app.storage.privileged import (
    PrivilegedAccess,
    PrivilegedAccessError,
    PrivilegedIdentityStore,
)


@pytest.fixture
def privileged_store(tmp_path: Path) -> PrivilegedIdentityStore:
    store = PrivilegedIdentityStore(
        tmp_path / "privileged.db", PrivilegedAccess(granted_to="test-harness")
    )
    store.record(
        "run-1",
        PrivilegedModelIdentity(
            pseudonym="model-aabbccdd",
            vendor="acme-vendor",
            model_identifier="acme-model-9",
            resolved_model_identifier="acme-model-9",
            endpoint="litellm-proxy",
        ),
    )
    yield store
    store.close()


def test_privileged_store_requires_a_capability(tmp_path: Path) -> None:
    """Workflow code cannot construct the store without an explicit capability."""
    with pytest.raises(PrivilegedAccessError):
        PrivilegedIdentityStore(tmp_path / "p.db", access=None)  # type: ignore[arg-type]

    with pytest.raises(PrivilegedAccessError):
        PrivilegedIdentityStore(tmp_path / "p.db", access="i-am-authorised")  # type: ignore[arg-type]


def test_capability_needs_a_named_holder() -> None:
    with pytest.raises(PrivilegedAccessError):
        PrivilegedAccess(granted_to="")


def test_privileged_store_resolves_only_with_the_capability(
    privileged_store: PrivilegedIdentityStore,
) -> None:
    identity = privileged_store.resolve("model-aabbccdd")
    assert identity is not None
    assert identity.vendor == "acme-vendor"


def test_audit_store_cannot_resolve_a_pseudonym(tmp_path: Path) -> None:
    """The agent-accessible store has no mapping to resolve."""
    audit = AuditStore(tmp_path / "audit.db")
    try:
        assert audit.resolve_model_identity("model-aabbccdd") is None
    finally:
        audit.close()


def test_audit_database_has_no_identity_table(tmp_path: Path) -> None:
    """A separate file, not a convention: the table simply is not there."""
    audit_path = tmp_path / "audit.db"
    audit = AuditStore(audit_path)
    audit.close()

    connection = sqlite3.connect(str(audit_path))
    try:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        connection.close()

    assert "model_identities" not in tables
    for table in tables:
        columns = set()
        connection = sqlite3.connect(str(audit_path))
        try:
            columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        finally:
            connection.close()
        assert "vendor" not in columns, f"table {table} exposes a vendor column"


def test_audit_store_refuses_to_persist_identity_fields(tmp_path: Path) -> None:
    audit = AuditStore(tmp_path / "audit.db")
    try:
        with pytest.raises(AuditStoreError):
            audit._reject_identity_fields({"vendor": "acme-vendor", "run_id": "r"})
    finally:
        audit.close()


def test_pseudonyms_are_unpredictable_and_well_shaped() -> None:
    pseudonyms = {generate_pseudonym() for _ in range(200)}
    assert len(pseudonyms) > 190, "pseudonyms should not collide in practice"
    for pseudonym in pseudonyms:
        assert pseudonym.startswith("model-") and len(pseudonym) == len("model-") + 8


def test_blinding_assigns_pseudonyms_and_randomises_order() -> None:
    assignments = (
        (ModelRole.SOLVER, "vendor-x", "model-x", "litellm-proxy"),
        (ModelRole.CRITIC, "vendor-y", "model-y", "litellm-proxy"),
        (ModelRole.VERIFIER, "vendor-z", "model-z", "litellm-proxy"),
    )
    result = blind_models(assignments, run_seed=1234)

    assert len(result.anonymous) == 3
    assert {i.presentation_order for i in result.anonymous} == {0, 1, 2}
    # Nothing a role can see names a vendor.
    for identity in result.anonymous:
        assert not find_identity_leaks(identity.pseudonym)
        assert "vendor" not in identity.pseudonym

    # A different seed generally produces a different order.
    orders = {
        tuple(i.role for i in blind_models(assignments, run_seed=seed).anonymous)
        for seed in range(30)
    }
    assert len(orders) > 1, "candidate order must vary across runs"


def test_assert_blinded_blocks_a_prompt_naming_a_real_model() -> None:
    assert_blinded('{"task_type":"generate_hypotheses"}')

    with pytest.raises(IdentityLeakError):
        assert_blinded("You are Claude, respond as gpt-4o would.")

    with pytest.raises(IdentityLeakError):
        assert_blinded('{"model":"anthropic/some-model"}', context="task payload")


def test_leak_detection_does_not_fire_on_ordinary_words() -> None:
    """A denylist that flags normal prose gets switched off, so it must not."""
    assert not find_identity_leaks("The metallama pattern and gptolemy notes are fine.")
    assert not find_identity_leaks("Concurrency: check-then-write race in the claim path.")
