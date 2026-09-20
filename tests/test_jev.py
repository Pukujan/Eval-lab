import pytest

from eval_lab.jev import evaluate_jev


@pytest.mark.asyncio
async def test_jev_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENCODE_API_KEY"):
        await evaluate_jev(
            state="candidate",
            questions={"correct": {"type": "noul", "instructions": "Correct?"}},
        )
