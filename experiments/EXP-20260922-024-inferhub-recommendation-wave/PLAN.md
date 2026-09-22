# Plan

## Hypothesis

The recommendation engine's policy-qualified, family-deduplicated cheapest
routes will expose a useful cost/quality frontier while making provider
reliability and latency differences measurable without counting duplicate
provider rails as independent model families.

## Frozen inputs

- Source pool: EXP-20260921-015 exact records and typed specification.
- Public selection: descriptive canary and comparison only.
- Primary partition: the 760-record blind holdout.
- Gold labels are used offline only.
- No local Qwen4B inference is started.

## Selection rule

1. Use the dated InferHub `daily-shortlist.json` generated on 2026-09-22.
2. Keep only operationally selected, routing-eligible families.
3. Deduplicate each family to the lowest current minimum input ask; break ties
   by minimum output ask and exact model ID.
4. Exclude aliases and IDs containing `gpt`, `chatgpt`, or `codex`.
5. Preserve the engine policy and route prices in `selection.json`; the
   recommendation score is metadata, never benchmark gold.

## Execution sequence

1. Run one-record streaming canaries for all nine routes in fresh directories.
2. Run the 648-record public selection in bounded batches, four workers per
   route and no more than eight route processes at once.
3. Compare public outputs offline and checkpoint provider statuses.
4. Run the same nine routes on the frozen 760-record blind holdout.
5. Generate metrics only from checkpointed outputs after duplicate-ID and
   partition-integrity audits.

## Stopping and missingness

An arm is paused for investigation if its canary produces a route error, server
rate limit, timeout, malformed stream, or missing content. Bulk records retain
`rate_limited`, `provider_error`, `timeout`, `parse_error`, or `skipped` as
unresolved statuses. No fallback model is called for an affected record.
