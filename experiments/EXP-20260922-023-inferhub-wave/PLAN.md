# Plan

## Hypothesis

The cheapest and newest release available on each active InferHub rail will
provide a useful cost/quality frontier, but marketplace rail, model release,
and capacity effects will produce different reliability and latency profiles.

## Frozen inputs

- Source pool: EXP-20260921-015 exact records and typed specification.
- Primary partition: `blind_holdout`.
- Public selection: route canaries and descriptive comparison only.
- No gold labels are included in provider requests.
- No local Qwen4B inference is started.

## Selection rule

1. Query the authenticated live `/v1/models` catalog.
2. Exclude aliases and model IDs containing `gpt` or `chatgpt`.
3. For each active marketplace rail, select the lowest live minimum ask.
4. Select the newest upstream release that is present on that rail and has an
   official release source; if the same route satisfies both, run it once.
5. Exclude a rail with zero active providers rather than inventing capacity.

## Execution sequence

1. Run one-record streaming canaries for each selected route in fresh output
   directories.
2. Run public selection with four workers per route, limiting the number of
   concurrent route processes to eight.
3. Compare public outputs offline and preserve all provider statuses.
4. Run the same selected routes on the frozen blind holdout.
5. Generate metrics only after all route outputs are checkpointed.

## Stopping and missingness

An arm is paused for investigation if its canary returns a route error, a
server rate limit, or a malformed stream. In bulk runs, each affected record
retains `rate_limited`, `provider_error`, `parse_error`, or `skipped`; no
fallback model is called for that record.
