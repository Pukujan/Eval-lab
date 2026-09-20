from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_URL = "https://opencode.ai/zen/v1/systemone"
DEFAULT_MODEL = "jev-1.13-free"


async def evaluate_jev(
    state: str | dict[str, Any] | list[Any],
    questions: dict[str, Any],
    *,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    base_url: str = DEFAULT_URL,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Call OpenCode Zen's Jev System One endpoint and return the raw JSON response."""
    key = api_key or os.getenv("OPENCODE_API_KEY")
    if not key:
        raise RuntimeError("Set OPENCODE_API_KEY before calling Jev.")

    payload = {"model": model, "state": state, "questions": questions}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(base_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
