# EXP-20260922-025 — Grok protocol ablation

Provider statuses remain unresolved and are not counted as labels.

## Public protocol selection

Primary model: `grok_46`; baseline: `typed_schema`; selected variant: `typed_schema`.
Gate passed: `False` — no alternative passed the preregistered public gate; rerun baseline.
The first no-schema pass exposed a Windows locale-decoding failure in the shared stream reader; it was stopped and resumed from its normalized checkpoint after the UTF-8-safe reader repair. Only the repaired arm's final results are used below.

| Arm | Variant | Resolved | Coverage | Mode-balanced score | Statuses |
|---|---|---:|---:|---:|---|
| `grok_46` | `explicit_no_schema` | 0/64 | 0.0000 | n/a | `parse_error=57, provider_error=6, rate_limited=1` |
| `grok_46` | `explicit_schema` | 63/64 | 0.9844 | 0.25806451612903225 | `ok=63, provider_error=1` |
| `grok_46` | `semantic_schema` | 63/64 | 0.9844 | 0.2661290322580645 | `ok=63, provider_error=1` |
| `grok_46` | `typed_schema` | 64/64 | 1.0000 | 0.265625 | `ok=64` |

## Blind confirmation

The blind run was evaluated only after the public selection decision.

| Arm | Variant | Resolved | Coverage | Mode-balanced score | Statuses |
|---|---|---:|---:|---:|---|
| `grok_46` | `typed_schema` | 757/760 | 0.9961 | 0.25857656362329257 | `ok=757, provider_error=3` |
