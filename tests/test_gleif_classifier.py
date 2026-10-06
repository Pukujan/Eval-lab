from __future__ import annotations

from collections.abc import Callable

import pytest

from eval_lab.datasets.gleif import (
    CLASSIFIER_FAMILIES,
    CLASSIFIER_VERIFIER_ID,
    GleifEntity,
    category_item,
    entity_split,
    jurisdiction_item,
    status_item,
)
from eval_lab.escalation.providers import normalize_typed_response
from eval_lab.escalation.spec import build_decision_spec
from eval_lab.schema import (
    GoldLabel,
    GoldProvenance,
    JudgeRecord,
    JudgmentMode,
    RubricCriterion,
    Split,
)

CATEGORY_LABELS = ["GENERAL", "FUND", "BRANCH", "SOLE_PROPRIETOR"]
CATEGORY_CRITERIA = {label: f"The entity category is {label}." for label in CATEGORY_LABELS}

ENTITY = GleifEntity(
    lei="5493001KJTIIGC8Y1R12",
    legal_name="ACME FUND LTD",
    entity_category="FUND",
    legal_jurisdiction="US-DE",
    registration_status="ISSUED",
    initial_registration_date="2013-05-15",
)


def record(label: str = "pass") -> JudgeRecord:
    return JudgeRecord(
        record_id="gleif:entity-category:TEST:1",
        source_problem_id="entity-category:TEST",
        mode=JudgmentMode.SINGLE,
        prompt="Which entity category applies?",
        rubric=[RubricCriterion(criterion_id="c1", description="Objective field value.")],
        candidate_a="Answer with exactly one entity category.",
        gold=GoldLabel(
            label=label,
            provenance=GoldProvenance.DETERMINISTIC_VERIFIER,
            evidence={"entity_lei": "TEST"},
            verifier_id="gleif-registry-classification-v1",
        ),
        split=Split.TEST,
    )


def test_binary_spec_payload_is_unchanged() -> None:
    payload = build_decision_spec(record()).provider_payload()
    criteria = payload["questions"]["verdict"]["criteria"]
    assert list(criteria) == ["pass", "fail"]
    assert criteria["pass"] == "The candidate is objectively correct."
    assert criteria["fail"] == "The candidate is objectively incorrect."


def test_custom_label_set_builds_closed_set_payload() -> None:
    spec = build_decision_spec(
        record("FUND"), label_set=CATEGORY_LABELS, criteria=CATEGORY_CRITERIA
    )
    assert spec.legal_labels == CATEGORY_LABELS
    criteria = spec.provider_payload()["questions"]["verdict"]["criteria"]
    assert list(criteria) == CATEGORY_LABELS
    assert criteria["FUND"] == "The entity category is FUND."


def test_custom_label_set_defaults_criteria_to_label() -> None:
    spec = build_decision_spec(record("FUND"), label_set=CATEGORY_LABELS)
    criteria = spec.provider_payload()["questions"]["verdict"]["criteria"]
    assert criteria == {label: label for label in CATEGORY_LABELS}


def test_custom_label_set_requires_matching_criteria_keys() -> None:
    with pytest.raises(ValueError, match="criteria keys"):
        build_decision_spec(
            record("FUND"), label_set=CATEGORY_LABELS, criteria={"FUND": "only one"}
        )


def test_custom_label_set_rejects_singleton() -> None:
    with pytest.raises(ValueError, match="at least two unique labels"):
        build_decision_spec(record("FUND"), label_set=["FUND"])


def test_custom_label_order_must_be_a_permutation() -> None:
    spec = build_decision_spec(
        record("FUND"),
        label_set=CATEGORY_LABELS,
        label_order=["FUND", "GENERAL", "BRANCH", "SOLE_PROPRIETOR"],
    )
    assert spec.legal_labels == ["FUND", "GENERAL", "BRANCH", "SOLE_PROPRIETOR"]
    with pytest.raises(ValueError, match="permutation"):
        build_decision_spec(
            record("FUND"), label_set=CATEGORY_LABELS, label_order=["FUND", "UNKNOWN"]
        )


def test_normalize_custom_label_preserves_probabilities() -> None:
    normalized = normalize_typed_response(
        {"label": "FUND", "probabilities": {"FUND": 0.7, "GENERAL": 0.2, "BRANCH": 0.1}},
        record("FUND"),
        provider="openrouter",
        model="typesafe/jev-1.13",
        label_set=CATEGORY_LABELS,
    )
    assert normalized.label == "FUND"
    assert normalized.probabilities == pytest.approx(
        {"FUND": 0.7, "GENERAL": 0.2, "BRANCH": 0.1, "SOLE_PROPRIETOR": 0.0}
    )


def test_normalize_custom_label_is_exact_membership() -> None:
    with pytest.raises(ValueError, match="illegal label"):
        normalize_typed_response(
            {"label": "fund"},
            record("FUND"),
            provider="openrouter",
            model="typesafe/jev-1.13",
            label_set=CATEGORY_LABELS,
        )
    with pytest.raises(ValueError, match="illegal label"):
        normalize_typed_response(
            {"label": "UNKNOWN"},
            record("FUND"),
            provider="openrouter",
            model="typesafe/jev-1.13",
            label_set=CATEGORY_LABELS,
        )


def test_normalize_custom_probabilities_reject_out_of_set_labels() -> None:
    with pytest.raises(ValueError, match="illegal label"):
        normalize_typed_response(
            {"label": "FUND", "probabilities": {"FUND": 0.5, "NOT_A_LABEL": 0.5}},
            record("FUND"),
            provider="openrouter",
            model="typesafe/jev-1.13",
            label_set=CATEGORY_LABELS,
        )


def test_binary_label_coercion_is_disabled_for_custom_sets() -> None:
    # The binary path coerces "1" to pass; a custom set must not.
    with pytest.raises(ValueError, match="illegal label"):
        normalize_typed_response(
            {"label": "1"},
            record("FUND"),
            provider="openrouter",
            model="typesafe/jev-1.13",
            label_set=CATEGORY_LABELS,
        )


CLASSIFIER_VOCABULARIES: dict[str, list[str]] = {
    "entity-category": ["GENERAL", "FUND", "BRANCH"],
    "registration-status": ["ISSUED", "LAPSED", "RETIRED"],
    "legal-jurisdiction": ["US-DE", "GB", "OTHER"],
}
CLASSIFIER_CASES: list[tuple[str, Callable[..., JudgeRecord], str, str]] = [
    ("entity-category", category_item, "Entity category", "FUND"),
    ("registration-status", status_item, "Registration status", "ISSUED"),
    ("legal-jurisdiction", jurisdiction_item, "Legal jurisdiction", "US-DE"),
]


def test_classifier_cases_cover_every_family() -> None:
    assert tuple(family for family, *_ in CLASSIFIER_CASES) == CLASSIFIER_FAMILIES


@pytest.mark.parametrize("family,builder,masked_line,gold", CLASSIFIER_CASES)
def test_classifier_item_masks_target_field_and_uses_source_gold(
    family: str, builder: Callable[..., JudgeRecord], masked_line: str, gold: str
) -> None:
    item = builder(ENTITY, vocabulary=CLASSIFIER_VOCABULARIES[family], seed=260922)
    assert item.gold.label == gold
    assert item.gold.provenance is GoldProvenance.DETERMINISTIC_VERIFIER
    assert item.gold.verifier_id == CLASSIFIER_VERIFIER_ID
    assert item.gold.evidence["source_field_value"] == gold
    assert item.source_problem_id == f"{family}:{ENTITY.lei}"
    # the target field is withheld from the prompt; the other fields stay.
    assert masked_line not in item.prompt
    assert f"LEI: {ENTITY.lei}" in item.prompt
    for option in CLASSIFIER_VOCABULARIES[family]:
        assert option in item.prompt


def test_jurisdiction_item_maps_out_of_vocabulary_value_to_other() -> None:
    item = jurisdiction_item(ENTITY, vocabulary=["GB", "DE", "OTHER"], seed=260922)
    assert item.gold.label == "OTHER"
    assert item.gold.evidence["source_field_value"] == "US-DE"
    assert "Legal jurisdiction" not in item.prompt


def test_classifier_item_rejects_gold_outside_the_closed_vocabulary() -> None:
    with pytest.raises(ValueError, match="not in the closed vocabulary"):
        category_item(ENTITY, vocabulary=["GENERAL", "BRANCH"], seed=260922)


def test_all_families_for_one_entity_share_a_split() -> None:
    items = [
        builder(ENTITY, vocabulary=CLASSIFIER_VOCABULARIES[family], seed=260922)
        for family, builder, *_ in CLASSIFIER_CASES
    ]
    assert len({item.split for item in items}) == 1
    assert items[0].split is entity_split(ENTITY.lei, seed=260922)
