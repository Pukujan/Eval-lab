"""Read-only live InferHub catalog check with secret-free output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import httpx


def _load_dotenv(path: Path | None) -> dict[str, str]:
    values: dict[str, str] = {}
    if path is None or not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _model_row(row: dict[str, Any]) -> dict[str, Any]:
    pricing = row.get("pricing") or {}
    return {
        "id": row.get("id"),
        "label": row.get("upstream_label"),
        "minimum_input_ask": pricing.get("min_ask_in"),
        "minimum_output_ask": pricing.get("min_ask_out"),
        "context_window": row.get("input_token_limit"),
        "modality": row.get("modality"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--compare", type=Path)
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    if args.limit <= 0:
        raise SystemExit("--limit must be positive")

    environment = _load_dotenv(args.env_file)
    api_key = environment.get("INFERHUB_API_KEY")
    api_url = environment.get("INFERHUB_API_URL", "https://api.inferhub.dev/v1").rstrip("/")
    if not api_key:
        raise SystemExit("INFERHUB_API_KEY is missing from --env-file")

    response = httpx.get(
        f"{api_url}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30.0,
    )
    response.raise_for_status()
    rows = [row for row in response.json().get("data", []) if isinstance(row, dict)]
    old_ids: set[str] = set()
    if args.compare:
        old_payload = json.loads(args.compare.read_text(encoding="utf-8-sig"))
        old_ids = {str(row.get("id")) for row in old_payload.get("data", []) if isinstance(row, dict)}

    priced = [
        _model_row(row)
        for row in rows
        if row.get("pricing") and not any(token in str(row.get("id", "")).lower() for token in ("gpt", "chatgpt"))
    ]
    priced.sort(key=lambda row: (row["minimum_input_ask"], row["minimum_output_ask"]))
    result = {
        "model_count": len(rows),
        "new_ids_vs_compare": sorted(str(row.get("id")) for row in rows if row.get("id") not in old_ids),
        "cheapest_non_chatgpt": priced[: args.limit],
        "rate_limit_remaining": response.headers.get("X-RateLimit-Remaining"),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
