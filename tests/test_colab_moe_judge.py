from __future__ import annotations

from scripts.build_colab_moe_requests import build
from scripts.run_colab_moe_judge import extract_label, grammar_for, user_prompt


def test_grammar_admits_exactly_the_legal_labels() -> None:
    assert grammar_for(["pass", "fail"]) == 'root ::= "pass" | "fail"\n'
    assert grammar_for(["A", "B", "TIE"]) == 'root ::= "A" | "B" | "TIE"\n'


def test_user_prompt_carries_question_options_and_labels() -> None:
    request = {
        "record_id": "r1",
        "question": "Is the answer correct?",
        "options": [
            {"id": "pass", "description": "correct"},
            {"id": "fail", "description": "wrong"},
        ],
        "labels": ["pass", "fail"],
        "state": '{"prompt": "2+2?"}',
    }
    prompt = user_prompt(request)
    assert "Is the answer correct?" in prompt
    assert "- pass: correct" in prompt
    assert "- fail: wrong" in prompt
    assert '"prompt": "2+2?"' in prompt
    assert "pass | fail" in prompt


def test_extract_label_prefers_content() -> None:
    label, text = extract_label({"content": "pass", "reasoning_content": "fail"}, ["pass", "fail"])
    assert label == "pass"
    assert text == "pass"


def test_extract_label_falls_back_to_reasoning_content() -> None:
    # A thinking model under a grammar emits the label in reasoning_content and
    # leaves content empty; this must still resolve.
    label, text = extract_label({"content": "", "reasoning_content": "fail"}, ["pass", "fail"])
    assert label == "fail"
    assert text == "fail"


def test_extract_label_rejects_non_label_output() -> None:
    label, text = extract_label({"content": "maybe"}, ["pass", "fail"])
    assert label is None
    assert text == "maybe"


def test_build_partitions_match_the_frozen_pool() -> None:
    blind = build("blind_holdout")
    public = build("public_selection")
    assert len(blind) == 760
    assert len(public) == 648
    for request in (blind[0], public[0]):
        assert "gold" not in request
        assert set(request["labels"]) in ({"pass", "fail"}, {"A", "B", "TIE"})
    single = [r for r in blind if r["mode"] == "single"]
    pairwise = [r for r in blind if r["mode"] == "pairwise"]
    assert len(single) == 652
    assert len(pairwise) == 108
    assert all(r["labels"] == ["pass", "fail"] for r in single)
    assert all(r["labels"] == ["A", "B", "TIE"] for r in pairwise)
