# Jev Eval Lab Integration Contract

This is the current operational contract for new Jev work. It supersedes the
historical OpenCode-specific route for future experiments without rewriting
historical TASK-0003 evidence.

## Authorized access

- Provider: OpenRouter, Jev-only.
- Endpoint: `https://openrouter.ai/api/alpha/decisions`.
- Pinned model: `typesafe/jev-1.13`.
- Rolling canary: `~typesafe/jev-latest`, always kept separate from the pinned arm.
- Credential: `OPENROUTER_API_KEY`, supplied transiently through the local secret
  environment or ignored `.env` file.
- Forbidden for new work: OpenCode, OpenCode Zen, Chat Completions for Jev,
  automatic paid fallbacks, and alternate providers.

The direct xAI Build CLI is for Grok only. Direct Codex is for Luna/Sol only
when an experiment explicitly includes those arms. This document does not
authorize either route for Jev.

## Request contract

Every record request must contain:

```json
{
  "model": "typesafe/jev-1.13",
  "state": "...",
  "questions": {
    "verdict": {
      "type": "choice",
      "instructions": "Return the single objective verdict for the candidate record.",
      "criteria": {
        "pass": "The candidate is objectively correct.",
        "fail": "The candidate is objectively incorrect."
      }
    }
  }
}
```

Pairwise records replace the legal set with `A`, `B`, and `TIE`, with explicit
descriptions. The question ID is a local join key and must never be treated as
an instruction.

## Response contract

The adapter must:

- require a legal typed choice;
- preserve `answers.<question_id>.probabilities` when present;
- preserve native `confidence` as metadata when present;
- preserve the resolved model and usage/cost metadata when present;
- reject malformed or out-of-set answers as `parse_error`;
- retain HTTP, transport, auth, billing, and rate-limit failures as execution
  states with no fabricated label;
- never promote Jev output to objective gold.

## Concurrency and streaming

Independent record calls may run in bounded parallel workers, with immediate
per-record checkpointing and deterministic output order. A future multi-record
fan-out adapter may be added only as a separately preregistered implementation
and experiment comparison.

Jev is a structured decision response, not a text-generation stream. Do not
add `stream=true` or parse partial text for the Jev route. If the provider later
documents a decision-stream protocol, it requires a new contract test and a new
experiment comparison.

## Research integrity

- Freeze model ID, prompt/spec version, label order, record pool, and any
  perturbation schedule before final labels.
- Keep pinned and rolling aliases separate.
- Keep native probability metrics separate from label-only outputs.
- Keep provider availability separate from accuracy and calibration.
- Do not alter EXP-014 through EXP-019; any changed route, question rubric,
  model alias, batching method, or calibration method receives a new experiment
  ID.
