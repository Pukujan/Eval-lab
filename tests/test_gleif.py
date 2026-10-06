from __future__ import annotations

from pathlib import Path

import pytest

from eval_lab.datasets.gleif import (
    VERIFIER_ID,
    GleifEntity,
    alias_claims,
    category_claims,
    entity_split,
    iter_entities,
    jurisdiction_claims,
    normalize_lei,
    parent_claims,
    registration_date_claims,
    status_claims,
)
from eval_lab.schema import GoldProvenance, JudgmentMode

SEED = 260922
LEI_A = "5493001KJTIIGC8Y1R12"
LEI_B = "213800WSGIIZCXF1P572"
LEI_C = "529900T8BM49AURSDO55"

HEADER = [
    "LEI",
    "Entity.LegalName",
    "Entity.EntityCategory",
    "Entity.LegalJurisdiction",
    "Registration.RegistrationStatus",
    "Registration.InitialRegistrationDate",
]
COLUMNS = {
    "lei": "LEI",
    "legal_name": "Entity.LegalName",
    "entity_category": "Entity.EntityCategory",
    "legal_jurisdiction": "Entity.LegalJurisdiction",
    "registration_status": "Registration.RegistrationStatus",
    "initial_registration_date": "Registration.InitialRegistrationDate",
}
ROWS = [
    [LEI_A, "ALPHA HOLDINGS LIMITED", "GENERAL", "GB", "ISSUED", "2013-04-11"],
    [LEI_B, "BETA CAPITAL SA", "GENERAL", "FR", "LAPSED", "2015-09-02"],
    [LEI_C, "GAMMA TRUST", "BRANCH", "US", "ISSUED", "2018-01-30"],
]


def entity(**overrides: str) -> GleifEntity:
    base = {
        "lei": LEI_A,
        "legal_name": "ALPHA HOLDINGS LIMITED",
        "entity_category": "GENERAL",
        "legal_jurisdiction": "GB",
        "registration_status": "ISSUED",
        "initial_registration_date": "2013-04-11",
    }
    return GleifEntity(**{**base, **overrides})


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> Path:
    lines = [",".join(header), *(",".join(row) for row in rows)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_iter_entities_streams_wellformed_leis(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path / "lei.csv", HEADER, ROWS)
    entities = list(iter_entities(csv_path, columns=COLUMNS))
    assert [item.lei for item in entities] == [LEI_A, LEI_B, LEI_C]
    assert entities[0].registration_status == "ISSUED"
    assert entities[1].legal_jurisdiction == "FR"


def test_iter_entities_skips_malformed_leis(tmp_path: Path) -> None:
    rows = [*ROWS, ["not-an-lei", "DELTA", "GENERAL", "DE", "ISSUED", "2020-05-05"]]
    csv_path = write_csv(tmp_path / "lei.csv", HEADER, rows)
    entities = list(iter_entities(csv_path, columns=COLUMNS))
    assert [item.lei for item in entities] == [LEI_A, LEI_B, LEI_C]


def test_iter_entities_fails_closed_on_missing_columns(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path / "lei.csv", ["LEI", "Entity.LegalName"], [])
    with pytest.raises(ValueError, match="missing required columns"):
        list(iter_entities(csv_path, columns=COLUMNS))


def test_entity_split_depends_only_on_normalized_lei() -> None:
    assert entity_split(LEI_A, seed=SEED) is entity_split(LEI_A, seed=SEED)
    assert entity_split(f"  {LEI_A.lower()} ", seed=SEED) is entity_split(LEI_A, seed=SEED)
    assert normalize_lei(f" {LEI_A.lower()} ") == LEI_A


def test_entity_split_rejects_malformed_lei() -> None:
    with pytest.raises(ValueError):
        entity_split("short", seed=SEED)


def test_aliases_inherit_the_source_entity_split() -> None:
    split = entity_split(LEI_A, seed=SEED)
    records = alias_claims(entity(), alias="ALPHA HOLDINGS LTD", wrong_lei=LEI_B, seed=SEED)
    assert len(records) == 2
    assert all(record.split is split for record in records)
    assert {record.source_problem_id for record in records} == {f"alias:{LEI_A}"}


def test_every_family_shares_one_entity_split() -> None:
    split = entity_split(LEI_A, seed=SEED)
    families = [
        status_claims(entity(), status_vocabulary=["ISSUED", "LAPSED"], seed=SEED),
        jurisdiction_claims(entity(), jurisdiction_vocabulary=["GB", "FR"], seed=SEED),
        category_claims(entity(), category_vocabulary=["GENERAL", "BRANCH"], seed=SEED),
        registration_date_claims(entity(), seed=SEED),
        alias_claims(entity(), alias="ALPHA HOLDINGS LTD", wrong_lei=LEI_B, seed=SEED),
    ]
    for family in families:
        assert family and all(record.split is split for record in family)


def test_claim_pair_is_one_pass_one_fail_with_distinct_candidates() -> None:
    records = status_claims(entity(), status_vocabulary=["ISSUED", "LAPSED"], seed=SEED)
    assert len(records) == 2
    assert {record.gold.label for record in records} == {"pass", "fail"}
    candidates = {record.candidate_a for record in records}
    assert candidates == {"Answer: ISSUED", "Answer: LAPSED"}
    assert len({record.record_id for record in records}) == 2
    for record in records:
        assert record.mode is JudgmentMode.SINGLE
        assert record.gold.provenance is GoldProvenance.DETERMINISTIC_VERIFIER
        assert record.gold.verifier_id == VERIFIER_ID
        assert record.gold.evidence["entity_lei"] == LEI_A


def test_wrong_variant_is_never_the_true_value() -> None:
    records = jurisdiction_claims(entity(), jurisdiction_vocabulary=["GB", "FR", "US"], seed=SEED)
    wrong = next(record for record in records if record.gold.label == "fail")
    assert wrong.gold.evidence["candidate_value"] != "GB"


def test_families_without_a_distractor_are_skipped() -> None:
    assert status_claims(entity(), status_vocabulary=["ISSUED"], seed=SEED) == []
    assert jurisdiction_claims(entity(), jurisdiction_vocabulary=["GB"], seed=SEED) == []


def test_registration_date_wrong_variant_shifts_by_one_day() -> None:
    records = registration_date_claims(entity(), seed=SEED)
    wrong = next(record for record in records if record.gold.label == "fail")
    assert wrong.candidate_a == "Answer: 2013-04-12"


def test_parent_claims_reject_distractor_collision() -> None:
    with pytest.raises(ValueError):
        parent_claims(
            start_lei=LEI_A,
            start_name="ALPHA",
            parent_lei=LEI_B,
            wrong_lei=LEI_A,
            relationship_type="IS_DIRECTLY_CONSOLIDATED_BY",
            seed=SEED,
        )


def test_parent_claims_are_entity_disjoint_on_the_child() -> None:
    records = parent_claims(
        start_lei=LEI_A,
        start_name="ALPHA HOLDINGS LIMITED",
        parent_lei=LEI_B,
        wrong_lei=LEI_C,
        relationship_type="IS_DIRECTLY_CONSOLIDATED_BY",
        seed=SEED,
    )
    assert all(record.split is entity_split(LEI_A, seed=SEED) for record in records)
    assert {record.gold.label for record in records} == {"pass", "fail"}
